from django import forms
from holder.models import Items, PersonalInfo

class ItemForm(forms.ModelForm):
    class Meta:
        model = Items
        fields = ['Technical_items', 'type_Item', 'brand', 'Configuration', 'status_item', 'status_sub_item', 'serial_number', 'Product_code', 'PersonalInfo']
        widgets = {
            'Technical_items': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'نام کالا را وارد کنید'
            }),
            'type_Item': forms.Select(attrs={
                'class': 'form-control'
            }),
            'brand': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'برند کالا (اختیاری)'
            }),
            'Configuration': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'پیکربندی و مشخصات کالا (اختیاری)',
                'rows': 3
            }),
            'status_item': forms.Select(attrs={
                'class': 'form-control',
                'id': 'id_status_item'
            }),
            'status_sub_item': forms.Select(attrs={
                'class': 'form-control',
                'id': 'id_status_sub_item'
            }),
            'serial_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'شماره سریال (اختیاری)'
            }),
            'Product_code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'کد محصول (اختیاری)'
            }),
            'PersonalInfo': forms.Select(attrs={
                'class': 'form-control'
            }),
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # سفارشی کردن نمایش PersonalInfo
        self.fields['PersonalInfo'].queryset = PersonalInfo.objects.all()
        self.fields['PersonalInfo'].empty_label = "انتخاب دارنده حساب"
        
        # اضافه کردن label های فارسی
        self.fields['Technical_items'].label = "نام کالا"
        self.fields['type_Item'].label = "نوع کالا"
        self.fields['brand'].label = "برند"
        self.fields['Configuration'].label = "پیکربندی"
        self.fields['status_item'].label = "وضعیت کالا"
        self.fields['status_sub_item'].label = "زیر مجموعه وضعیت"
        self.fields['serial_number'].label = "شماره سریال"
        self.fields['Product_code'].label = "کد محصول"
        self.fields['PersonalInfo'].label = "دارنده حساب"
        
        # اضافه کردن help text
        self.fields['Technical_items'].help_text = "نام کالا یا تجهیزات را وارد کنید"
        self.fields['brand'].help_text = "برند یا سازنده کالا (اختیاری)"
        self.fields['Configuration'].help_text = "مشخصات فنی، پیکربندی و جزئیات کالا (اختیاری)"
        self.fields['status_item'].help_text = "وضعیت فعلی کالا را انتخاب کنید"
        self.fields['status_sub_item'].help_text = "زیر مجموعه وضعیت کالا (اختیاری)"
        self.fields['serial_number'].help_text = "شماره سریال کالا (در صورت وجود)"
        self.fields['Product_code'].help_text = "کد محصول یا شناسه کالا (در صورت وجود)"
        
        # تنظیم گزینه‌های اولیه برای status_sub_item
        self.fields['status_sub_item'].required = False
        self.fields['status_sub_item'].empty_label = "انتخاب کنید"