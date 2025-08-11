from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.http import JsonResponse
from holder.models import Items, PersonalInfo
import json


@login_required
def add_selected_items(request):
    """افزودن کالاهای انتخاب شده از مقایسه Excel به دیتابیس"""
    if request.method != 'POST':
        messages.error(request, 'روش درخواست نامعتبر است.')
        return redirect('account:import_excel')

    selected_items = request.POST.getlist('selected_items')
    
    if not selected_items:
        messages.error(request, 'هیچ کالایی انتخاب نشده است.')
        return redirect('account:import_excel')

    success_count = 0
    error_count = 0
    errors = []

    try:
        with transaction.atomic():
            for item_index in selected_items:
                try:
                    # دریافت داده‌های کالا از فرم
                    item_data = {
                        'item_name': request.POST.get(f'item_{item_index}_item_name', '').strip(),
                        'item_type': request.POST.get(f'item_{item_index}_item_type', '').strip(),
                        'brand': request.POST.get(f'item_{item_index}_brand', '').strip(),
                        'product_code': request.POST.get(f'item_{item_index}_product_code', '').strip(),
                        'serial_number': request.POST.get(f'item_{item_index}_serial_number', '').strip(),
                        'status_main': request.POST.get(f'item_{item_index}_status_main', '').strip(),
                        'status_sub': request.POST.get(f'item_{item_index}_status_sub', '').strip(),
                        'number': request.POST.get(f'item_{item_index}_number', '1').strip(),
                        'holder_info': request.POST.get(f'item_{item_index}_holder_info', '').strip(),
                        'configuration': request.POST.get(f'item_{item_index}_configuration', '').strip(),
                        'row': request.POST.get(f'item_{item_index}_row', '').strip(),
                    }

                    # اعتبارسنجی داده‌های ضروری
                    if not item_data['product_code']:
                        errors.append(f"ردیف {item_data['row']}: کد محصول الزامی است")
                        error_count += 1
                        continue

                    # تبدیل نوع کالا به مقادیر مدل
                    item_type_mapping = {
                        'فنی': 'Technical',
                        'غیر فنی': 'Non-technical',
                        'Technical': 'Technical',
                        'Non-technical': 'Non-technical'
                    }
                    
                    model_item_type = item_type_mapping.get(item_data['item_type'], 'Technical')

                    # تبدیل وضعیت اصلی
                    status_mapping = {
                        'سخت افزار': 'hardware',
                        'تحویل': 'Delivery', 
                        'انبار': 'warehouse',
                        'hardware': 'hardware',
                        'Delivery': 'Delivery',
                        'warehouse': 'warehouse'
                    }
                    
                    model_status = status_mapping.get(item_data['status_main'], 'warehouse')

                    # تبدیل زیر وضعیت
                    sub_status_mapping = {
                        'تعمیر': 'repair',
                        'ارتقا': 'upgrade',
                        'ارجاع': 'external',
                        'داخل': 'internal',
                        'آماده بکار': 'ready',
                        'عودتی سالم': 'returned_good',
                        'عودتی فرسوده': 'returned_worn',
                        'repair': 'repair',
                        'upgrade': 'upgrade',
                        'external': 'external',
                        'internal': 'internal',
                        'ready': 'ready',
                        'returned_good': 'returned_good',
                        'returned_worn': 'returned_worn'
                    }
                    
                    model_sub_status = sub_status_mapping.get(item_data['status_sub'], None) if item_data['status_sub'] else None

                    # تبدیل تعداد به عدد
                    try:
                        number = int(item_data['number']) if item_data['number'] else 1
                    except ValueError:
                        number = 1

                    # یافتن دارنده حساب (اختیاری)
                    personal_info = None
                    if item_data['holder_info']:
                        # جستجو بر اساس شماره پرسنلی یا نام
                        try:
                            # اگر شماره پرسنلی است (9 رقم)
                            if item_data['holder_info'].isdigit() and len(item_data['holder_info']) == 9:
                                personal_info = PersonalInfo.objects.get(Personnel_number=item_data['holder_info'])
                            else:
                                # جستجو بر اساس نام و نام خانوادگی
                                name_parts = item_data['holder_info'].split()
                                if len(name_parts) >= 2:
                                    personal_info = PersonalInfo.objects.filter(
                                        name__icontains=name_parts[0],
                                        family__icontains=name_parts[1]
                                    ).first()
                        except PersonalInfo.DoesNotExist:
                            pass

                    # بررسی تکراری بودن شماره سریال فقط برای کالاهای فنی
                    if item_data['serial_number'] and model_item_type == 'Technical':
                        if Items.objects.filter(serial_number=item_data['serial_number']).exists():
                            errors.append(f"ردیف {item_data['row']}: شماره سریال '{item_data['serial_number']}' قبلاً در سیستم موجود است")
                            error_count += 1
                            continue

                    # ایجاد کالای جدید
                    # برای کالاهای غیر فنی، شماره سریال همیشه None است
                    serial_number_value = None
                    if model_item_type == 'Technical' and item_data['serial_number']:
                        serial_number_value = item_data['serial_number']
                    
                    new_item = Items(
                        Technical_items=item_data['item_name'] or None,
                        type_Item=model_item_type,
                        brand=item_data['brand'] or None,
                        Product_code=item_data['product_code'],
                        serial_number=serial_number_value,
                        status_item=model_status,
                        status_sub_item=model_sub_status,
                        Number=number,
                        Configuration=item_data['configuration'] or None,
                        PersonalInfo=personal_info
                    )

                    # ذخیره کالا
                    new_item.save()
                    success_count += 1

                except Exception as e:
                    error_count += 1
                    row = item_data.get('row', item_index)
                    errors.append(f"ردیف {row}: خطا در ذخیره - {str(e)}")

        # نمایش نتایج
        if success_count > 0:
            messages.success(request, f'{success_count} کالا با موفقیت به دیتابیس اضافه شد.')
        
        if error_count > 0:
            error_message = f'{error_count} کالا به دلیل خطا اضافه نشد:'
            for error in errors[:5]:  # نمایش حداکثر 5 خطای اول
                error_message += f'\n• {error}'
            if len(errors) > 5:
                error_message += f'\n... و {len(errors) - 5} خطای دیگر'
            messages.error(request, error_message)

    except Exception as e:
        messages.error(request, f'خطای کلی در پردازش: {str(e)}')

    return redirect('account:import_excel')


@login_required
def get_item_preview(request):
    """پیش‌نمایش کالا قبل از افزودن به دیتابیس"""
    if request.method != 'POST':
        return JsonResponse({'error': 'روش درخواست نامعتبر است'}, status=400)

    try:
        item_data = json.loads(request.body)
        
        # پردازش و تبدیل داده‌ه��
        processed_data = {
            'item_name': item_data.get('item_name', ''),
            'item_type': item_data.get('item_type', ''),
            'brand': item_data.get('brand', ''),
            'product_code': item_data.get('product_code', ''),
            'serial_number': item_data.get('serial_number', ''),
            'status_main': item_data.get('status_main', ''),
            'status_sub': item_data.get('status_sub', ''),
            'number': item_data.get('number', 1),
            'configuration': item_data.get('configuration', ''),
            'holder_info': item_data.get('holder_info', ''),
        }

        # بررسی اعتبار
        warnings = []
        
        if not processed_data['product_code']:
            warnings.append('کد محصول الزامی است')
        
        # بررسی شماره سریال تکراری فقط برای کالاهای فنی
        if processed_data['serial_number'] and processed_data['item_type'] in ['فنی', 'Technical']:
            if Items.objects.filter(serial_number=processed_data['serial_number']).exists():
                warnings.append('شماره سریال تکراری است')

        return JsonResponse({
            'success': True,
            'data': processed_data,
            'warnings': warnings
        })

    except Exception as e:
        return JsonResponse({'error': f'خطا در پردازش: {str(e)}'}, status=500)