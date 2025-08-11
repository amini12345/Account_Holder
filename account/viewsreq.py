"""
Views مربوط به سیستم تایید تغییرات کالاها
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import UpdateView
from django.urls import reverse_lazy
from django.contrib import messages
from django.db.models import Q
from django.views.decorators.http import require_POST
from django.utils import timezone
from holder.models import Items, ItemHistory, PersonalInfo, ItemChangeRequest
from .forms import ItemForm
from shared.approval_utils import (
    check_both_parties_approved, approve_item_transfer, approve_item_assignment,
    approve_item_removal, approve_item_edit, reject_related_requests, get_approval_message
)


# ==================== ITEM CHANGE REQUEST VIEWS ====================

class ItemUpdateViewWithApproval(LoginRequiredMixin, UpdateView):
    """ویرایش کالا با سیستم تایید"""
    model = Items
    form_class = ItemForm
    template_name = 'registration/item_form.html'
    success_url = reverse_lazy('account:home')
    
    def form_valid(self, form):
        # دریافت کالای اصلی قبل از تغییر
        original_obj = Items.objects.get(pk=form.instance.pk)
        
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
                    description = f"درخواست {'انتقال' if new_owner else 'حذف'} کالا {original_obj.Technical_items} توسط مدیر {self.request.user.username}"
                    if new_owner:
                        description += f" به {new_owner.name} {new_owner.family}"
                    
                    # ایجاد درخواست برای مالک فعلی
                    ItemChangeRequest.objects.create(
                        item=original_obj,
                        owner=old_owner,
                        admin_user=self.request.user.username,
                        action_type=action_type,
                        proposed_changes=changes,
                        description=description
                    )
                    
                    if new_owner:
                        # همزمان ایجاد درخواست برای مالک جدید
                        ItemChangeRequest.objects.create(
                            item=original_obj,
                            owner=new_owner,
                            admin_user=self.request.user.username,
                            action_type='receive',
                            proposed_changes=changes,
                            description=f"درخواست دریافت کالا {original_obj.Technical_items} توسط مدیر {self.request.user.username}"
                        )
                        
                        messages.warning(self.request, 
                            f"درخواست انتقال کالا {original_obj.Technical_items} "
                            f"برای تایید {old_owner.name} {old_owner.family} (مالک فعلی) و "
                            f"{new_owner.name} {new_owner.family} (مالک جدید) ارسال شد. "
                            f"کالا پس از تایید هر دو نفر منتقل خواهد شد."
                        )
                    else:
                        messages.warning(self.request, 
                            f"درخواست حذف کالا {original_obj.Technical_items} "
                            f"برای تایید {old_owner.name} {old_owner.family} ارسال شد. "
                            f"تغییرات پس از تایید مالک اعمال خواهد شد."
                        )
                    return redirect(self.success_url)
                
                # اگر کالا به کسی داده می‌شود (اضافه می‌شود) و مالک قبلی ندارد
                elif new_owner and not old_owner:
                    # ایجاد درخواست تایید برای مالک جدید
                    ItemChangeRequest.objects.create(
                        item=original_obj,
                        owner=new_owner,
                        admin_user=self.request.user.username,
                        action_type='assign',
                        proposed_changes=changes,
                        description=f"درخواست تخصیص کالا {original_obj.Technical_items} توسط مدیر {self.request.user.username}"
                    )
                    
                    messages.warning(self.request, 
                        f"درخواست تخصیص کالا {original_obj.Technical_items} "
                        f"برای تایید {new_owner.name} {new_owner.family} ارسال شد. "
                        f"تغییرات پس از تایید مالک اعمال خواهد شد."
                    )
                    return redirect(self.success_url)
            
            # اگر تغییرات غیر از مالک است و کالا مالک دارد
            elif original_obj.PersonalInfo:
                # ایجاد درخواست تایید برای تغییرات عادی
                ItemChangeRequest.objects.create(
                    item=original_obj,
                    owner=original_obj.PersonalInfo,
                    admin_user=self.request.user.username,
                    action_type='edit',
                    proposed_changes=changes,
                    description=f"درخواست تغییر مشخصات کالا {original_obj.Technical_items} توسط مدیر {self.request.user.username}"
                )
                
                messages.warning(self.request, 
                    f"درخواست تغییر کالا {original_obj.Technical_items} برای تایید مالک ارسال شد. "
                    f"تغییرات پس از تایید مالک اعمال خواهد شد."
                )
                return redirect(self.success_url)
            
            # اگر کالا مالک ندارد، مستقیماً تغییرات اعمال شود
            else:
                messages.success(self.request, 'کالا با موفقیت به‌روزرسانی شد.')
                return super().form_valid(form)
        
        # اگر تغییری وجود ندارد
        else:
            messages.info(self.request, 'هیچ تغییری اعمال نشد.')
            return redirect(self.success_url)


@login_required
def change_requests_list(request):
    """نمایش لیست درخواست‌های تغییر کالا"""
    # فیلتر درخواست‌ها
    status_filter = request.GET.get('status', '')
    action_filter = request.GET.get('action', '')
    search_query = request.GET.get('search', '')
    
    requests_queryset = ItemChangeRequest.objects.select_related('item', 'owner').all()
    
    if status_filter:
        requests_queryset = requests_queryset.filter(status=status_filter)
    
    if action_filter:
        requests_queryset = requests_queryset.filter(action_type=action_filter)
    
    if search_query:
        requests_queryset = requests_queryset.filter(
            Q(item__Technical_items__icontains=search_query) |
            Q(owner__name__icontains=search_query) |
            Q(owner__family__icontains=search_query) |
            Q(admin_user__icontains=search_query)
        )
    
    requests = requests_queryset.order_by('-created_at')
    
    # آمار درخواست‌ها
    total_requests = requests_queryset.count()
    pending_requests = requests_queryset.filter(status='pending').count()
    approved_requests = requests_queryset.filter(status='approved').count()
    rejected_requests = requests_queryset.filter(status='rejected').count()
    
    context = {
        'requests': requests,
        'total_requests': total_requests,
        'pending_requests': pending_requests,
        'approved_requests': approved_requests,
        'rejected_requests': rejected_requests,
        'status_filter': status_filter,
        'action_filter': action_filter,
        'search_query': search_query,
    }
    
    return render(request, 'registration/change_requests_list.html', context)


@login_required
def change_request_detail(request, pk):
    """جزئیات درخواست تغییر"""
    from django.contrib.auth.models import User
    from extensions.utils import jalali_converter
    
    change_request = get_object_or_404(ItemChangeRequest, pk=pk)
    
    # ��ریافت اطلاعات مدیر از User model
    admin_user_obj = None
    try:
        admin_user_obj = User.objects.get(username=change_request.admin_user)
    except User.DoesNotExist:
        admin_user_obj = None
    
    # دریافت اطلاعات دریافت کننده از proposed_changes
    new_owner_info = None
    if change_request.proposed_changes and 'PersonalInfo' in change_request.proposed_changes:
        new_owner_id = change_request.proposed_changes['PersonalInfo'].get('new_id')
        if new_owner_id:
            try:
                new_owner_info = PersonalInfo.objects.get(Personnel_number=new_owner_id)
            except PersonalInfo.DoesNotExist:
                new_owner_info = None
    
    # تبدیل تاریخ پاسخ به فارسی
    responded_at_persian = None
    if change_request.responded_at:
        responded_at_persian = jalali_converter(change_request.responded_at)
    
    context = {
        'change_request': change_request,
        'admin_user_obj': admin_user_obj,
        'new_owner_info': new_owner_info,
        'responded_at_persian': responded_at_persian,
    }
    
    return render(request, 'registration/change_request_detail.html', context)


@require_POST
@login_required
def approve_change_request_user(request, request_id):
    """تایید درخواست تغییر کالا توسط کاربر (مالک) - استفاده از shared utilities"""
    change_request = get_object_or_404(ItemChangeRequest, id=request_id)
    
    # بررسی اینکه کاربر مالک کالا است
    if change_request.owner.Personnel_number != request.user.username:
        messages.error(request, "شما مجاز به تایید این درخواست نیستید.")
        return redirect('account:change_requests_list')
    
    try:
        item = change_request.item
        changes = change_request.proposed_changes
        
        # ابتدا درخواست را تایید می‌کنیم
        change_request.status = 'approved'
        change_request.responded_at = timezone.now()
        change_request.save()
        
        if change_request.action_type in ['transfer', 'receive']:
            # برای انتقال کالا، بررسی می‌کنیم که آیا هر دو طرف تایید کرده‌اند
            old_owner_id = changes['PersonalInfo'].get('old_id')
            new_owner_id = changes['PersonalInfo'].get('new_id')
            
            if old_owner_id and new_owner_id:
                # بررسی اینکه آیا هر دو طرف تایید کرده‌اند
                both_approved = check_both_parties_approved(item, old_owner_id, new_owner_id)
                
                if both_approved:
                    # استفاده از shared utility برای انتقال
                    success, message = approve_item_transfer(item, old_owner_id, new_owner_id)
                    if success:
                        messages.success(request, f"درخواست شما تایید شد. {message}")
                    else:
                        messages.error(request, message)
                else:
                    # فقط یکی از طرفین تایید کرده
                    message = get_approval_message(change_request, old_owner_id, new_owner_id)
                    messages.success(request, message)
            else:
                # اگر مالک قبلی وجود ندارد، این یک خطای منطقی است
                # چون transfer/receive باید همیشه بین دو نفر باشد
                messages.error(request, "خطا: درخواست انتقال نامعتبر - اطلاعات مالک قبلی یافت نشد.")
        
        elif change_request.action_type == 'remove':
            # حذف ��الا از مالک
            success, message = approve_item_removal(item, item.PersonalInfo)
            if success:
                messages.success(request, message)
            else:
                messages.error(request, message)
        
        elif change_request.action_type == 'assign':
            # تخصیص کالا به مالک جدید - فقط اگر کالا مالک قبلی نداشته باشد
            if not item.PersonalInfo:
                success, message = approve_item_assignment(item, change_request.owner)
                if success:
                    messages.success(request, message)
                else:
                    messages.error(request, message)
            else:
                # اگر کالا مالک دارد، این باید از طریق transfer/receive باشد
                messages.error(request, "خطا: کالا دارای مالک است. انتقال باید از طریق سیستم تایید دوطرفه انجام شود.")
        
        elif change_request.action_type == 'edit':
            # ویرایش کالا
            success, message = approve_item_edit(item, changes, change_request.owner)
            if success:
                messages.success(request, message)
            else:
                messages.error(request, message)
        
        return redirect('account:change_requests_list')
        
    except Exception as e:
        messages.error(request, f"خطا در تایید درخواست: {str(e)}")
        return redirect('account:change_requests_list')


@require_POST
@login_required
def reject_change_request_user(request, request_id):
    """رد درخواست تغییر کالا توسط کاربر (مالک) - استفاده از shared utilities"""
    change_request = get_object_or_404(ItemChangeRequest, id=request_id)
    
    # بررسی اینکه کاربر مالک کالا است
    if change_request.owner.Personnel_number != request.user.username:
        messages.error(request, "شما مجاز به رد این درخواست نیستید.")
        return redirect('account:change_requests_list')
    
    try:
        # بروزرسانی وضعیت درخواست
        change_request.status = 'rejected'
        change_request.responded_at = timezone.now()
        change_request.save()
        
        # استفاده از shared utility برای رد درخواست‌های مرتبط
        reject_related_requests(change_request)
        
        messages.info(request, f"درخواست تغییر کالا {change_request.item.Technical_items} رد شد.")
        return redirect('account:change_requests_list')
        
    except Exception as e:
        messages.error(request, f"خطا در رد درخواست: {str(e)}")
        return redirect('account:change_requests_list')


@require_POST
@login_required
def approve_change_request_admin(request, request_id):
    """تایید درخواست تغییر کالا توسط مدیر (اجباری)"""
    change_request = get_object_or_404(ItemChangeRequest, id=request_id)
    
    try:
        # اعمال تغییرات
        item = change_request.item
        changes = change_request.proposed_changes
        
        if change_request.action_type in ['transfer', 'remove']:
            # انتقال یا حذف کالا
            if 'PersonalInfo' in changes:
                new_owner_id = changes['PersonalInfo'].get('new_id')
                
                if new_owner_id and change_request.action_type == 'transfer':
                    # انتقال کالا
                    old_owner_id = item.PersonalInfo.Personnel_number if item.PersonalInfo else None
                    if old_owner_id:
                        success, message = approve_item_transfer(
                            item, old_owner_id, new_owner_id,
                            f'انتقال اجباری توسط مدیر {request.user.username}'
                        )
                    else:
                        # تخصیص به مالک جدید
                        try:
                            new_owner = PersonalInfo.objects.get(Personnel_number=new_owner_id)
                            success, message = approve_item_assignment(
                                item, new_owner,
                                f'تخصیص اجباری توسط مدیر {request.user.username}'
                            )
                        except PersonalInfo.DoesNotExist:
                            success, message = False, "مالک جدید یافت نشد"
                else:
                    # حذف کالا
                    success, message = approve_item_removal(
                        item, item.PersonalInfo,
                        f'حذف اجباری توسط مدیر {request.user.username}'
                    )
                
                if not success:
                    messages.error(request, message)
                    return redirect('account:change_requests_list')
                
        elif change_request.action_type == 'assign':
            # تخصیص کالا به مالک جدید
            success, message = approve_item_assignment(
                item, change_request.owner,
                f'تخصیص اجباری توسط مدیر {request.user.username}'
            )
            if not success:
                messages.error(request, message)
                return redirect('account:change_requests_list')
                        
        elif change_request.action_type == 'edit':
            # و��رایش کالا
            success, message = approve_item_edit(
                item, changes, change_request.owner,
                f'تغییرات اجباری توسط مدیر {request.user.username}'
            )
            if not success:
                messages.error(request, message)
                return redirect('account:change_requests_list')
        
        # بروزرسانی وضعیت درخواست
        change_request.status = 'approved'
        change_request.responded_at = timezone.now()
        change_request.save()
        
        action_message = {
            'transfer': 'انتقال',
            'remove': 'حذف',
            'assign': 'تخصیص',
            'edit': 'تغییر'
        }.get(change_request.action_type, 'تغییر')
        
        messages.success(request, f"درخواست {action_message} کالا {item.Technical_items} به صورت اجباری تایید شد.")
        return redirect('account:change_requests_list')
        
    except Exception as e:
        messages.error(request, f"خطا در تایید درخواست: {str(e)}")
        return redirect('account:change_requests_list')


@require_POST
@login_required
def reject_change_request_admin(request, request_id):
    """رد درخواست تغییر کالا توسط مدیر"""
    change_request = get_object_or_404(ItemChangeRequest, id=request_id)
    
    try:
        # بروزرسانی وضعیت درخواست
        change_request.status = 'rejected'
        change_request.responded_at = timezone.now()
        change_request.save()
        
        messages.info(request, f"درخواست تغییر کالا {change_request.item.Technical_items} رد شد.")
        return redirect('account:change_requests_list')
        
    except Exception as e:
        messages.error(request, f"خطا در رد درخواست: {str(e)}")
        return redirect('account:change_requests_list')


@require_POST
@login_required
def delete_change_request(request, request_id):
    """حذف درخواست تغییر کالا"""
    change_request = get_object_or_404(ItemChangeRequest, id=request_id)
    
    try:
        item_name = change_request.item.Technical_items
        change_request.delete()
        
        messages.success(request, f"درخواست تغییر کالا {item_name} با موفقیت حذف شد.")
        return redirect('account:change_requests_list')
        
    except Exception as e:
        messages.error(request, f"خطا در حذف درخواست: {str(e)}")
        return redirect('account:change_requests_list')


@login_required
def bulk_transfer_items(request):
    """انتقال دسته‌ای کالاها با سیستم تایید"""
    if request.method == 'POST':
        selected_items = request.POST.getlist('selected_items')
        to_person_id = request.POST.get('to_person')
        description = request.POST.get('description', '')
        
        if not selected_items:
            messages.error(request, 'لطفاً حداقل یک کالا را انتخاب کنید.')
            return redirect('account:home')
        
        if not to_person_id:
            messages.error(request, 'لطفاً شخص مقصد را انتخاب کنید.')
            return redirect('account:home')
        
        try:
            to_person = PersonalInfo.objects.get(Personnel_number=to_person_id)
            
            request_count = 0
            direct_count = 0
            
            for item_id in selected_items:
                try:
                    item = Items.objects.get(id=item_id)
                    
                    if item.PersonalInfo and item.PersonalInfo != to_person:
                        # ایجاد درخواست تایید برای مالک قبلی و همزمان برای مالک جدید
                        ItemChangeRequest.objects.create(
                            item=item,
                            owner=item.PersonalInfo,
                            admin_user=request.user.username,
                            action_type='transfer',
                            proposed_changes={
                                'PersonalInfo': {
                                    'old': f"{item.PersonalInfo.name} {item.PersonalInfo.family}",
                                    'new': f"{to_person.name} {to_person.family}",
                                    'old_id': item.PersonalInfo.Personnel_number,
                                    'new_id': to_person.Personnel_number
                                }
                            },
                            description=description or f'درخواست انتقال کالا از {item.PersonalInfo.name} {item.PersonalInfo.family} به {to_person.name} {to_person.family}'
                        )
                        
                        # همزمان ایجاد درخواست برای مالک جدید
                        ItemChangeRequest.objects.create(
                            item=item,
                            owner=to_person,
                            admin_user=request.user.username,
                            action_type='receive',
                            proposed_changes={
                                'PersonalInfo': {
                                    'old': f"{item.PersonalInfo.name} {item.PersonalInfo.family}",
                                    'new': f"{to_person.name} {to_person.family}",
                                    'old_id': item.PersonalInfo.Personnel_number,
                                    'new_id': to_person.Personnel_number
                                }
                            },
                            description=description or f'درخواست دریافت کالا از {item.PersonalInfo.name} {item.PersonalInfo.family}'
                        )
                        
                        request_count += 1
                    elif not item.PersonalInfo:
                        # اگر کالا مالک ندارد، درخواست تخصیص ایجاد کن
                        ItemChangeRequest.objects.create(
                            item=item,
                            owner=to_person,
                            admin_user=request.user.username,
                            action_type='assign',
                            proposed_changes={
                                'PersonalInfo': {
                                    'old': None,
                                    'new': f"{to_person.name} {to_person.family}",
                                    'old_id': None,
                                    'new_id': to_person.Personnel_number
                                }
                            },
                            description=description or f'درخواست تخصیص دسته‌ای کالا {item.Technical_items} به {to_person.name} {to_person.family}'
                        )
                        
                        direct_count += 1
                        
                except Items.DoesNotExist:
                    continue
            
            if request_count > 0:
                messages.warning(request, 
                    f'{request_count} درخواست انتقال برای تایید مالکان فعلی و جدید ارسال شد. '
                    f'کالاها پس از تایید هر دو نفر منتقل خواهند شد.'
                )
            if direct_count > 0:
                messages.warning(request, 
                    f'{direct_count} درخواست تخصیص کالاهای بدون مالک برای تایید {to_person.name} {to_person.family} ارسال شد. '
                    f'کالاها پس از تایید مالک جدید تخصیص خواهند یافت.'
                )
                
        except PersonalInfo.DoesNotExist:
            messages.error(request, 'شخص مقصد یافت نشد.')
        except Exception as e:
            messages.error(request, f'خطا در انتقال کالاها: {str(e)}')
    
    return redirect('account:home')