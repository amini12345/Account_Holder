from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse
from django.db.models import Q
from holder.models import Items, PersonalInfo
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.pdfbase import pdfmetrics

# Import های سازگار با نسخه‌های مختلف ReportLab
try:
    from reportlab.pdfbase.ttfonts import TTFont
except ImportError:
    # برای نسخه‌های جدیدتر ReportLab
    try:
        from reportlab.lib.fonts import TTFont
    except ImportError:
        TTFont = None

try:
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT
except ImportError:
    # برای نسخه‌های جدیدتر ReportLab
    try:
        from reportlab.lib.styles import TA_CENTER, TA_RIGHT
    except ImportError:
        # تعریف ثابت‌ها به صورت دستی
        TA_CENTER = 1
        TA_RIGHT = 2

from datetime import datetime
import os
import urllib.parse

# برای پشتیبانی از متن فارسی
try:
    from arabic_reshaper import reshape
    from bidi.algorithm import get_display
    PERSIAN_SUPPORT = True
except ImportError:
    PERSIAN_SUPPORT = False
    print("برای نمایش صحیح فارسی، لطفاً پکیج‌های arabic-reshaper و python-bidi را نصب کنید:")
    print("pip install arabic-reshaper python-bidi")

def fix_persian_text(text):
    """تصحیح متن فارسی برای نمایش صحیح در PDF"""
    if not text or not PERSIAN_SUPPORT:
        return text
    
    try:
        # تبدیل متن فارسی به فرمت قابل نمایش
        reshaped_text = reshape(text)
        bidi_text = get_display(reshaped_text)
        return bidi_text
    except Exception as e:
        print(f"خطا در تصحیح متن فارسی: {e}")
        return text

# تنظیم فونت فارسی
def setup_persian_font():
    """تنظیم فونت فارسی برای PDF"""
    if TTFont is None:
        return 'Helvetica'
    
    try:
        # مسیرهای مختلف فونت‌های فارسی
        font_paths = [
            # فونت‌های فارسی در Linux
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/TTF/NotoSansFarsi-Regular.ttf",
            "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
            # فونت‌های در macOS
            "/System/Library/Fonts/Arial.ttf",
            "/Library/Fonts/Arial.ttf",
            # فونت‌های در Windows
            "C:\\Windows\\Fonts\\arial.ttf",
            "C:\\Windows\\Fonts\\tahoma.ttf",
        ]
        
        for font_path in font_paths:
            if os.path.exists(font_path):
                try:
                    pdfmetrics.registerFont(TTFont('PersianFont', font_path))
                    return 'PersianFont'
                except Exception as e:
                    continue
        
        # اگر هیچ فونت خاصی پیدا نشد، از فونت پیش‌فرض استفاده کن
        return 'Helvetica'
    except Exception as e:
        print(f"خطا در تنظیم فونت: {e}")
        return 'Helvetica'

@login_required
def export_pdf(request):
    """خروجی PDF از لیست کالاها با در نظر گیری جستجو و فیلترها"""
    
    # دریافت همان queryset که در HomeView استفاده می‌شود
    queryset = Items.objects.select_related('PersonalInfo').all()
    search_query = request.GET.get('search')
    brand_search = request.GET.get('brand_search')
    serial_search = request.GET.get('serial_search')
    code_search = request.GET.get('code_search')
    holder_search = request.GET.get('holder_search')
    type_filter = request.GET.get('type_filter')
    status_filter = request.GET.get('status_filter')
    sub_status_filter = request.GET.get('sub_status_filter')
    
    # اعمال فیلترها (همان منطق HomeView)
    if search_query:
        queryset = queryset.filter(Technical_items__icontains=search_query)
    if brand_search:
        queryset = queryset.filter(brand__icontains=brand_search)
    if serial_search:
        queryset = queryset.filter(serial_number__icontains=serial_search)
    if code_search:
        queryset = queryset.filter(Product_code__icontains=code_search)
    if holder_search:
        queryset = queryset.filter(
            Q(PersonalInfo__name__icontains=holder_search) |
            Q(PersonalInfo__family__icontains=holder_search) |
            Q(PersonalInfo__Personnel_number__icontains=holder_search)
        )
    if type_filter:
        queryset = queryset.filter(type_Item=type_filter)
    if status_filter:
        queryset = queryset.filter(status_item=status_filter)
    if sub_status_filter:
        queryset = queryset.filter(status_sub_item=sub_status_filter)
    
    queryset = queryset.order_by('-register_date')
    
    # تنظیم نام فایل
    current_time = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename_parts = ['goods_list']
    
    # اضافه کردن فیلترها به نام فایل
    if search_query:
        filename_parts.append(f'name_{search_query}')
    if brand_search:
        filename_parts.append(f'brand_{brand_search}')
    if serial_search:
        filename_parts.append(f'serial_{serial_search}')
    if code_search:
        filename_parts.append(f'code_{code_search}')
    if holder_search:
        filename_parts.append(f'holder_{holder_search}')
    if type_filter:
        type_name = 'technical' if type_filter == 'Technical' else 'non_technical'
        filename_parts.append(f'type_{type_name}')
    if status_filter:
        status_names = {
            'hardware': 'hardware',
            'Delivery': 'delivery',
            'warehouse': 'warehouse'
        }
        filename_parts.append(f'status_{status_names.get(status_filter, status_filter)}')
    if sub_status_filter:
        sub_status_names = {
            'repair': 'repair',
            'upgrade': 'upgrade',
            'external': 'external',
            'internal': 'internal',
            'ready': 'ready',
            'returned_good': 'returned_good',
            'returned_worn': 'returned_worn'
        }
        filename_parts.append(f'substatus_{sub_status_names.get(sub_status_filter, sub_status_filter)}')
    
    filename_parts.append(current_time)
    filename = '_'.join(filename_parts) + '.pdf'
    
    # ایجاد response با تنظیمات صحیح برای دانلود
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    
    # تنظیم فونت
    font_name = setup_persian_font()
    
    # ایجاد PDF
    doc = SimpleDocTemplate(
        response,
        pagesize=landscape(A4),
        rightMargin=0.5*inch,
        leftMargin=0.5*inch,
        topMargin=0.5*inch,
        bottomMargin=0.5*inch
    )
    
    # تنظیم استایل‌ها
    styles = getSampleStyleSheet()
    
    # استایل عنوان
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontName=font_name,
        fontSize=16,
        alignment=TA_CENTER,
        spaceAfter=20,
        textColor=colors.darkblue
    )
    
    # استایل متن عادی
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontName=font_name,
        fontSize=8,
        alignment=TA_CENTER
    )
    
    # محتوای PDF
    story = []
    
    # عنوان
    title_text = fix_persian_text("گزارش لیست کالاها")
    title = Paragraph(title_text, title_style)
    story.append(title)
    
    # اطلاعات گزارش
    report_info = f"تاریخ تولید گزارش: {datetime.now().strftime('%Y/%m/%d %H:%M')}"
    if queryset.count() > 0:
        report_info += f" | تعداد کالاها: {queryset.count()}"
    
    report_info = fix_persian_text(report_info)
    info_para = Paragraph(report_info, normal_style)
    story.append(info_para)
    story.append(Spacer(1, 20))
    
    # اگر فیلتری اعمال شده، نمایش آن
    if any([search_query, brand_search, serial_search, code_search, holder_search, type_filter, status_filter, sub_status_filter]):
        filter_info = "فیلترهای اعمال شده: "
        filters = []
        if search_query:
            filters.append(f"نام کالا: {search_query}")
        if brand_search:
            filters.append(f"برند: {brand_search}")
        if serial_search:
            filters.append(f"شماره سریال: {serial_search}")
        if code_search:
            filters.append(f"کد محصول: {code_search}")
        if holder_search:
            filters.append(f"دارنده: {holder_search}")
        if type_filter:
            type_name = 'فنی' if type_filter == 'Technical' else 'غیر فنی'
            filters.append(f"نوع: {type_name}")
        if status_filter:
            status_names = {
                'hardware': 'سخت افزار (تعمیری)',
                'Delivery': 'تحویل',
                'warehouse': 'انبار'
            }
            filters.append(f"وضعیت: {status_names.get(status_filter, status_filter)}")
        if sub_status_filter:
            sub_status_names = {
                'repair': 'تعمیر',
                'upgrade': 'ارتقا',
                'external': 'خارج',
                'internal': 'داخل',
                'ready': 'آماده بکار',
                'returned_good': 'عودتی سالم',
                'returned_worn': 'عودتی فرسوده'
            }
            filters.append(f"زیر وضعیت: {sub_status_names.get(sub_status_filter, sub_status_filter)}")
        
        filter_info += " | ".join(filters)
        filter_info = fix_persian_text(filter_info)
        filter_para = Paragraph(filter_info, normal_style)
        story.append(filter_para)
        story.append(Spacer(1, 15))
    
    if queryset.exists():
        # ایجاد جدول
        data = []
        
        # هدرهای جدول
        headers = [
            fix_persian_text('ردیف'), 
            fix_persian_text('نام کالا'), 
            fix_persian_text('نوع'), 
            fix_persian_text('برند'), 
            fix_persian_text('وضعیت'), 
            fix_persian_text('شماره سریال'), 
            fix_persian_text('کد محصول'), 
            fix_persian_text('دارنده حساب'), 
            fix_persian_text('تاریخ ثبت')
        ]
        data.append(headers)
        
        # داده‌های جدول
        for index, item in enumerate(queryset, 1):
            # نام کالا
            item_name = fix_persian_text(item.Technical_items or 'تعریف نشده')
            
            # نوع کالا
            item_type = fix_persian_text('فنی' if item.type_Item == 'Technical' else 'غیر فنی' if item.type_Item == 'Non-technical' else 'نامشخص')
            
            # برند
            brand = fix_persian_text(item.brand or 'تعریف نشده')
            
            # وضعیت
            status_display = {
                'hardware': 'سخت افزار',
                'Delivery': 'تحویل',
                'warehouse': 'انبار'
            }.get(item.status_item, 'نامشخص')
            
            if item.status_sub_item:
                sub_status_display = {
                    'repair': 'تعمیر',
                    'upgrade': 'ارتقا',
                    'external': 'خارج',
                    'internal': 'داخل',
                    'ready': 'آماده بکار',
                    'returned_good': 'عودتی سالم',
                    'returned_worn': 'عودتی فرسوده'
                }.get(item.status_sub_item, item.status_sub_item)
                status_display += f" - {sub_status_display}"
            
            status_display = fix_persian_text(status_display)
            
            # شماره سریال
            serial = item.serial_number or 'ندارد'
            
            # کد محصول
            product_code = item.Product_code or 'ندارد'
            
            # دارنده حساب
            if item.PersonalInfo:
                holder = f"{item.PersonalInfo.name} {item.PersonalInfo.family}"
                holder = fix_persian_text(holder)
            else:
                holder = fix_persian_text('بدون دارنده')
            
            # تاریخ ثبت
            register_date = str(item.jinfo)
            
            row = [
                str(index),
                item_name[:20] + '...' if len(item_name) > 20 else item_name,
                item_type,
                brand[:15] + '...' if len(brand) > 15 else brand,
                status_display[:20] + '...' if len(status_display) > 20 else status_display,
                serial[:15] + '...' if len(serial) > 15 else serial,
                product_code[:12] + '...' if len(product_code) > 12 else product_code,
                holder[:20] + '...' if len(holder) > 20 else holder,
                register_date
            ]
            data.append(row)
        
        # ایجاد جدول
        table = Table(data, repeatRows=1)
        
        # استایل جدول
        table.setStyle(TableStyle([
            # استایل هدر
            ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), font_name),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('FONTNAME', (0, 1), (-1, -1), font_name),
            ('FONTSIZE', (0, 1), (-1, -1), 7),
            
            # خطوط جدول
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('LINEBELOW', (0, 0), (-1, 0), 2, colors.darkblue),
            
            # رنگ‌بندی ردیف‌ها
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
            
            # padding
            ('LEFTPADDING', (0, 0), (-1, -1), 3),
            ('RIGHTPADDING', (0, 0), (-1, -1), 3),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        
        story.append(table)
    else:
        # پیام عدم وجود داده
        no_data_text = fix_persian_text("هیچ کالایی با فیلترهای انتخاب شده یافت نشد.")
        no_data_para = Paragraph(no_data_text, normal_style)
        story.append(no_data_para)
    
    # ساخت PDF
    doc.build(story)
    
    return response

@login_required
def export_pdf_fields_selection(request):
    """صفحه انتخاب فیلدهای خروجی PDF"""
    context = {
        'search_query': request.GET.get('search', ''),
        'brand_search': request.GET.get('brand_search', ''),
        'serial_search': request.GET.get('serial_search', ''),
        'code_search': request.GET.get('code_search', ''),
        'holder_search': request.GET.get('holder_search', ''),
        'type_filter': request.GET.get('type_filter', ''),
        'status_filter': request.GET.get('status_filter', ''),
        'sub_status_filter': request.GET.get('sub_status_filter', ''),
    }
    return render(request, 'registration/pdf_fields_selection.html', context)

@login_required
def generate_pdf(request):
    """تولید فایل PDF با فیلدهای انتخاب شده"""
    if request.method != 'POST':
        return redirect('account:export_pdf_fields_selection')
    
    selected_fields = request.POST.getlist('selected_fields')
    if not selected_fields:
        messages.error(request, 'لطفاً حداقل یک فیلد را انتخاب کنید.')
        return redirect('account:export_pdf_fields_selection')
    
    # دریافت همان queryset که در HomeView استفاده می‌شود
    queryset = Items.objects.select_related('PersonalInfo').all()
    search_query = request.POST.get('search')
    brand_search = request.POST.get('brand_search')
    serial_search = request.POST.get('serial_search')
    code_search = request.POST.get('code_search')
    holder_search = request.POST.get('holder_search')
    type_filter = request.POST.get('type_filter')
    status_filter = request.POST.get('status_filter')
    sub_status_filter = request.POST.get('sub_status_filter')
    
    # اعمال فیلترها
    if search_query:
        queryset = queryset.filter(Technical_items__icontains=search_query)
    if brand_search:
        queryset = queryset.filter(brand__icontains=brand_search)
    if serial_search:
        queryset = queryset.filter(serial_number__icontains=serial_search)
    if code_search:
        queryset = queryset.filter(Product_code__icontains=code_search)
    if holder_search:
        queryset = queryset.filter(
            Q(PersonalInfo__name__icontains=holder_search) |
            Q(PersonalInfo__family__icontains=holder_search) |
            Q(PersonalInfo__Personnel_number__icontains=holder_search)
        )
    if type_filter:
        queryset = queryset.filter(type_Item=type_filter)
    if status_filter:
        queryset = queryset.filter(status_item=status_filter)
    if sub_status_filter:
        queryset = queryset.filter(status_sub_item=sub_status_filter)
    
    queryset = queryset.order_by('-register_date')
    
    # تعریف تمام فیلدهای ممکن
    all_fields = {
        'row_number': 'ردیف',
        'name': 'نام کالا',
        'type': 'نوع کالا',
        'brand': 'برند',
        'configuration': 'پیکربندی',
        'status': 'وضعیت کالا',
        'sub_status': 'زیر وضعیت',
        'serial': 'شماره سریال',
        'product_code': 'کد محصول',
        'holder': 'دارنده حساب',
        'register_date': 'تاریخ ثبت',
        'update_date': 'تاریخ بروزرسانی',
    }
    
    # فیلتر کردن فیلدهای انتخاب شده
    selected_field_configs = [(field, all_fields[field]) for field in selected_fields if field in all_fields]
    
    # تنظیم نام فایل
    current_time = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename_parts = ['goods_list_custom']
    
    # اضافه کردن فیلترها به نام فایل
    if search_query:
        filename_parts.append(f'name_{search_query}')
    if brand_search:
        filename_parts.append(f'brand_{brand_search}')
    if type_filter:
        type_name = 'technical' if type_filter == 'Technical' else 'non_technical'
        filename_parts.append(f'type_{type_name}')
    
    filename_parts.append(current_time)
    filename = '_'.join(filename_parts) + '.pdf'
    
    # ایجاد response با تنظیمات صحیح برای دانلود
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    
    # تنظیم فونت
    font_name = setup_persian_font()
    
    # ایجاد PDF
    doc = SimpleDocTemplate(
        response,
        pagesize=landscape(A4),
        rightMargin=0.5*inch,
        leftMargin=0.5*inch,
        topMargin=0.5*inch,
        bottomMargin=0.5*inch
    )
    
    # تنظیم استایل‌ها
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontName=font_name,
        fontSize=16,
        alignment=TA_CENTER,
        spaceAfter=20,
        textColor=colors.darkblue
    )
    
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontName=font_name,
        fontSize=8,
        alignment=TA_CENTER
    )
    
    # محتوای PDF
    story = []
    
    # عنوان
    title_text = fix_persian_text("گزارش لیست کالاها (فیلدهای انتخابی)")
    title = Paragraph(title_text, title_style)
    story.append(title)
    
    # اطلاعات گزارش
    report_info = f"تاریخ تولید گزارش: {datetime.now().strftime('%Y/%m/%d %H:%M')}"
    if queryset.count() > 0:
        report_info += f" | تعداد کالاها: {queryset.count()}"
    
    report_info = fix_persian_text(report_info)
    info_para = Paragraph(report_info, normal_style)
    story.append(info_para)
    story.append(Spacer(1, 20))
    
    if queryset.exists():
        # ایجاد جدول با فیلدهای انتخابی
        data = []
        
        # هدرهای جدول
        headers = [fix_persian_text(field_config[1]) for field_config in selected_field_configs]
        data.append(headers)
        
        # داده‌های جدول
        for index, item in enumerate(queryset, 1):
            row = []
            for field_key, field_label in selected_field_configs:
                value = get_pdf_field_value(item, field_key, index)
                # تصحیح متن فارسی
                if isinstance(value, str) and any('\u0600' <= char <= '\u06FF' for char in value):
                    value = fix_persian_text(value)
                # محدود کردن طول متن برای نمایش بهتر
                if len(str(value)) > 25:
                    value = str(value)[:22] + '...'
                row.append(str(value))
            data.append(row)
        
        # ایجاد جدول
        table = Table(data, repeatRows=1)
        
        # استایل جدول
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), font_name),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('FONTNAME', (0, 1), (-1, -1), font_name),
            ('FONTSIZE', (0, 1), (-1, -1), 7),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('LINEBELOW', (0, 0), (-1, 0), 2, colors.darkblue),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
            ('LEFTPADDING', (0, 0), (-1, -1), 3),
            ('RIGHTPADDING', (0, 0), (-1, -1), 3),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        
        story.append(table)
    else:
        no_data_text = fix_persian_text("هیچ کالایی با فیلترهای انتخاب شده یافت نشد.")
        no_data_para = Paragraph(no_data_text, normal_style)
        story.append(no_data_para)
    
    # ساخت PDF
    doc.build(story)
    
    return response

def get_pdf_field_value(item, field_key, row_index):
    """دریافت مقدار فیلد برای یک آیتم در PDF"""
    if field_key == 'row_number':
        return row_index
    elif field_key == 'name':
        return item.Technical_items or 'تعریف نشده'
    elif field_key == 'type':
        return 'فنی' if item.type_Item == 'Technical' else 'غیر فنی' if item.type_Item == 'Non-technical' else 'نامشخص'
    elif field_key == 'brand':
        return item.brand or 'تعریف نشده'
    elif field_key == 'configuration':
        return item.Configuration or 'ندارد'
    elif field_key == 'status':
        status_display = {
            'hardware': 'سخت افزار (تعمیری)',
            'Delivery': 'تحویل',
            'warehouse': 'انبار'
        }.get(item.status_item, 'نامشخص')
        return status_display
    elif field_key == 'sub_status':
        return item.get_status_sub_item_display() if item.status_sub_item else 'ندارد'
    elif field_key == 'serial':
        return item.serial_number or 'ندارد'
    elif field_key == 'product_code':
        return item.Product_code or 'ندارد'
    elif field_key == 'holder':
        if item.PersonalInfo:
            return f"{item.PersonalInfo.name} {item.PersonalInfo.family} ({item.PersonalInfo.Personnel_number})"
        else:
            return 'بدون دارنده'
    elif field_key == 'register_date':
        return str(item.jinfo)
    elif field_key == 'update_date':
        if item.update_date:
            return item.update_date.strftime('%Y/%m/%d %H:%M')
        else:
            return 'ندارد'
    else:
        return ''