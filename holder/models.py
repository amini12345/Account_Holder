from django.db import models
from django.utils import timezone
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError
from extensions.utils import jalali_converter

class PersonalInfo(models.Model):
    STATUS_CHOICES = (
        ('d', 'دیپلم'),
        ('a', 'کارشناسی ناپیوسته'),
        ('b', 'کارشناسی'),
        ('m', 'کارشناسی ارشد'),
        ('p', 'دکتری'),
        ('o', 'سایر')
    )
    name = models.CharField(max_length=100, verbose_name="نام")
    family = models.CharField(max_length=100, verbose_name="نام خانوادگی") 
    Personnel_number = models.CharField(max_length=9, validators=[RegexValidator(regex=r'^\d{9}$')], unique=True,primary_key=True,verbose_name="شماره پرسنلی") 
    National_ID = models.CharField(max_length=10,unique=True,verbose_name="کد ملی",validators=[RegexValidator(regex=r'^\d{10}$')])
    date_of_birth = models.DateField(verbose_name="تاریخ تولد")
    email = models.EmailField(max_length=254, verbose_name="ایمیل",blank=True, null=True, help_text="اختیاری") 
    phone_number = models.CharField(max_length=16, verbose_name="شماره همراه") 
    date_created = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ثبت نام")
    Educational_degree = models.CharField(max_length=10, verbose_name="مدرک تحصیلی", choices=STATUS_CHOICES)   
    password = models.CharField(max_length=100, verbose_name="رمز عبور")

    def __str__(self):
        return f"شماره پرسنلی:{self.Personnel_number} - نام و نام خانوادگی:{self.name} {self.family}"
    
    def jinfo(self):
        return jalali_converter(self.date_of_birth)
    jinfo.short_description = "تاریخ تولد "

    class Meta:
        verbose_name = "دارنده حساب"
        verbose_name_plural = "دارندگان حساب"

class Items(models.Model):
    Technical_items = models.CharField(max_length=100,blank=True , null=True, verbose_name="نام کالا") 
    TYPE_CHOICES = [('Technical', 'فنی'),('Non-technical', 'غیر فنی')] 
    type_Item = models.CharField(max_length=50,choices=TYPE_CHOICES, verbose_name="نوع کالا") 
    STATUS_CHOICES = [('hardware','سخت افزار'),('Delivery','تحویل'),('warehouse','انبار')]  
    status_item =  models.CharField(max_length=50,choices=STATUS_CHOICES, verbose_name="وضعیت کالا")
    Number = models.IntegerField(verbose_name="تعداد کالا", default=1, blank=True, null=True) 
    # زیرمجموعه‌های وضعیت کالا
    STATUS_SUB_MAPPING = {
        'hardware': [
            ('repair', 'تعمیر'),
            ('upgrade', 'ارتقا'),
        ],
        'Delivery': [
            ('external', 'خارج'),
            ('internal', 'داخل'),
        ],
        'warehouse': [
            ('ready', 'آماده بکار'),
            ('returned_good', 'عودتی سالم'),
            ('returned_worn', 'عودتی فرسوده'),
        ],
    }
    status_sub_item = models.CharField(max_length=50,choices=[choice for sublist in STATUS_SUB_MAPPING.values() for choice in sublist],blank=True,null=True,verbose_name="زیر مجموعه وضعیت")
    brand = models.CharField(max_length=100, verbose_name="برند", blank=True, null=True)
    Configuration = models.TextField(verbose_name="پیکربندی", blank=True, null=True)
    serial_number = models.CharField(max_length=100, unique=True,blank=True, null=True,verbose_name="شماره سریال") 
    Product_code = models.CharField(max_length=100, verbose_name="کد محصول") 
    register_date = models.DateTimeField(auto_now_add=True) 
    update_date = models.DateTimeField(default=timezone.now,verbose_name="تاریخ بروزرسانی")    
    PersonalInfo = models.ForeignKey(PersonalInfo, on_delete=models.CASCADE, related_name='items', blank=True, null=True, verbose_name="دارنده حساب")  

    def clean(self):
        """
        اعتبارسنجی مدل: بررسی اینکه زیرمجموعه انتخاب‌شده، با وضعیت اصلی مطابقت دارد.
        """
        if self.status_item and self.status_sub_item:
            valid_sub_choices = self.STATUS_SUB_MAPPING.get(self.status_item, [])
            if self.status_sub_item not in [choice[0] for choice in valid_sub_choices]:
                raise ValidationError(
                    {'status_sub_item': 'زیر مجموعه انتخاب‌شده معتبر نیست.'}
                )

    def save(self, *args, **kwargs):
        self.clean()  # اجرای اعتبارسنجی
        super().save(*args, **kwargs)

    def __str__(self):
        # نمایش وضعیت کامل (اصلی + زیر مجموعه)
        status_display = self.get_status_item_display()
        if self.status_sub_item:
            status_display += f" - {self.get_status_sub_item_display()}"
            
        if self.PersonalInfo:
            return f"نام کالا:{self.Technical_items} - نوع کالا:{self.type_Item} - کد کالا:{self.Product_code} - شماره سریال:{self.serial_number} - وضعیت کالا:{status_display} - دارنده حساب:{self.PersonalInfo.name} {self.PersonalInfo.family}"
        else:
            return f"نام کالا:{self.Technical_items} - نوع کالا:{self.type_Item} - کد کالا:{self.Product_code} - شماره سریال:{self.serial_number} - وضعیت کالا:{status_display} - دارنده حساب: بدون دارنده"
    def jinfo(self):
        return jalali_converter(self.register_date)
    jinfo.short_description = "تاریخ ثبت نام"
    class Meta:
        verbose_name = "کالا"
        verbose_name_plural = "کالاها"


class ItemHistory(models.Model):
    ACTION_CHOICES = [
        ('assign', 'تخصیص'),
        ('transfer', 'انتقال'),
        ('return', 'بازگشت'),
        ('maintenance', 'تعمیر'),
        ('other', 'سایر')
    ]
    
    item = models.ForeignKey(Items, on_delete=models.CASCADE, related_name='history', verbose_name="کالا")
    from_person = models.ForeignKey(PersonalInfo, on_delete=models.SET_NULL, null=True, blank=True, related_name='given_items_history', verbose_name="از شخص")
    to_person = models.ForeignKey(PersonalInfo, on_delete=models.SET_NULL, null=True, blank=True, related_name='received_items_history', verbose_name="به شخص")
    action_date = models.DateTimeField(default=timezone.now, verbose_name="تاریخ اقدام")
    action_type = models.CharField(max_length=20, choices=ACTION_CHOICES, verbose_name="نوع اقدام")
    description = models.TextField(blank=True, null=True, verbose_name="توضیحات")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ثبت")
    
    def __str__(self):
        from_name = f"{self.from_person.name} {self.from_person.family}" if self.from_person else "---"
        to_name = f"{self.to_person.name} {self.to_person.family}" if self.to_person else "---"
        return f"{self.item.Technical_items} - از: {from_name} - به: {to_name} - {self.get_action_type_display()} - {self.action_date}"
    
    def jinfo(self):
        return jalali_converter(self.action_date)
    jinfo.short_description = "تاریخ اقدام"
    
    class Meta:
        verbose_name = "تاریخچه کالا"
        verbose_name_plural = "تاریخچه کالاها"
        ordering = ['-action_date']


class Documents(models.Model):
    name_document = models.CharField(max_length=100, verbose_name="نام مدرک")
    start_date = models.DateField(verbose_name="تاریخ شروع")
    end_date = models.DateField(verbose_name="تاریخ پایان")
    Training_hours = models.IntegerField(verbose_name="ساعت آموزشی")
    Training_costs = models.DecimalField(max_digits=10, decimal_places=0, verbose_name="(ریال)هزینه آموزشی")
    Training_location = models.CharField(max_length=100, verbose_name="محل آموزشی")
    STATUS_CHOICES = [('online', 'اینترنتی'),('offline', 'حضوری')]
    Type_of_training = models.CharField(max_length=50, verbose_name="نوع آموزش",choices=STATUS_CHOICES) 
    register_date = models.DateTimeField(auto_now_add=True)
    update_date = models.DateTimeField(default=timezone.now) 
    PersonalInfo = models.ManyToManyField(PersonalInfo,related_name='documents')    
    
    def __str__(self):
        return f"{self.name_document} - {self.Training_location} - {self.Type_of_training}"
    
    def jinfo(self):
        return jalali_converter(self.start_date)
    jinfo.short_description = "تاریخ مدارک"
    
    def jinfo1(self):
        return jalali_converter(self.end_date)
    jinfo.short_description = "تاریخ مدارک پایان"
    
    
    class Meta:
        verbose_name = "مدرک"
        verbose_name_plural = "مدارک"
        
        
class Mission(models.Model):
    types_of_missions = models.CharField(max_length=100, verbose_name="نوع ماموریت")
    Mission_Description = models.TextField(verbose_name="توضیحات(موضوع) ماموریت") 
    mission_location = models.CharField(max_length=100, verbose_name="محل(مقصد) ماموریت")
    start_date = models.DateField(verbose_name="تاریخ شروع")
    time_frame = models.CharField(max_length=100,verbose_name="بازه زمانی ماموریت",help_text="لطفا تعداد روز ماموریت را وارد کنید")
    register_date = models.DateTimeField(auto_now_add=True)
    update_date = models.DateTimeField(default=timezone.now)  
    PersonalInfo = models.ManyToManyField(PersonalInfo,related_name='missions',verbose_name="حاضرین در ماموریت")

    def __str__(self):
        return f"{self.mission_location} - {self.start_date} - {self.time_frame}"    
    
    def jinfo(self):
        return jalali_converter(self.start_date)
    jinfo.short_description = "تاریخ ماموریت"
    

    class Meta:
        verbose_name = "ماموریت"
        verbose_name_plural = "ماموریت ها"
        
class Results(models.Model):
    Date_of_submission = models.DateTimeField(default=timezone.now,verbose_name="تاریخ تحویل")
    Internal_meetings = models.IntegerField( verbose_name="جلسات داخلی")  
    Meeting_Minutes = models.TextField(verbose_name="صورت جلسات")
    register_date = models.DateTimeField(auto_now_add=True)
    update_date = models.DateTimeField(default=timezone.now)  
    PersonalInfo = models.ForeignKey(PersonalInfo, on_delete=models.CASCADE, related_name='results')    

    def __str__(self):
        return f"{self.Date_of_submission} - {self.Meeting_Minutes} - {self.Internal_meetings} "

    class Meta:
        verbose_name = "نتیجه"
        verbose_name_plural = "نتایج"


class ItemChangeRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'در انتظار تایید'),
        ('approved', 'تایید شده'),
        ('rejected', 'رد شده'),
    ]
    
    ACTION_CHOICES = [
        ('edit', 'ویرایش'),
        ('transfer', 'انتقال'),
        ('assign', 'تخصیص'),
        ('remove', 'حذف'),
        ('delete', 'حذف'),
        ('status_change', 'تغییر وضعیت'),
    ]
    
    item = models.ForeignKey(Items, on_delete=models.CASCADE, related_name='change_requests', verbose_name="کالا")
    owner = models.ForeignKey(PersonalInfo, on_delete=models.CASCADE, related_name='item_change_requests', verbose_name="مالک کالا")
    admin_user = models.CharField(max_length=150, verbose_name="کاربر مدیر")  # نام کاربر مدیر که درخواست داده
    action_type = models.CharField(max_length=20, choices=ACTION_CHOICES, verbose_name="نوع تغییر")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name="وضعیت درخواست")
    
    # فیلدهای تغییرات پیشنهادی
    proposed_changes = models.JSONField(verbose_name="تغییرات پیشنهادی", help_text="تغییرات پیشنهادی در قالب JSON")
    description = models.TextField(verbose_name="توضیحات", help_text="توضیحات مربوط به تغییر")
    
    # تاریخ‌ها
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")
    responded_at = models.DateTimeField(null=True, blank=True, verbose_name="تاریخ پاسخ")
    
    def __str__(self):
        return f"درخواست {self.get_action_type_display()} برای {self.item.Technical_items} - {self.get_status_display()}"
    
    def jinfo(self):
        return jalali_converter(self.created_at)
    jinfo.short_description = "تاریخ ایجاد"
    
    class Meta:
        verbose_name = "درخواست تغییر کالا"
        verbose_name_plural = "درخواست‌های تغییر کالا"
        ordering = ['-created_at']


