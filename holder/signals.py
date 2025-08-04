from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from .models import Items, ItemHistory


# متغیر سراسری برای کنترل signal
_skip_signal = False

def skip_signals():
    """تابع برای غیرفعال کردن موقت signal ها"""
    global _skip_signal
    _skip_signal = True

def enable_signals():
    """تابع برای فعال کردن مجدد signal ها"""
    global _skip_signal
    _skip_signal = False


@receiver(pre_save, sender=Items)
def track_item_changes(sender, instance, **kwargs):
    """
    این تابع تغییرات در کالاها را پیگیری می‌کند
    اما فقط برای کالاهایی که مالک ندارند یا تغییر مجاز است
    """
    global _skip_signal
    if _skip_signal:
        return
        
    # بررسی اینکه آیا این یک رکورد جدید است یا خیر
    if instance.pk:  # اگر pk وجود داشته باشد، یعنی کالا از قبل وجود دارد و در حال بروزرسانی است
        try:
            # دریافت اطلاعات قبلی کالا
            old_instance = Items.objects.get(pk=instance.pk)
            
            # بررسی تغییر مالک کالا
            if old_instance.PersonalInfo != instance.PersonalInfo:
                # اگر کالا قبلاً مالک داشته و حالا تغییر می‌کند
                # این تغییر باید از طریق سیستم تایید انجام شود
                if old_instance.PersonalInfo and not hasattr(instance, '_approved_transfer'):
                    # جلوگیری از تغییر غیرمجاز - کالا را به حالت قبلی برگردان
                    instance.PersonalInfo = old_instance.PersonalInfo
                    return
                
                # اگر کالا مالک نداشته یا تغییر مجاز است، تاریخچه ثبت شود
                if not old_instance.PersonalInfo or hasattr(instance, '_approved_transfer'):
                    # تعیین تو��یحات بر اساس وضعیت مالکان
                    if old_instance.PersonalInfo and instance.PersonalInfo:
                        description = f'کالا از {old_instance.PersonalInfo.name} {old_instance.PersonalInfo.family} به {instance.PersonalInfo.name} {instance.PersonalInfo.family} منتقل شد.'
                    elif old_instance.PersonalInfo and not instance.PersonalInfo:
                        description = f'کالا از {old_instance.PersonalInfo.name} {old_instance.PersonalInfo.family} به انبار منتقل شد.'
                    elif not old_instance.PersonalInfo and instance.PersonalInfo:
                        description = f'کالا از انبار به {instance.PersonalInfo.name} {instance.PersonalInfo.family} منتقل شد.'
                    else:
                        description = 'تغییر در وضعیت کالا'
                    
                    # ثبت رکورد جدید در تاریخچه فقط اگر توسط signal انجام شده
                    if not hasattr(instance, '_approved_transfer'):
                        ItemHistory.objects.create(
                            item=instance,
                            from_person=old_instance.PersonalInfo,
                            to_person=instance.PersonalInfo,
                            action_type='transfer',
                            description=description
                        )
                        
        except Items.DoesNotExist:
            pass


@receiver(post_save, sender=Items)
def create_item_history(sender, instance, created, **kwargs):
    """
    ایجاد رکورد تاریخچه برای کالاهای جدید
    """
    global _skip_signal
    if _skip_signal:
        return
        
    if created:  # اگر کالا جدید ایجاد شده است
        if instance.PersonalInfo:
            # اگر کالا به شخصی تخصیص داده شده است
            ItemHistory.objects.create(
                item=instance,
                to_person=instance.PersonalInfo,
                action_type='assign',
                description=f'کالا به {instance.PersonalInfo.name} {instance.PersonalInfo.family} تخصیص داده شد.'
            )
        else:
            # اگر کالا بدون تخصیص به شخص خاص ایجاد شده است
            ItemHistory.objects.create(
                item=instance,
                to_person=None,
                action_type='assign',
                description='کالا بدون تخصیص به شخص خاص ایجاد شد.'
            )