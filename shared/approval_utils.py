"""
ابزارهای مشترک برای سیستم تایید درخواست‌ها
"""

from django.utils import timezone
from holder.models import Items, ItemHistory, PersonalInfo, ItemChangeRequest


def check_both_parties_approved(item, old_owner_id, new_owner_id):
    """
    بررسی اینکه آیا هر دو طرف انتقال تایید کرده‌اند
    
    Args:
        item: آبجکت کالا
        old_owner_id: شماره پرسنلی مالک قبلی
        new_owner_id: شماره پرسنلی مالک جدید
    
    Returns:
        bool: True اگر هر دو طرف تایید کرده باشند، در غیر این صورت False
    """
    # بررسی تایید مالک قبلی - باید درخواست transfer تایید شده باشد
    transfer_requests = ItemChangeRequest.objects.filter(
        item=item,
        owner__Personnel_number=old_owner_id,
        action_type='transfer',
        status='approved'
    )
    
    transfer_approved = False
    for req in transfer_requests:
        proposed_changes = req.proposed_changes or {}
        personal_info_changes = proposed_changes.get('PersonalInfo', {})
        if personal_info_changes.get('new_id') == new_owner_id:
            transfer_approved = True
            break
    
    # بررسی تایید مالک جدید - باید درخواست receive تایید شده باشد
    receive_requests = ItemChangeRequest.objects.filter(
        item=item,
        owner__Personnel_number=new_owner_id,
        action_type='receive',
        status='approved'
    )
    
    receive_approved = False
    for req in receive_requests:
        proposed_changes = req.proposed_changes or {}
        personal_info_changes = proposed_changes.get('PersonalInfo', {})
        if personal_info_changes.get('old_id') == old_owner_id:
            receive_approved = True
            break
    
    return transfer_approved and receive_approved


def approve_item_transfer(item, old_owner_id, new_owner_id, description=None):
    """
    انجام انتقال کالا پس از تایید دوطرفه
    
    Args:
        item: آبجکت کالا
        old_owner_id: شماره پرسنلی مالک قبلی
        new_owner_id: شماره پرسنلی مالک جدید
        description: توضیحات اختیاری
    
    Returns:
        tuple: (success: bool, message: str)
    """
    try:
        old_owner = PersonalInfo.objects.get(Personnel_number=old_owner_id)
        new_owner = PersonalInfo.objects.get(Personnel_number=new_owner_id)
        
        # ایجاد رکورد تاریخچه
        default_description = f'انتقال کالا از {old_owner.name} {old_owner.family} به {new_owner.name} {new_owner.family} پس از تایید هر دو نفر'
        ItemHistory.objects.create(
            item=item,
            from_person=old_owner,
            to_person=new_owner,
            action_type='transfer',
            description=description or default_description
        )
        
        # انتقال کالا
        item._approved_transfer = True  # فلگ برای signal
        item.PersonalInfo = new_owner
        item.update_date = timezone.now()
        item.save()
        
        return True, f"کالا {item.Technical_items} با موفقیت منتقل شد."
        
    except PersonalInfo.DoesNotExist:
        return False, "خطا در یافتن اطلاعات مالکان."
    except Exception as e:
        return False, f"خطا در انتقال کالا: {str(e)}"


def approve_item_assignment(item, new_owner, description=None):
    """
    تخصیص کالا به مالک جدید
    
    Args:
        item: آبجکت کالا
        new_owner: آبجکت مالک جدید
        description: توضیحات اختیاری
    
    Returns:
        tuple: (success: bool, message: str)
    """
    try:
        # ایجاد رکورد تاریخچه
        default_description = f'تخصیص کالا به {new_owner.name} {new_owner.family} پس از تایید مالک'
        ItemHistory.objects.create(
            item=item,
            from_person=None,
            to_person=new_owner,
            action_type='assign',
            description=description or default_description
        )
        
        # تخصیص کالا
        item._approved_transfer = True  # فلگ برای signal
        item.PersonalInfo = new_owner
        item.update_date = timezone.now()
        item.save()
        
        return True, f"کالا {item.Technical_items} با موفقیت به شما تخصیص داده شد."
        
    except Exception as e:
        return False, f"خطا در تخصیص کالا: {str(e)}"


def approve_item_removal(item, old_owner, description=None):
    """
    حذف کالا از مالک
    
    Args:
        item: آبجکت کالا
        old_owner: آبجکت مالک قبلی
        description: توضیحات اختیاری
    
    Returns:
        tuple: (success: bool, message: str)
    """
    try:
        # ایجاد رکورد تاریخچه
        default_description = f'حذف کالا از {old_owner.name} {old_owner.family} پس از تایید مالک'
        ItemHistory.objects.create(
            item=item,
            from_person=old_owner,
            to_person=None,
            action_type='return',
            description=description or default_description
        )
        
        # حذف مالک از کالا
        item._approved_transfer = True  # فلگ برای signal
        item.PersonalInfo = None
        item.update_date = timezone.now()
        item.save()
        
        return True, f"کالا {item.Technical_items} با موفقیت از شما حذف شد."
        
    except Exception as e:
        return False, f"خطا در حذف کالا: {str(e)}"


def approve_item_edit(item, changes, owner, description=None):
    """
    ویرایش کالا پس از تایید
    
    Args:
        item: آبجکت کالا
        changes: دیکشنری تغییرات
        owner: مالک کالا
        description: توضیحات اختیاری
    
    Returns:
        tuple: (success: bool, message: str)
    """
    try:
        owner_changed = False
        old_owner_id = None
        new_owner_id = None
        
        # اعمال تغییرات
        for field, change in changes.items():
            if field == 'PersonalInfo':
                # بررسی تغییر مالک در edit
                old_owner_id = change.get('old_id')
                new_owner_id = change.get('new_id')
                
                # اگر مالک تغییر کرده است، باید بررسی تایید دوطرفه شود
                if old_owner_id and new_owner_id and old_owner_id != new_owner_id:
                    owner_changed = True
                    # بررسی تایید دوطرفه
                    both_approved = check_both_parties_approved(item, old_owner_id, new_owner_id)
                    
                    if both_approved:
                        # فقط زمانی که هر دو نفر تایید کرده‌اند، مالک تغییر می‌کند
                        try:
                            new_owner = PersonalInfo.objects.get(Personnel_number=new_owner_id)
                            setattr(item, field, new_owner)
                            
                            # ثبت تاریخچه انتقال
                            old_owner = PersonalInfo.objects.get(Personnel_number=old_owner_id)
                            ItemHistory.objects.create(
                                item=item,
                                from_person=old_owner,
                                to_person=new_owner,
                                action_type='transfer',
                                description=f'انتقال کالا از {old_owner.name} {old_owner.family} به {new_owner.name} {new_owner.family} پس از تایید هر دو نفر (از طریق edit)'
                            )
                            
                        except PersonalInfo.DoesNotExist:
                            return False, "خطا در یافتن اطلاعات مالکان."
                    else:
                        # فقط یکی از طرفین تایید کرده، کالا منتقل نمی‌شود
                        return True, "درخواست شما تایید شد. کالا منتظر تایید طرف ��قابل است."
                elif new_owner_id:
                    # تغییر عادی مالک (بدون نیاز به تایید دوطرفه)
                    try:
                        new_owner = PersonalInfo.objects.get(Personnel_number=new_owner_id)
                        setattr(item, field, new_owner)
                        owner_changed = True
                    except PersonalInfo.DoesNotExist:
                        pass
                else:
                    # حذف مالک
                    setattr(item, field, None)
                    owner_changed = True
            else:
                # سایر فیلدها
                setattr(item, field, change['new'])
        
        # ذخیره تغییرات
        if not owner_changed:
            # اگر مالک تغییر نکرده، تغییرات عادی را اعمال کن
            item.update_date = timezone.now()
            item.save()
            
            # ایجاد رکورد تاریخچه برای تغییرات غیر از انتقال
            default_description = 'تغییرات کالا پس از تایید مالک'
            ItemHistory.objects.create(
                item=item,
                from_person=owner,
                to_person=owner,
                action_type='other',
                description=description or default_description
            )
            return True, f"تغییرات کالا {item.Technical_items} با موفقیت اعمال شد."
        elif owner_changed and check_both_parties_approved(item, old_owner_id, new_owner_id):
            # اگر مالک تغییر کرده و هر دو طرف تایید کرده‌اند
            item._approved_transfer = True  # فلگ برای signal
            item.update_date = timezone.now()
            item.save()
            return True, f"درخواست شما تایید شد. کالا {item.Technical_items} با موفقیت منتقل شد."
        else:
            # اگر مالک تغییر کرده اما هنوز هر دو طرف تایید نکرده‌اند
            return True, "درخواست شما تایید شد. کالا منتظر تایید طرف مقابل است."
        
    except Exception as e:
        return False, f"خطا در ویرایش کالا: {str(e)}"


def reject_related_requests(change_request):
    """
    رد درخواست‌های مرتبط (برای انتقال دوطرفه)
    
    Args:
        change_request: درخواست اصلی که رد شده
    """
    if change_request.action_type in ['transfer', 'receive']:
        item = change_request.item
        changes = change_request.proposed_changes or {}
        
        if change_request.action_type == 'transfer':
            # رد درخواست دریافت مالک جدید
            new_owner_id = changes.get('PersonalInfo', {}).get('new_id')
            if new_owner_id:
                related_request = ItemChangeRequest.objects.filter(
                    item=item,
                    owner__Personnel_number=new_owner_id,
                    action_type='receive',
                    status='pending'
                ).first()
                if related_request:
                    related_request.status = 'rejected'
                    related_request.responded_at = timezone.now()
                    related_request.save()
        
        elif change_request.action_type == 'receive':
            # رد درخواست انتقال مالک قبلی
            old_owner_id = changes.get('PersonalInfo', {}).get('old_id')
            if old_owner_id:
                related_request = ItemChangeRequest.objects.filter(
                    item=item,
                    owner__Personnel_number=old_owner_id,
                    action_type='transfer',
                    status='pending'
                ).first()
                if related_request:
                    related_request.status = 'rejected'
                    related_request.responded_at = timezone.now()
                    related_request.save()


def get_approval_message(change_request, old_owner_id, new_owner_id):
    """
    تولید پیام مناسب بر اساس وضعیت تایید
    
    Args:
        change_request: درخواست تغییر
        old_owner_id: شماره پرسنلی مالک قبلی
        new_owner_id: شماره پرسنلی مالک جدید
    
    Returns:
        str: پیام مناسب
    """
    try:
        if change_request.action_type == 'transfer':
            new_owner = PersonalInfo.objects.get(Personnel_number=new_owner_id)
            return f"درخواست شما تایید شد. کالا در حساب شما باقی می‌ماند تا {new_owner.name} {new_owner.family} نیز تایید کند."
        else:  # receive
            old_owner = PersonalInfo.objects.get(Personnel_number=old_owner_id)
            return f"درخواست شما تایید شد. کالا در حساب {old_owner.name} {old_owner.family} باقی می‌ماند تا ایشان نیز تایید کنند."
    except PersonalInfo.DoesNotExist:
        return "درخواست شما تایید شد. منتظر تایید طرف مقابل هستیم."