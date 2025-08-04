#!/usr/bin/env python
"""
تست جامع سیستم انتقال کالا
"""

import os
import sys
import django

# تنظیم Django
sys.path.append('/wsl.localhost/Ubuntu/home/behnam/Account_holder/project')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')
django.setup()

from holder.models import Items, ItemChangeRequest, PersonalInfo
from shared.approval_utils import (
    check_both_parties_approved, approve_item_transfer, approve_item_assignment,
    approve_item_edit
)
from django.utils import timezone

def test_comprehensive():
    """تست جامع تمام سناریوهای انتقال"""
    
    print("=== تست جامع سیستم انتقال کالا ===")
    
    # پیدا کردن کاربران
    users = list(PersonalInfo.objects.all()[:3])
    if len(users) < 2:
        print("❌ حداقل دو کاربر برای تست نیاز است")
        return
        
    user1, user2 = users[0], users[1]
    print(f"✅ کاربر 1: {user1.name} {user1.family} ({user1.Personnel_number})")
    print(f"✅ کاربر 2: {user2.name} {user2.family} ({user2.Personnel_number})")
    
    # پیدا کردن کالا
    item = Items.objects.first()
    if not item:
        print("❌ کالایی یافت نشد")
        return
        
    print(f"✅ کالا: {item.Technical_items}")
    
    # تنظیم مالک اولیه
    item.PersonalInfo = user1
    item.save()
    print(f"✅ مالک اولیه تنظیم شد: {user1.name}")
    
    # حذف درخواست‌های قبلی
    ItemChangeRequest.objects.filter(item=item).delete()
    print("✅ درخواست‌های قبلی حذف شدند")
    
    print(f"\n🧪 تست 1: تایید فقط یک نفر (نباید منتقل شود)")
    
    # ایجاد درخواست‌های انتقال
    transfer_req = ItemChangeRequest.objects.create(
        item=item,
        owner=user1,
        admin_user='test_admin',
        action_type='transfer',
        proposed_changes={
            'PersonalInfo': {
                'old': f"{user1.name} {user1.family}",
                'new': f"{user2.name} {user2.family}",
                'old_id': user1.Personnel_number,
                'new_id': user2.Personnel_number
            }
        },
        description='تست انتقال'
    )
    
    receive_req = ItemChangeRequest.objects.create(
        item=item,
        owner=user2,
        admin_user='test_admin',
        action_type='receive',
        proposed_changes={
            'PersonalInfo': {
                'old': f"{user1.name} {user1.family}",
                'new': f"{user2.name} {user2.family}",
                'old_id': user1.Personnel_number,
                'new_id': user2.Personnel_number
            }
        },
        description='تست دریافت'
    )
    
    print("   ✅ درخواست‌ها ایجاد شدند")
    
    # تایید فقط یک نفر
    transfer_req.status = 'approved'
    transfer_req.responded_at = timezone.now()
    transfer_req.save()
    
    print("   ✅ فقط transfer تایید شد")
    
    # بررسی وضعیت
    both_approved = check_both_parties_approved(item, user1.Personnel_number, user2.Personnel_number)
    print(f"   📊 آیا هر دو طرف تایید کرده‌اند؟ {both_approved}")
    
    if both_approved:
        print("   ❌ خطا: نباید True باشد!")
        return False
    else:
        print("   ✅ درست: هنوز هر دو طرف تایید نکرده‌اند")
    
    # بررسی مالک کالا
    item.refresh_from_db()
    if item.PersonalInfo == user1:
        print("   ✅ درست: کالا هنوز نزد مالک اول است")
    else:
        print(f"   ❌ خطا: کالا به اشتباه منتقل شده به {item.PersonalInfo.name if item.PersonalInfo else 'None'}")
        return False
    
    print(f"\n🧪 تست 2: تایید هر دو نفر (باید منتقل شود)")
    
    # تایید نفر دوم
    receive_req.status = 'approved'
    receive_req.responded_at = timezone.now()
    receive_req.save()
    
    print("   ✅ receive نیز تایید شد")
    
    # بررسی وضعیت
    both_approved = check_both_parties_approved(item, user1.Personnel_number, user2.Personnel_number)
    print(f"   📊 آیا هر دو طرف تایید کرده‌اند؟ {both_approved}")
    
    if not both_approved:
        print("   ❌ خطا: باید True باشد!")
        return False
    else:
        print("   ✅ درست: هر دو طرف تایید کرده‌اند")
    
    # انجام انتقال
    success, message = approve_item_transfer(item, user1.Personnel_number, user2.Personnel_number)
    print(f"   📋 نتیجه انتقال: {success} - {message}")
    
    if not success:
        print("   ❌ خطا در انتقال")
        return False
    
    # بررسی مالک جدید
    item.refresh_from_db()
    if item.PersonalInfo == user2:
        print("   ✅ درست: کالا با موفقیت منتقل شد")
    else:
        print(f"   ❌ خطا: کالا منتقل نشد. مالک فعلی: {item.PersonalInfo.name if item.PersonalInfo else 'None'}")
        return False
    
    print(f"\n🧪 تست 3: تست assign برای کالای دارای مالک (نباید کار کند)")
    
    # ایجاد درخواست assign برای کالای دارای مالک
    assign_req = ItemChangeRequest.objects.create(
        item=item,
        owner=user1,  # کسی که کالا را نداره
        admin_user='test_admin',
        action_type='assign',
        proposed_changes={
            'PersonalInfo': {
                'old': None,
                'new': f"{user1.name} {user1.family}",
                'old_id': None,
                'new_id': user1.Personnel_number
            }
        },
        description='تست assign نادرست'
    )
    
    print("   ✅ درخواست assign ایجاد شد")
    
    # تایید درخواست assign
    assign_req.status = 'approved'
    assign_req.responded_at = timezone.now()
    assign_req.save()
    
    print("   ✅ درخواست assign تایید شد")
    
    # بررسی که کالا منتقل نشده (چون دارای مالک است)
    item.refresh_from_db()
    if item.PersonalInfo == user2:
        print("   ✅ درست: کالا منتقل نشد (چون دارای مالک بود)")
    else:
        print(f"   ❌ خطا: کالا به اشتباه منتقل شد به {item.PersonalInfo.name if item.PersonalInfo else 'None'}")
        return False
    
    print(f"\n🧪 تست 4: تست assign برای کالای بدون مالک (باید کار کند)")
    
    # حذف مالک از کالا
    item.PersonalInfo = None
    item.save()
    print("   ✅ مالک کالا حذف شد")
    
    # ایجاد درخواست assign جدید
    assign_req2 = ItemChangeRequest.objects.create(
        item=item,
        owner=user1,
        admin_user='test_admin',
        action_type='assign',
        proposed_changes={
            'PersonalInfo': {
                'old': None,
                'new': f"{user1.name} {user1.family}",
                'old_id': None,
                'new_id': user1.Personnel_number
            }
        },
        description='تست assign صحیح'
    )
    
    # تایید و اجرا
    assign_req2.status = 'approved'
    assign_req2.responded_at = timezone.now()
    assign_req2.save()
    
    # شبیه‌سازی تایید assign
    success, message = approve_item_assignment(item, user1)
    print(f"   📋 نتیجه assign: {success} - {message}")
    
    if success:
        item.refresh_from_db()
        if item.PersonalInfo == user1:
            print("   ✅ درست: کالا با assign منتقل شد")
        else:
            print("   ❌ خطا: assign کار نکرد")
            return False
    else:
        print("   ❌ خطا در assign")
        return False
    
    print(f"\n✅ تمام تست‌ها موفق بودند!")
    print(f"📊 خلاصه نهایی:")
    print(f"   - کالا: {item.Technical_items}")
    print(f"   - مالک نهایی: {item.PersonalInfo.name if item.PersonalInfo else 'None'}")
    print(f"   - تعداد درخواست‌ها: {ItemChangeRequest.objects.filter(item=item).count()}")
    
    return True

if __name__ == "__main__":
    try:
        success = test_comprehensive()
        if success:
            print("\n🎉 همه چیز درست کار می‌کند!")
        else:
            print("\n💥 هنوز مشکل وجود دارد!")
    except Exception as e:
        print(f"\n❌ خطا در تست: {str(e)}")
        import traceback
        traceback.print_exc()