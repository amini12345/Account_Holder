from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from .models import Items, ItemHistory


@receiver(pre_save, sender=Items)
def track_item_changes(sender, instance, **kwargs):
    """
    این تابع تغییرات در کالاها را پیگیری می‌کند و در صورت تغییر مالک کالا، آن را در تاریخچه ثبت می‌کند
    """
    # بررسی اینکه آیا این یک رکورد جدید است یا خیر
    if instance.pk:  # اگر pk وجود داشته باشد، یعنی کالا از قبل وجود دارد و در حال بروزرسانی است
        try:
            # دریافت اطلاعات قبلی کالا
            old_instance = Items.objects.get(pk=instance.pk)
            
            # بررسی تغییر مالک کالا
            if old_instance.PersonalInfo != instance.PersonalInfo:
                # تعیین توضیحات بر اساس وضعیت مالکان
                if old_instance.PersonalInfo and instance.PersonalInfo:
                    description = f'کالا از {old_instance.PersonalInfo.name} {old_instance.PersonalInfo.family} به {instance.PersonalInfo.name} {instance.PersonalInfo.family} منتقل شد.'
                elif old_instance.PersonalInfo and not instance.PersonalInfo:
                    description = f'کالا از {old_instance.PersonalInfo.name} {old_instance.PersonalInfo.family} به انبار منتقل شد.'
                elif not old_instance.PersonalInfo and instance.PersonalInfo:
                    description = f'کالا از انبار به {instance.PersonalInfo.name} {instance.PersonalInfo.family} منتقل شد.'
                else:
                    description = 'تغییر در وضعیت کالا'
                
                # ثبت رکورد جدید در تاریخچه
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