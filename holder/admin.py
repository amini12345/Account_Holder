from django.contrib import admin
from .models import PersonalInfo, Documents, Mission, Results, Items, ItemHistory, ItemChangeRequest
from django.utils import timezone
from django.contrib import messages
from django.shortcuts import render, redirect
from django import forms
from django.utils.html import format_html
from django.urls import reverse
import json
from shared.approval_utils import approve_item_assignment
from extensions.jalali import Persian, Gregorian
import datetime


class PersianDateWidget(forms.DateInput):
    """ویجت تاریخ فارسی با تقویم"""
    
    def format_value(self, value):
        """تبدیل تاریخ میلادی به شمسی برای نمایش"""
        if value and isinstance(value, (datetime.date, datetime.datetime)):
            try:
                persian_date = Gregorian(value).persian_tuple()
                return f"{persian_date[0]}/{persian_date[1]:02d}/{persian_date[2]:02d}"
            except:
                pass
        return value
    
    def value_from_datadict(self, data, files, name):
        """تبدیل تاریخ شمسی وارد شده به میلادی برای ذخیره"""
        value = super().value_from_datadict(data, files, name)
        if value and '/' in value:
            try:
                parts = value.split('/')
                if len(parts) == 3:
                    year, month, day = int(parts[0]), int(parts[1]), int(parts[2])
                    gregorian_date = Persian(year, month, day).gregorian_tuple()
                    return f"{gregorian_date[0]}-{gregorian_date[1]:02d}-{gregorian_date[2]:02d}"
            except:
                pass
        return value
    
    class Media:
        css = {
            'all': ('css/persian-calendar.css',)
        }
        js = ('js/persian-calendar.js',)

#Admin header change
admin.site.site_header = "پنل مدیریت وب سایت"

class TransferItemForm(forms.Form):
    to_person = forms.ModelChoiceField(
        queryset=PersonalInfo.objects.all(),
        label="انتقال به",
        help_text="شخصی که کالا به او منتقل می‌شود"
    )
    description = forms.CharField(
        widget=forms.Textarea,
        required=False,
        label="توضیحات",
        help_text="توضیحات مربوط به انتقال کالا"
    )

class PersonalInfoAdminForm(forms.ModelForm):
    """
    فرم سفارشی برای مدل PersonalInfo با ویجت تاریخ فارسی
    """
    class Meta:
        model = PersonalInfo
        fields = '__all__'
        widgets = {
            'date_of_birth': PersianDateWidget(attrs={
                'placeholder': 'مثال: 1370/01/01',
                'help_text': 'تاریخ تولد را به فرمت شمسی وارد کنید'
            }),
        }

class PersonalInfoAdmin(admin.ModelAdmin):
    form = PersonalInfoAdminForm
    list_display = ('Personnel_number','name', 'family', 'National_ID','Educational_degree','jinfo')
    search_fields = ('family',)
    list_filter = ('date_created',)  
    ordering = ('-date_created',)
    
    fieldsets = (
        ('اطلاعات شخصی', {
            'fields': ('name', 'family', 'Personnel_number', 'National_ID', 'date_of_birth')
        }),
        ('اطلاعات تماس', {
            'fields': ('email', 'phone_number')
        }),
        ('اطلاعات تحصیلی و امنیتی', {
            'fields': ('Educational_degree', 'password')
        }),
    )
    
admin.site.register(PersonalInfo, PersonalInfoAdmin) 

class ItemHistoryInline(admin.TabularInline):
    model = ItemHistory
    fk_name = 'item'
    extra = 0
    readonly_fields = ('from_person', 'to_person', 'action_type', 'action_date', 'description', 'created_at')
    can_delete = False
    
    def has_add_permission(self, request, obj=None):
        return False
        
    verbose_name = "تاریخچه کالا"
    verbose_name_plural = "تاریخچه کالا"

class ItemInfoAdmin(admin.ModelAdmin):
    list_display = ('Technical_items', 'type_Item', 'brand', 'Configuration', 'jinfo','serial_number','Product_code', 'status_item', 'PersonalInfo', 'show_history')
    search_fields = ('Technical_items', 'serial_number', 'brand')
    list_filter = ('type_Item', 'brand')  
    ordering = ('-register_date',)
    actions = ['transfer_item']
    inlines = [ItemHistoryInline]
    
    def show_history(self, obj):
        count = obj.history.count()
        if count > 0:
            url = reverse('admin:holder_itemhistory_changelist') + f'?item__id__exact={obj.id}'
            return format_html('<a href="{}">{} مورد</a>', url, count)
        return "بدون تاریخچه"
    
    show_history.short_description = "تاریخچه"
    
    def save_model(self, request, obj, form, change):
        """Override save_model to create change request for existing items with owners"""
        if change and obj.PersonalInfo:  # اگر کالا در حال ویرایش است و مالک دارد
            # بررسی تغییرات
            original_obj = Items.objects.get(pk=obj.pk)
            changes = {}
            
            # بررسی فیلدهای مختلف برای تغییر
            fields_to_check = [
                'Technical_items', 'type_Item', 'status_item', 'status_sub_item',
                'brand', 'Configuration', 'serial_number', 'Product_code', 'PersonalInfo'
            ]
            
            for field in fields_to_check:
                original_value = getattr(original_obj, field)
                new_value = getattr(obj, field)
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
            
            if changes:  # اگر تغییری وجود دارد
                # بررسی اینکه آیا تغییر مالک رخ داده است
                owner_change = 'PersonalInfo' in changes
                
                if owner_change:
                    old_owner = original_obj.PersonalInfo
                    new_owner = obj.PersonalInfo
                    
                    # اگر کالا از کسی گرفته می‌شود (کم می‌شود)
                    if old_owner and old_owner != new_owner:
                        # ایجاد درخواست تایید برای مالک قبلی (مرحله اول)
                        action_type = 'transfer' if new_owner else 'remove'
                        description = f"درخواست {'انتقال' if new_owner else 'حذف'} کالا {original_obj.Technical_items} توسط مدیر {request.user.username}"
                        if new_owner:
                            description += f" به {new_owner.name} {new_owner.family}"
                        
                        # ایجاد درخواست برای مالک فعلی
                        ItemChangeRequest.objects.create(
                            item=original_obj,
                            owner=old_owner,
                            admin_user=request.user.username,
                            action_type=action_type,
                            proposed_changes=changes,
                            description=description
                        )
                        
                        if new_owner:
                            # همزمان ایجاد درخواست برای مالک جدید
                            ItemChangeRequest.objects.create(
                                item=original_obj,
                                owner=new_owner,
                                admin_user=request.user.username,
                                action_type='receive',
                                proposed_changes=changes,
                                description=f"درخواست دریافت کالا {original_obj.Technical_items} توسط مدیر {request.user.username}"
                            )
                            
                            messages.warning(request, 
                                f"درخواست انتقال کالا {original_obj.Technical_items} "
                                f"برای تایید {old_owner.name} {old_owner.family} (مالک فعلی) و "
                                f"{new_owner.name} {new_owner.family} (مالک جدید) ارسال شد. "
                                f"کالا پس از تایید هر دو نفر منتقل خواهد شد."
                            )
                        else:
                            messages.warning(request, 
                                f"درخواست حذف کالا {original_obj.Technical_items} "
                                f"برای تایید {old_owner.name} {old_owner.family} ارسال شد. "
                                f"تغییرات پس از تایید مالک اعمال خواهد شد."
                            )
                        return  # جلوگیری از ذخیره تغییرات
                    
                    # اگر کالا به کسی داده می‌شود (اضافه می‌شود) و مالک قبلی ندارد
                    elif new_owner and not old_owner:
                        # ایجاد درخواست تایید برای مالک جدید
                        ItemChangeRequest.objects.create(
                            item=original_obj,
                            owner=new_owner,
                            admin_user=request.user.username,
                            action_type='assign',
                            proposed_changes=changes,
                            description=f"درخواست تخصیص کالا {original_obj.Technical_items} توسط مدیر {request.user.username}"
                        )
                        
                        messages.warning(request, 
                            f"درخواست تخصیص کالا {original_obj.Technical_items} "
                            f"برای تایید {new_owner.name} {new_owner.family} ارسال شد. "
                            f"تغییرات پس از تایید مالک اعمال خواهد شد."
                        )
                        return  # جلوگیری از ذخیره تغییرات
                
                # اگر تغییرات غیر از مالک است و کالا مالک دارد
                else:
                    # ایجاد درخواست تایید برای تغییرات عادی
                    ItemChangeRequest.objects.create(
                        item=original_obj,
                        owner=original_obj.PersonalInfo,
                        admin_user=request.user.username,
                        action_type='edit',
                        proposed_changes=changes,
                        description=f"درخواست تغییر مشخصات کالا {original_obj.Technical_items} توسط مدیر {request.user.username}"
                    )
                    
                    messages.warning(request, 
                        f"درخواست تغییر کالا {original_obj.Technical_items} برای تایید مالک ارسال شد. "
                        f"تغییرات پس از تایید مالک اعمال خواهد شد."
                    )
                    return  # جلوگیری از ذخیره تغییرات
        
        # اگر کالا مالک ندارد یا کالا جدید است، مستقیماً ذخیره شود
        super().save_model(request, obj, form, change)
    
    def transfer_item(self, request, queryset):
        if 'apply' in request.POST:
            form = TransferItemForm(request.POST)
            if form.is_valid():
                to_person = form.cleaned_data['to_person']
                description = form.cleaned_data['description']
                
                count = 0
                request_count = 0
                
                for item in queryset:
                    if item.PersonalInfo and item.PersonalInfo != to_person:
                        # ایجاد درخواست تایید برای مالک قبلی
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
                        
                        # همزمان ایجاد درخواست تایید برای مالک جدید
                        ItemChangeRequest.objects.create(
                            item=item,
                            owner=to_person,
                            admin_user=request.user.username,
                            action_type='receive',
                            proposed_changes={
                                'PersonalInfo': {
                                    'old': f"{item.PersonalInfo.name} {item.PersonalInfo.family}",
                                    'new': f"{to_person.name} {to_person.family}",
                                    'old_id': item.PersonalInfo.Personnel_number,
                                    'new_id': to_person.Personnel_number
                                }
                            },
                            description=description or f'درخواست دریافت کالا از {item.PersonalInfo.name} {item.PersonalInfo.family}'
                        )
                        request_count += 1
                    elif not item.PersonalInfo:
                        # اگر کالا مالک ندارد، از shared utility استفاده کن
                        success, message = approve_item_assignment(
                            item, to_person,
                            description or f'کالا به {to_person.name} {to_person.family} تخصیص داده شد.'
                        )
                        if success:
                            count += 1
                
                if request_count > 0:
                    self.message_user(request, 
                        f'{request_count} درخواست انتقال برای تایید مالکان فعلی و جدید ارسال شد. '
                        f'کالاها پس از تایید هر دو نفر منتقل خواهند شد.', 
                        messages.WARNING
                    )
                if count > 0:
                    self.message_user(request, 
                        f'{count} کالا بدون مالک با موفقیت تخصیص داده شد.', 
                        messages.SUCCESS
                    )
                return None
        else:
            form = TransferItemForm()
        
        return render(request, 'admin/transfer_items.html', {
            'items': queryset,
            'form': form,
            'title': 'انتقال کالاها به شخص دیگر'
        })
    
    transfer_item.short_description = "انتقال کالاهای انتخاب شده به شخص دیگر"
    
# admin.site.register(Items,ItemInfoAdmin)

class ItemHistoryAdmin(admin.ModelAdmin):
    list_display = ('item', 'get_item_status', 'from_person', 'to_person', 'action_type', 'get_change_summary', 'jinfo')
    search_fields = ('item__Technical_items', 'from_person__name', 'from_person__family', 'to_person__name', 'to_person__family', 'description')
    list_filter = ('action_type', 'action_date', 'item', 'item__status_item')
    ordering = ('-action_date',)
    readonly_fields = ('item', 'from_person', 'to_person', 'action_type', 'action_date', 'description', 'created_at')
    
    def get_item_status(self, obj):
        return obj.item.get_status_item_display()
    get_item_status.short_description = "وضعیت کالا"
    
    def get_change_summary(self, obj):
        """ایجاد شرح کوتاه از تغییرات انجام شده"""
        action_display = obj.get_action_type_display()
        
        if obj.action_type == 'assign':
            if obj.to_person:
                return f"تخصیص به {obj.to_person.name} {obj.to_person.family}"
            else:
                return "تخصیص بدون مالک"
                
        elif obj.action_type == 'transfer':
            from_name = f"{obj.from_person.name} {obj.from_person.family}" if obj.from_person else "انبار"
            to_name = f"{obj.to_person.name} {obj.to_person.family}" if obj.to_person else "انبار"
            return f"انتقال از {from_name} به {to_name}"
            
        elif obj.action_type == 'return':
            if obj.from_person:
                return f"بازگشت از {obj.from_person.name} {obj.from_person.family}"
            else:
                return "بازگشت به انبار"
                
        elif obj.action_type == 'maintenance':
            return f"ارسال به تعمیر - {obj.item.get_status_item_display()}"
            
        else:
            # برای سایر موارد
            if obj.description:
                return obj.description[:50] + "..." if len(obj.description) > 50 else obj.description
            return action_display
    
    get_change_summary.short_description = "شرح تغییر"
    
    def has_add_permission(self, request):
        return False
        
    def has_delete_permission(self, request, obj=None):
        return False
        
# admin.site.register(ItemHistory, ItemHistoryAdmin)

# admin.site.register(Documents)   

class MissionAdmin(admin.ModelAdmin):
    list_display = ('types_of_missions','Mission_Description','mission_location','jinfo','time_frame',)
    search_fields = ('mission_location',)

# admin.site.register(Mission, MissionAdmin)

# admin.site.register(Results)

class ItemChangeRequestAdmin(admin.ModelAdmin):
    list_display = ('item', 'owner', 'admin_user', 'action_type', 'status', 'jinfo', 'show_changes')
    list_filter = ('status', 'action_type', 'created_at')
    search_fields = ('item__Technical_items', 'owner__name', 'owner__family', 'admin_user')
    readonly_fields = ('item', 'owner', 'admin_user', 'action_type', 'proposed_changes', 'description', 'created_at')
    ordering = ('-created_at',)
    
    def show_changes(self, obj):
        """نمای�� خلاصه تغییرات"""
        changes = obj.proposed_changes
        if isinstance(changes, dict):
            summary = []
            for field, change in changes.items():
                if isinstance(change, dict) and 'old' in change and 'new' in change:
                    summary.append(f"{field}: {change['old']} → {change['new']}")
            return " | ".join(summary[:2]) + ("..." if len(summary) > 2 else "")
        return "تغییرات موجود"
    
    show_changes.short_description = "تغییرات"
    
    def has_add_permission(self, request):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return obj and obj.status != 'pending'  # فقط درخواست‌های غیر در انتظار قابل حذف هستند

admin.site.register(ItemChangeRequest, ItemChangeRequestAdmin)