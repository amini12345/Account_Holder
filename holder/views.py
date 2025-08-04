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
from .session_utils import HolderSessionManager
import json
from shared.approval_utils import (
    check_both_parties_approved, approve_item_transfer, approve_item_assignment,
    approve_item_removal, approve_item_edit, reject_related_requests, get_approval_message
)

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
                    # استفاده از Session Manager جدید
                    HolderSessionManager.login_user(request, user)
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
    HolderSessionManager.logout_user(request)
    messages.success(request, "با موفقیت خارج شدید")
    return redirect('login')

def dashboard(request):
    if not HolderSessionManager.is_authenticated(request):
        messages.error(request, "لطفا ابتدا وارد شوید")
        return redirect('login')
    
    user_id = HolderSessionManager.get_user_id(request)
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
    if not HolderSessionManager.is_authenticated(request):
        return JsonResponse({'status': 'error', 'message': 'لطفا ابتدا وارد شوید'})
    
    user_id = HolderSessionManager.get_user_id(request)
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
    if not HolderSessionManager.is_authenticated(request):
        return JsonResponse({'status': 'error', 'message': 'لطفا ابتدا وارد شوید'})
    
    user_id = HolderSessionManager.get_user_id(request)
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
    if not HolderSessionManager.is_authenticated(request):
        return JsonResponse({'status': 'error', 'message': 'لطفا ابتدا وارد شوید'})
    
    user_id = HolderSessionManager.get_user_id(request)
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
    if not HolderSessionManager.is_authenticated(request):
        return JsonResponse({'status': 'error', 'message': 'لطفا ابتدا وارد شوید'})
    
    user_id = HolderSessionManager.get_user_id(request)
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
    """تایید درخواست تغییر کالا - استفاده از shared utilities"""
    if not HolderSessionManager.is_authenticated(request):
        return JsonResponse({'status': 'error', 'message': 'لطفا ابتدا وارد شوید'})
    
    user_id = HolderSessionManager.get_user_id(request)
    try:
        user = PersonalInfo.objects.get(Personnel_number=user_id)
        change_request = get_object_or_404(ItemChangeRequest, id=request_id, owner=user, status='pending')
        
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
                    # استفاده از shared utility برای انتقا��
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
            # حذف کالا ا�� مالک
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
                # اگر کالا مالک دارد، این باید از طریق transfer/receive با��د
                messages.error(request, "خطا: کالا دارای مالک است. انتقال باید از طریق سیستم تایید دوطرفه انجام شود.")
        
        elif change_request.action_type == 'edit':
            # ویرایش کالا
            success, message = approve_item_edit(item, changes, change_request.owner)
            if success:
                messages.success(request, message)
            else:
                messages.error(request, message)
        
        return redirect('dashboard')
        
    except PersonalInfo.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'کاربر یافت نشد'})
    except Exception as e:
        messages.error(request, f"خطا در تایید درخواست: {str(e)}")
        return redirect('dashboard')

@require_POST
def reject_change_request(request, request_id):
    """رد درخواست تغییر کالا - استفاده از shared utilities"""
    if not HolderSessionManager.is_authenticated(request):
        return JsonResponse({'status': 'error', 'message': 'لطفا ابتدا وارد شوید'})
    
    user_id = HolderSessionManager.get_user_id(request)
    try:
        user = PersonalInfo.objects.get(Personnel_number=user_id)
        change_request = get_object_or_404(ItemChangeRequest, id=request_id, owner=user, status='pending')
        
        # بروزرسانی وضعیت درخواست
        change_request.status = 'rejected'
        change_request.responded_at = timezone.now()
        change_request.save()
        
        # استفاده از shared utility برای رد درخواست‌های مرتبط
        reject_related_requests(change_request)
        
        messages.info(request, f"درخواست تغییر کالا {change_request.item.Technical_items} رد شد.")
        return redirect('dashboard')
        
    except PersonalInfo.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'کاربر یافت نشد'})
    except Exception as e:
        messages.error(request, f"خطا در رد درخواست: {str(e)}")
        return redirect('dashboard')