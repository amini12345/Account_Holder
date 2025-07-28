from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.http import HttpResponse, JsonResponse
from .models import PersonalInfo, Items, Documents, Mission, Results, ItemChangeRequest, ItemHistory
from .forms import (
    PersonalInfoRegistrationForm, CustomLoginForm,
    DocumentForm, MissionForm, ResultForm, ItemForm
)
from django.utils.crypto import get_random_string
from django.utils import timezone
import json

def register(request):
    if request.method == 'POST':
        form = PersonalInfoRegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "ثبت‌نام با موفقیت انجام شد. لطفا وارد شوید.")
            return redirect('login')
    else:
        form = PersonalInfoRegistrationForm()
    
    return render(request, 'holder/register.html', {'form': form})

def login(request):
    if request.method == 'POST':
        form = CustomLoginForm(request.POST)
        if form.is_valid():
            personnel_number = form.cleaned_data['Personnel_number']
            password = form.cleaned_data['password']
            
            try:
                user = PersonalInfo.objects.get(Personnel_number=personnel_number)
                if user.password == password: 
                    request.session['user_id'] = user.Personnel_number
                    request.session['user_name'] = f"{user.name} {user.family}"
                    messages.success(request, f"خوش آمدید {user.name} {user.family}")
                    return redirect('dashboard')
                else:
                    messages.error(request, "شماره پرسنلی یا رمز عبور اشتباه است")
            except PersonalInfo.DoesNotExist:
                messages.error(request, "شماره پرسنلی یا رمز عبور اشتباه است")
    else:
        form = CustomLoginForm()
    
    return render(request, 'holder/login.html', {'form': form})

def logout(request):
    request.session.flush()
    messages.success(request, "با موفقیت خارج شدید")
    return redirect('login')

def dashboard(request):
    if 'user_id' not in request.session:
        messages.error(request, "لطفا ابتدا وارد شوید")
        return redirect('login')
    
    user_id = request.session['user_id']
    try:
        user = PersonalInfo.objects.get(Personnel_number=user_id)
        
        # دریافت تمام داده‌های مرتبط با کاربر
        items = Items.objects.filter(PersonalInfo=user).order_by('-register_date')
        documents = Documents.objects.filter(PersonalInfo=user).order_by('-register_date')
        missions = Mission.objects.filter(PersonalInfo=user).order_by('-register_date')
        results = Results.objects.filter(PersonalInfo=user).order_by('-register_date')
        
        # دریافت درخواست‌های تایید در انتظار
        pending_requests = ItemChangeRequest.objects.filter(
            owner=user, 
            status='pending'
        ).order_by('-created_at')
        
        # فرم‌های جدید
        document_form = DocumentForm()
        mission_form = MissionForm()
        result_form = ResultForm()
        item_form = ItemForm()
        
        context = {
            'user': user,
            'items': items,
            'documents': documents,
            'missions': missions,
            'results': results,
            'pending_requests': pending_requests,
            'document_form': document_form,
            'mission_form': mission_form,
            'result_form': result_form,
            'item_form': item_form,
        }
        
        return render(request, 'holder/dashboard.html', context)
    except PersonalInfo.DoesNotExist:
        request.session.flush()
        messages.error(request, "حساب کاربری یافت نشد")
        return redirect('login')

@require_POST
def add_document(request):
    if 'user_id' not in request.session:
        return JsonResponse({'status': 'error', 'message': 'لطفا ابتدا وارد شوید'})
    
    user_id = request.session['user_id']
    try:
        user = PersonalInfo.objects.get(Personnel_number=user_id)
        form = DocumentForm(request.POST)
        if form.is_valid():
            doc = form.save()
            doc.PersonalInfo.add(user)  # چون رابطه ManyToMany است
            messages.success(request, "مدرک با موفقیت اضافه شد")
            return redirect('dashboard')
        else:
            messages.error(request, "خطا در اضافه کردن مدرک")
            return redirect('dashboard')
    except PersonalInfo.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'کاربر یافت نشد'})

def get_status_sub_items(request):
    """
    Ajax view برای دریافت زیر مجموعه‌های وضعیت کالا بر اساس وضعیت اصلی
    """
    status_item = request.GET.get('status_item')
    
    # تعریف نقشه زیر مجموعه‌های وضعیت
    STATUS_SUB_MAPPING = {
        'hardware': [
            {'value': 'repair', 'label': 'تعمیر'},
            {'value': 'upgrade', 'label': 'ارتقا'}
        ],
        'Delivery': [
            {'value': 'external', 'label': 'خارج'},
            {'value': 'internal', 'label': 'داخل'}
        ],
        'warehouse': [
            {'value': 'ready', 'label': 'آماده بکار'},
            {'value': 'returned_good', 'label': 'عودتی سالم'},
            {'value': 'returned_worn', 'label': 'عودتی فرسوده'}
        ],
    }
    
    # دریافت داده‌های مربوط به وضعیت انتخاب شده
    data = STATUS_SUB_MAPPING.get(status_item, [])
    
    return JsonResponse(data, safe=False)

@require_POST
def add_item(request):
    """
    اضافه کردن کالای جدید
    """
    if 'user_id' not in request.session:
        return JsonResponse({'status': 'error', 'message': 'لطفا ابتدا وارد شوید'})
    
    user_id = request.session['user_id']
    try:
        user = PersonalInfo.objects.get(Personnel_number=user_id)
        form = ItemForm(request.POST)
        if form.is_valid():
            item = form.save(commit=False)
            if not item.PersonalInfo:
                item.PersonalInfo = user
            item.save()
            messages.success(request, "کالا با موفقیت اضافه شد")
            return redirect('dashboard')
        else:
            messages.error(request, "خطا در اضافه کردن کالا")
            return redirect('dashboard')
    except PersonalInfo.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'کاربر یافت نشد'})

@require_POST
def add_mission(request):
    if 'user_id' not in request.session:
        return JsonResponse({'status': 'error', 'message': 'لطفا ابتدا وارد شوید'})
    
    user_id = request.session['user_id']
    try:
        user = PersonalInfo.objects.get(Personnel_number=user_id)
        form = MissionForm(request.POST)
        if form.is_valid():
            mission = form.save()
            mission.PersonalInfo.add(user)  # چون رابطه ManyToMany است
            messages.success(request, "ماموریت با موفقیت اضافه شد")
            return redirect('dashboard')
        else:
            messages.error(request, "خطا در اضافه کردن ماموریت")
            return redirect('dashboard')
    except PersonalInfo.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'کاربر یافت نشد'})

@require_POST
def add_result(request):
    if 'user_id' not in request.session:
        return JsonResponse({'status': 'error', 'message': 'لطفا ابتدا وارد شوید'})
    
    user_id = request.session['user_id']
    try:
        user = PersonalInfo.objects.get(Personnel_number=user_id)
        form = ResultForm(request.POST)
        if form.is_valid():
            result = form.save(commit=False)
            result.PersonalInfo = user
            result.save()
            messages.success(request, "نتیجه با موفقیت اضافه شد")
            return redirect('dashboard')
        else:
            messages.error(request, "خطا در اضافه کردن نتیجه")
            return redirect('dashboard')
    except PersonalInfo.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'کاربر یافت نشد'})

@require_POST
def approve_change_request(request, request_id):
    """تایید درخواست تغییر کالا"""
    if 'user_id' not in request.session:
        return JsonResponse({'status': 'error', 'message': 'لطفا ابتدا وارد شوید'})
    
    user_id = request.session['user_id']
    try:
        user = PersonalInfo.objects.get(Personnel_number=user_id)
        change_request = get_object_or_404(ItemChangeRequest, id=request_id, owner=user, status='pending')
        
        # اعمال تغییرات
        item = change_request.item
        changes = change_request.proposed_changes
        
        if change_request.action_type in ['transfer', 'remove']:
            # انتقال یا حذف کالا از مالک فعلی
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
                description = f'{"انتقال" if new_owner else "حذف"} تایید شده توسط {user.name} {user.family}'
                
                ItemHistory.objects.create(
                    item=item,
                    from_person=item.PersonalInfo,
                    to_person=new_owner,
                    action_type=action_type,
                    description=description
                )
                
                # بروزرسانی مالک (حذف یا انتقال)
                item.PersonalInfo = new_owner
                item.update_date = timezone.now()
                item.save()
                
        elif change_request.action_type == 'assign':
            # تخصیص کالا به مالک جدید (کالا قبلاً مالک نداشته)
            if 'PersonalInfo' in changes:
                # ایجاد رکورد تاریخچه
                ItemHistory.objects.create(
                    item=item,
                    from_person=None,
                    to_person=user,
                    action_type='assign',
                    description=f'تخصیص تایید شده توسط {user.name} {user.family}'
                )
                
                # بروزرسانی مالک
                item.PersonalInfo = user
                item.update_date = timezone.now()
                item.save()
                
        elif change_request.action_type == 'edit':
            # ویرایش مشخصات کالا
            for field, change in changes.items():
                if field == 'PersonalInfo':
                    # تغییر مالک در ویرایش
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
                from_person=user,
                to_person=user,
                action_type='other',
                description=f'تغییرات تایید شده توسط {user.name} {user.family}'
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
        
        messages.success(request, f"درخواست {action_message} کالا {item.Technical_items} تایید شد.")
        return redirect('dashboard')
        
    except PersonalInfo.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'کاربر یافت نشد'})
    except Exception as e:
        messages.error(request, f"خطا در تایید درخواست: {str(e)}")
        return redirect('dashboard')

@require_POST
def reject_change_request(request, request_id):
    """رد درخواست تغییر کالا"""
    if 'user_id' not in request.session:
        return JsonResponse({'status': 'error', 'message': 'لطفا ابتدا وارد شوید'})
    
    user_id = request.session['user_id']
    try:
        user = PersonalInfo.objects.get(Personnel_number=user_id)
        change_request = get_object_or_404(ItemChangeRequest, id=request_id, owner=user, status='pending')
        
        # بروزرسانی وضعیت در��واست
        change_request.status = 'rejected'
        change_request.responded_at = timezone.now()
        change_request.save()
        
        messages.info(request, f"درخواست تغییر کالا {change_request.item.Technical_items} رد شد.")
        return redirect('dashboard')
        
    except PersonalInfo.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'کاربر یافت نشد'})
    except Exception as e:
        messages.error(request, f"خطا در رد درخواست: {str(e)}")
        return redirect('dashboard')