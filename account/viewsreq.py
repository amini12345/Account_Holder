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
                    
                    ItemChangeRequest.objects.create(
                        item=original_obj,
                        owner=old_owner,
                        admin_user=self.request.user.username,
                        action_type=action_type,
                        proposed_changes=changes,
                        description=description
                    )
                    
                    if new_owner:
                        messages.warning(self.request, 
                            f"درخواست انتقال کالا {original_obj.Technical_items} "
                            f"برای تایید {old_owner.name} {old_owner.family} (مالک فعلی) ارسال شد. "
                            f"پس از تایید مالک فعلی، درخواست برای {new_owner.name} {new_owner.family} (مالک جدید) ارسال خواهد شد."
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
    change_request = get_object_or_404(ItemChangeRequest, pk=pk)
    
    context = {
        'change_request': change_request,
    }
    
    return render(request, 'registration/change_request_detail.html', context)


@require_POST
@login_required
def approve_change_request_user(request, request_id):
    """تایید درخواست تغییر کالا توسط کاربر (مالک)"""
    change_request = get_object_or_404(ItemChangeRequest, id=request_id)
    
    # بررسی اینکه کاربر مالک کالا است
    if change_request.owner.Personnel_number != request.user.username:
        messages.error(request, "شما مجاز به تایید این درخواست نیستید.")
        return redirect('account:change_requests_list')
    
    try:
        # بروزرسانی وضعیت درخواست
        change_request.status = 'approved'
        change_request.responded_at = timezone.now()
        change_request.save()
        
        item = change_request.item
        changes = change_request.proposed_changes
        
        if change_request.action_type == 'transfer':
            # مالک اول تایید کرد، کالا را از او حذف کرده و درخواست برای مالک دوم ایجاد می‌شود
            new_owner_id = changes['PersonalInfo'].get('new_id')
            if new_owner_id:
                try:
                    new_owner = PersonalInfo.objects.get(Personnel_number=new_owner_id)
                    
                    # ابتدا کالا را از مالک فعلی حذف می‌کنیم (بدون دارنده می‌شود)
                    ItemHistory.objects.create(
                        item=item,
                        from_person=change_request.owner,
                        to_person=None,
                        action_type='return',
                        description=f'حذف کالا از {change_request.owner.name} {change_request.owner.family} پس از تایید انتقال'
                    )
                    
                    item.PersonalInfo = None
                    item.update_date = timezone.now()
                    item.save()
                    
                    # بررسی اینکه آیا درخواست برای مالک جدید قبلاً ایجاد شده است
                    existing_receive_request = ItemChangeRequest.objects.filter(
                        item=item,
                        owner=new_owner,
                        action_type='receive',
                        status='pending'
                    ).first()
                    
                    if not existing_receive_request:
                        # ایجاد درخواست برای مالک جدید
                        ItemChangeRequest.objects.create(
                            item=item,
                            owner=new_owner,
                            admin_user=change_request.admin_user,
                            action_type='receive',
                            proposed_changes=changes,
                            description=f"درخواست دریافت کالا {item.Technical_items} توسط مدیر {change_request.admin_user}"
                        )
                        messages.success(request, f"درخواست شما تایید شد. کالا از شما حذف شد و درخواست دریافت کالا برای {new_owner.name} {new_owner.family} ارسال شد.")
                    else:
                        messages.success(request, f"درخواست شما تایید شد. کالا از شما حذف شد. منتظر تایید مالک جدید ({new_owner.name} {new_owner.family}) هستیم.")
                            
                except PersonalInfo.DoesNotExist:
                    messages.error(request, "مالک جدید ی��فت نشد.")
        
        elif change_request.action_type == 'receive':
            # مالک دوم تایید کرد، کالا را به او اختصاص می‌دهیم
            # (کالا قبلاً بدون دارنده شده است)
            ItemHistory.objects.create(
                item=item,
                from_person=None,
                to_person=change_request.owner,
                action_type='assign',
                description=f'تخصیص کالا به {change_request.owner.name} {change_request.owner.family} پس از تایید دریافت'
            )
            
            item.PersonalInfo = change_request.owner
            item.update_date = timezone.now()
            item.save()
            
            messages.success(request, f"کالا {item.Technical_items} با موفقیت به شما تخصیص داده شد.")
        
        elif change_request.action_type == 'remove':
            # حذف کالا از مالک
            ItemHistory.objects.create(
                item=item,
                from_person=item.PersonalInfo,
                to_person=None,
                action_type='return',
                description=f'حذف کالا از {item.PersonalInfo.name} {item.PersonalInfo.family} پس از تایید مالک'
            )
            
            item.PersonalInfo = None
            item.update_date = timezone.now()
            item.save()
            
            messages.success(request, f"کالا {item.Technical_items} با موفقیت از شما حذف شد.")
        
        elif change_request.action_type == 'assign':
            # تخصیص کالا به مالک جدید
            ItemHistory.objects.create(
                item=item,
                from_person=None,
                to_person=change_request.owner,
                action_type='assign',
                description=f'تخصیص کالا به {change_request.owner.name} {change_request.owner.family} پس از تایید مالک'
            )
            
            item.PersonalInfo = change_request.owner
            item.update_date = timezone.now()
            item.save()
            
            messages.success(request, f"کالا {item.Technical_items} با موفقیت به شما تخصیص داده شد.")
        
        elif change_request.action_type == 'edit':
            # ویرایش کالا
            for field, change in changes.items():
                if field == 'PersonalInfo':
                    # تغییر مالک
                    new_owner_id = change.get('new_id')
                    if new_owner_id:
                        try:
                            new_owner = PersonalInfo.objects.get(Personnel_number=new_owner_id)
                            setattr(item, field, new_owner)
                        except PersonalInfo.DoesNotExist:
                            pass
                    else:
                        # حذف مالک
                        setattr(item, field, None)
                else:
                    # سایر فیلدها
                    setattr(item, field, change['new'])
            
            item.update_date = timezone.now()
            item.save()
            
            # ایجاد رکورد تاریخچه
            ItemHistory.objects.create(
                item=item,
                from_person=change_request.owner,
                to_person=change_request.owner,
                action_type='other',
                description=f'تغییرات کالا پس از تایید مالک'
            )
            
            messages.success(request, f"تغییرات کالا {item.Technical_items} با موفقیت اعمال شد.")
        
        return redirect('account:change_requests_list')
        
    except Exception as e:
        messages.error(request, f"خطا در تایید درخواست: {str(e)}")
        return redirect('account:change_requests_list')


@require_POST
@login_required
def reject_change_request_user(request, request_id):
    """رد درخواست تغییر کالا توسط کاربر (مالک)"""
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
        
        # اگر این درخواست انتقال بود، درخواست مرتبط با مالک دیگر را نیز رد کنید
        if change_request.action_type in ['transfer', 'receive']:
            item = change_request.item
            changes = change_request.proposed_changes
            
            if change_request.action_type == 'transfer':
                # ��د درخواست دریافت مالک جدید
                new_owner_id = changes['PersonalInfo'].get('new_id')
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
                old_owner_id = changes['PersonalInfo'].get('old_id')
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
                new_owner = None
                
                if new_owner_id and change_request.action_type == 'transfer':
                    # پیدا کردن مالک جدید برای انتقال
                    try:
                        new_owner = PersonalInfo.objects.get(Personnel_number=new_owner_id)
                    except PersonalInfo.DoesNotExist:
                        # اگر مالک جدید یافت نشد، از نام استفاده کن
                        new_owner_name = changes['PersonalInfo']['new']
                        if new_owner_name:
                            name_parts = new_owner_name.split(' ')
                            if len(name_parts) >= 2:
                                new_owner = PersonalInfo.objects.filter(
                                    name=name_parts[0], 
                                    family=' '.join(name_parts[1:])
                                ).first()
                
                # ایجاد رکورد تاریخچه
                action_type = 'transfer' if new_owner else 'return'
                description = f'{"انتقال" if new_owner else "حذف"} اجباری توسط مدیر {request.user.username}'
                
                ItemHistory.objects.create(
                    item=item,
                    from_person=item.PersonalInfo,
                    to_person=new_owner,
                    action_type=action_type,
                    description=description
                )
                
                # بروزرسانی مالک
                item.PersonalInfo = new_owner
                item.update_date = timezone.now()
                item.save()
                
        elif change_request.action_type == 'assign':
            # تخصیص کالا به مالک جدید
            if 'PersonalInfo' in changes:
                new_owner_id = changes['PersonalInfo'].get('new_id')
                if new_owner_id:
                    try:
                        new_owner = PersonalInfo.objects.get(Personnel_number=new_owner_id)
                    except PersonalInfo.DoesNotExist:
                        # اگر مالک جدید یافت نشد، از نام استفاده کن
                        new_owner_name = changes['PersonalInfo']['new']
                        if new_owner_name:
                            name_parts = new_owner_name.split(' ')
                            if len(name_parts) >= 2:
                                new_owner = PersonalInfo.objects.filter(
                                    name=name_parts[0], 
                                    family=' '.join(name_parts[1:])
                                ).first()
                    
                    if new_owner:
                        # ایجاد رکورد تاریخچه
                        ItemHistory.objects.create(
                            item=item,
                            from_person=None,
                            to_person=new_owner,
                            action_type='assign',
                            description=f'تخصیص اجباری توسط مدیر {request.user.username}'
                        )
                        
                        # بروزرسانی مالک
                        item.PersonalInfo = new_owner
                        item.update_date = timezone.now()
                        item.save()
                        
        elif change_request.action_type == 'edit':
            # ویرایش کالا
            for field, change in changes.items():
                if field == 'PersonalInfo':
                    # تغییر مالک
                    new_owner_id = change.get('new_id')
                    if new_owner_id:
                        try:
                            new_owner = PersonalInfo.objects.get(Personnel_number=new_owner_id)
                            setattr(item, field, new_owner)
                        except PersonalInfo.DoesNotExist:
                            # اگر مالک جدید یافت نشد، از نام استفاده کن
                            new_owner_name = change['new']
                            if new_owner_name:
                                name_parts = new_owner_name.split(' ')
                                if len(name_parts) >= 2:
                                    new_owner = PersonalInfo.objects.filter(
                                        name=name_parts[0], 
                                        family=' '.join(name_parts[1:])
                                    ).first()
                                    if new_owner:
                                        setattr(item, field, new_owner)
                    else:
                        # حذف مالک
                        setattr(item, field, None)
                else:
                    # سایر فیلدها
                    setattr(item, field, change['new'])
            
            item.update_date = timezone.now()
            item.save()
            
            # ایجاد رکورد تاریخچه
            ItemHistory.objects.create(
                item=item,
                from_person=change_request.owner,
                to_person=change_request.owner,
                action_type='other',
                description=f'تغییرات اجباری توسط مدیر {request.user.username}'
            )
        
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
                        # ایجاد درخواست تایید برای مالک قبلی (فقط مرحله اول)
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
                        request_count += 1
                    elif not item.PersonalInfo:
                        # اگر کالا مالک ندارد، مستقیماً انتقال دهید
                        ItemHistory.objects.create(
                            item=item,
                            from_person=None,
                            to_person=to_person,
                            action_type='assign',
                            description=description or f'کالا به {to_person.name} {to_person.family} تخصیص داده شد.'
                        )
                        item.PersonalInfo = to_person
                        item.update_date = timezone.now()
                        item.save()
                        direct_count += 1
                        
                except Items.DoesNotExist:
                    continue
            
            if request_count > 0:
                messages.warning(request, 
                    f'{request_count} درخواست انتقال برای تایید مالکان فعلی ارسال شد. '
                    f'پس از تایید هر مالک، درخواست برای مالک جدید ارسال خواهد شد.'
                )
            if direct_count > 0:
                messages.success(request, 
                    f'{direct_count} کالا بدون مالک با موفقیت تخصیص داده شد.'
                )
                
        except PersonalInfo.DoesNotExist:
            messages.error(request, 'شخص مقصد یافت نشد.')
        except Exception as e:
            messages.error(request, f'خطا در انتقال کالاها: {str(e)}')
    
    return redirect('account:home')