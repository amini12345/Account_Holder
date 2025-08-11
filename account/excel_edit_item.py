from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from holder.models import Items, PersonalInfo, ItemChangeRequest
from .forms import ItemForm
import json

@login_required
def edit_item_from_comparison(request, item_id):
    """ویرایش کالا از طریق نتایج مقایسه Excel با سیستم تایید"""
    item = get_object_or_404(Items, id=item_id)
    
    if request.method == 'POST':
        form = ItemForm(request.POST, instance=item)
        if form.is_valid():
            # دریافت کالای اصلی قبل از تغییر
            original_obj = Items.objects.get(pk=item.pk)
            
            # بررسی تغییرات
            changes = {}
            fields_to_check = [
                'Technical_items', 'type_Item', 'status_item', 'status_sub_item',
                'brand', 'Configuration', 'serial_number', 'Product_code', 'PersonalInfo'
            ]
            
            for field in fields_to_check:
                original_value = getattr(original_obj, field)
                new_value = getattr(form.instance, field)
                if original_value != new_value:
                    if field == 'PersonalInfo':
                        changes[field] = {
                            'old': f"{original_value.name} {original_value.family}" if original_value else None,
                            'new': f"{new_value.name} {new_value.family}" if new_value else None,
                            'old_id': original_value.Personnel_number if original_value else None,
                            'new_id': new_value.Personnel_number if new_value else None
                        }
                    else:
                        changes[field] = {
                            'old': str(original_value) if original_value else None,
                            'new': str(new_value) if new_value else None
                        }
            
            # اگر تغییری وجود دارد
            if changes:
                # بررسی اینکه آیا تغییر مالک رخ داده است
                owner_change = 'PersonalInfo' in changes
                
                if owner_change:
                    old_owner = original_obj.PersonalInfo
                    new_owner = form.instance.PersonalInfo
                    
                    # اگر کالا از کسی گرفته می‌شود (کم می‌شود)
                    if old_owner and old_owner != new_owner:
                        # ایجاد درخواست تایید برای مالک قبلی (مرحله اول)
                        action_type = 'transfer' if new_owner else 'remove'
                        description = f"درخواست {'انتقال' if new_owner else 'حذف'} کالا {original_obj.Technical_items} توسط مدیر {request.user.username}"
                        if new_owner:
                            description += f" به {new_owner.name} {new_owner.family}"
                        
                        # ایجاد درخواست برای مالک فعلی
                        ItemChangeRequest.objects.create(
                            item=original_obj,
                            owner=old_owner,
                            admin_user=request.user.username,
                            action_type=action_type,
                            proposed_changes=changes,
                            description=description
                        )
                        
                        if new_owner:
                            # همزمان ایجاد درخواست برای مالک جدید
                            ItemChangeRequest.objects.create(
                                item=original_obj,
                                owner=new_owner,
                                admin_user=request.user.username,
                                action_type='receive',
                                proposed_changes=changes,
                                description=f"درخواست دریافت کالا {original_obj.Technical_items} توسط مدیر {request.user.username}"
                            )
                            
                            message = (f"درخواست انتقال کالا {original_obj.Technical_items} "
                                     f"برای تایید {old_owner.name} {old_owner.family} (مالک فعلی) و "
                                     f"{new_owner.name} {new_owner.family} (مالک جدید) ارسال شد. "
                                     f"کالا پس از تایید هر دو نفر منتقل خواهد شد.")
                        else:
                            message = (f"درخواست حذف کالا {original_obj.Technical_items} "
                                     f"برای تایید {old_owner.name} {old_owner.family} ارسال شد. "
                                     f"تغییرات پس از تایید مالک اعمال خواهد شد.")
                        
                        messages.warning(request, message)
                        
                        # اگر درخواست AJAX باشد، پاسخ JSON برگردان
                        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                            return JsonResponse({
                                'success': True,
                                'message': message,
                                'approval_required': True
                            })
                        
                        return redirect(request.META.get('HTTP_REFERER', 'account:home'))
                    
                    # اگر کالا به کسی داده می‌شود (اضافه می‌شود) و مالک قبلی ندارد
                    elif new_owner and not old_owner:
                        # ایجاد درخواست تایید برای مالک جدید
                        ItemChangeRequest.objects.create(
                            item=original_obj,
                            owner=new_owner,
                            admin_user=request.user.username,
                            action_type='assign',
                            proposed_changes=changes,
                            description=f"درخواست تخصیص کالا {original_obj.Technical_items} توسط مدیر {request.user.username}"
                        )
                        
                        message = (f"درخواست تخصیص کالا {original_obj.Technical_items} "
                                 f"برای تایید {new_owner.name} {new_owner.family} ارسال شد. "
                                 f"تغییرات پس از تایید مالک اعمال خواهد شد.")
                        
                        messages.warning(request, message)
                        
                        # اگر درخواست AJAX باشد، پاسخ JSON برگردان
                        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                            return JsonResponse({
                                'success': True,
                                'message': message,
                                'approval_required': True
                            })
                        
                        return redirect(request.META.get('HTTP_REFERER', 'account:home'))
                
                # اگر تغییرات غیر از مالک است و کالا مالک دارد
                elif original_obj.PersonalInfo:
                    # ایجاد درخواست تایید برای تغییرات عادی
                    ItemChangeRequest.objects.create(
                        item=original_obj,
                        owner=original_obj.PersonalInfo,
                        admin_user=request.user.username,
                        action_type='edit',
                        proposed_changes=changes,
                        description=f"درخواست تغییر مشخصات کالا {original_obj.Technical_items} توسط مدیر {request.user.username}"
                    )
                    
                    message = (f"درخواست تغییر کالا {original_obj.Technical_items} برای تایید مالک ارسال شد. "
                             f"تغییرات پس از تایید مالک اعمال خواهد شد.")
                    
                    messages.warning(request, message)
                    
                    # اگر درخواست AJAX باشد، پاسخ JSON برگردان
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return JsonResponse({
                            'success': True,
                            'message': message,
                            'approval_required': True
                        })
                    
                    return redirect(request.META.get('HTTP_REFERER', 'account:home'))
                
                # اگر کالا مالک ندارد، مستقیماً تغییرات اعمال شود
                else:
                    form.save()
                    message = f'کالا "{item.Technical_items}" با موفقیت به‌روزرسانی شد.'
                    messages.success(request, message)
                    
                    # اگر درخواست AJAX باشد، پاسخ JSON برگردان
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return JsonResponse({
                            'success': True,
                            'message': message,
                            'approval_required': False,
                            'item_data': {
                                'id': item.id,
                                'item_name': item.Technical_items,
                                'item_type': item.get_type_Item_display(),
                                'brand': item.brand,
                                'configuration': item.Configuration,
                                'status_main': item.get_status_item_display(),
                                'status_sub': item.get_status_sub_item_display() if item.status_sub_item else None,
                                'serial_number': item.serial_number,
                                'product_code': item.Product_code,
                                'holder_info': f"{item.PersonalInfo.name} {item.PersonalInfo.family} ({item.PersonalInfo.Personnel_number})" if item.PersonalInfo else None,
                                'number': item.Number
                            }
                        })
                    
                    return redirect(request.META.get('HTTP_REFERER', 'account:home'))
            
            # اگر تغییری وجود ندارد
            else:
                message = 'هیچ تغییری اعمال نشد.'
                messages.info(request, message)
                
                # اگر درخواست AJAX باشد، پاسخ JSON برگردان
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': True,
                        'message': message,
                        'approval_required': False
                    })
                
                return redirect(request.META.get('HTTP_REFERER', 'account:home'))
        
        else:
            # اگر فرم نامعتبر باشد
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                errors = {}
                for field, error_list in form.errors.items():
                    errors[field] = [str(error) for error in error_list]
                return JsonResponse({
                    'success': False,
                    'errors': errors,
                    'message': 'لطفاً خطاهای فرم را بررسی کنید.'
                })
            
            messages.error(request, 'لطفاً خطاهای فرم را بررسی کنید.')
    else:
        form = ItemForm(instance=item)
    
    # دریافت داده‌های Excel اگر در session موجود باشد
    excel_data = None
    if 'comparison_excel_data' in request.session:
        comparison_data = request.session['comparison_excel_data']
        # پیدا کردن داده‌های Excel مربوط به این کالا
        for diff_item in comparison_data.get('differences', []):
            if diff_item['system_data']['id'] == item.id:
                excel_data = diff_item['excel_data']
                break
    
    context = {
        'form': form,
        'item': item,
        'excel_data': excel_data,
        'title': f'ویرایش کالا: {item.Technical_items}',
        'is_comparison_edit': True
    }
    
    return render(request, 'registration/item_edit_from_comparison.html', context)

@login_required
def get_sub_status_options_for_edit(request):
    """دریافت گزینه‌های زیر وضعیت برای ویرایش کالا"""
    status_item = request.GET.get('status_item')
    
    if not status_item:
        return JsonResponse({'options': []})
    
    # دریافت گزینه‌های زیر وضعیت بر اساس وضعیت اصلی
    sub_status_options = []
    
    if status_item in Items.STATUS_SUB_MAPPING:
        for value, label in Items.STATUS_SUB_MAPPING[status_item]:
            sub_status_options.append({
                'value': value,
                'label': label
            })
    
    return JsonResponse({'options': sub_status_options})

@login_required
def apply_excel_data_to_item(request, item_id):
    """اعمال داده‌های Excel به کالای موجود"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'روش درخواست نامعتبر است.'})
    
    item = get_object_or_404(Items, id=item_id)
    
    try:
        # دریافت داده‌های Excel از درخواست
        excel_data = json.loads(request.body)
        
        # تبدیل داده‌های فارسی به انگلیسی
        def convert_persian_to_english(field_type, value):
            """تبدیل مقادیر فارسی به انگلیسی"""
            if not value:
                return value
            
            if field_type == 'item_type':
                type_mapping = {
                    'فنی': 'Technical',
                    'غیر فنی': 'Non-technical'
                }
                return type_mapping.get(value, value)
            
            elif field_type == 'status_main':
                status_mapping = {
                    '(تعمیری)سخت افزار': 'hardware',
                    'تحویل': 'Delivery',
                    'انبار': 'warehouse'
                }
                return status_mapping.get(value, value)
            
            elif field_type == 'status_sub':
                sub_status_mapping = {
                    'تعمیر': 'repair',
                    'ارتقا': 'upgrade',
                    'خارج': 'external',
                    'داخل': 'internal',
                    'آماده بکار': 'ready',
                    'عودتی سالم': 'returned_good',
                    'عودتی فرسوده': 'returned_worn'
                }
                return sub_status_mapping.get(value, value)
            
            return value
        
        # به‌روزرسانی فیلدهای کالا
        if 'item_name' in excel_data and excel_data['item_name']:
            item.Technical_items = excel_data['item_name']
        
        if 'item_type' in excel_data and excel_data['item_type']:
            item.type_Item = convert_persian_to_english('item_type', excel_data['item_type'])
        
        if 'brand' in excel_data and excel_data['brand']:
            item.brand = excel_data['brand']
        
        if 'configuration' in excel_data and excel_data['configuration']:
            item.Configuration = excel_data['configuration']
        
        if 'status_main' in excel_data and excel_data['status_main']:
            item.status_item = convert_persian_to_english('status_main', excel_data['status_main'])
        
        if 'status_sub' in excel_data and excel_data['status_sub']:
            item.status_sub_item = convert_persian_to_english('status_sub', excel_data['status_sub'])
        
        if 'serial_number' in excel_data and excel_data['serial_number']:
            item.serial_number = excel_data['serial_number']
        
        if 'product_code' in excel_data and excel_data['product_code']:
            item.Product_code = excel_data['product_code']
        
        if 'number' in excel_data and excel_data['number']:
            item.Number = int(excel_data['number'])
        
        # پردازش دارنده حساب
        if 'holder_info' in excel_data and excel_data['holder_info']:
            holder_info = excel_data['holder_info']
            
            # تلاش برای پیدا کردن دارنده حساب
            personal_info = None
            
            # اگر شماره پرسنلی 9 رقمی باشد
            if holder_info.isdigit() and len(holder_info) == 9:
                personal_info = PersonalInfo.objects.filter(Personnel_number=holder_info).first()
            else:
                # جستجو بر اساس نام و نام خانوادگی
                name_parts = holder_info.strip().split()
                if len(name_parts) >= 2:
                    first_name = name_parts[0]
                    last_name = ' '.join(name_parts[1:])
                    personal_info = PersonalInfo.objects.filter(
                        name__icontains=first_name,
                        family__icontains=last_name
                    ).first()
            
            if personal_info:
                item.PersonalInfo = personal_info
        
        # ذخیره تغییرات
        item.save()
        
        return JsonResponse({
            'success': True,
            'message': 'داده‌های Excel با موفقیت اعمال شد.',
            'item_data': {
                'id': item.id,
                'item_name': item.Technical_items,
                'item_type': item.get_type_Item_display(),
                'brand': item.brand,
                'configuration': item.Configuration,
                'status_main': item.get_status_item_display(),
                'status_sub': item.get_status_sub_item_display() if item.status_sub_item else None,
                'serial_number': item.serial_number,
                'product_code': item.Product_code,
                'holder_info': f"{item.PersonalInfo.name} {item.PersonalInfo.family} ({item.PersonalInfo.Personnel_number})" if item.PersonalInfo else None,
                'number': item.Number
            }
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'خطا در اعمال تغییرات: {str(e)}'
        })