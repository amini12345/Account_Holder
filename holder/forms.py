from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError
from .models import PersonalInfo, Items, Documents, Mission, Results, ItemHistory

class PersonalInfoRegistrationForm(forms.ModelForm):
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'تایید رمز عبور'}), 
        label="تایید رمز عبور"
    )
    
    class Meta:
        model = PersonalInfo
        fields = ['name', 'family', 'Personnel_number', 'National_ID', 
                  'date_of_birth', 'email', 'phone_number', 'Educational_degree', 'password']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'نام'}),
            'family': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'نام خانوادگی'}),
            'Personnel_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'شماره پرسنلی 9 رقمی'}),
            'National_ID': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'کد ملی 10 رقمی'}),
            'password': forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'رمز عبور'}),
            'date_of_birth': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'ایمیل (اختیاری)'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'شماره همراه'}),
            'Educational_degree': forms.Select(attrs={'class': 'form-control'}),
        }
        labels = {
            'name': 'نام',
            'family': 'نام خانوادگی',
            'Personnel_number': 'شماره پرسنلی',
            'National_ID': 'کد ملی',
            'date_of_birth': 'تاریخ تولد',
            'email': 'ایمیل',
            'phone_number': 'شماره همراه',
            'Educational_degree': 'مدرک تحصیلی',
            'password': 'رمز عبور'
        }
    
    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')
        
        if password and confirm_password and password != confirm_password:
            self.add_error('confirm_password', "رمز عبور و تایید رمز عبور یکسان نیستند")
        
        return cleaned_data

    def clean_Personnel_number(self):
        personnel_number = self.cleaned_data.get('Personnel_number')
        if personnel_number and len(personnel_number) != 9:
            raise ValidationError("شماره پرسنلی باید 9 رقم باشد")
        return personnel_number

    def clean_National_ID(self):
        national_id = self.cleaned_data.get('National_ID')
        if national_id and len(national_id) != 10:
            raise ValidationError("کد ملی باید 10 رقم باشد")
        return national_id

class CustomLoginForm(forms.Form):
    Personnel_number = forms.CharField(
        max_length=9, 
        label="شماره پرسنلی",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'شماره پرسنلی'})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'رمز عبور'}), 
        label="رمز عبور"
    ) 

# فرم‌های جدید برای اضافه کردن اطلاعات
class ItemForm(forms.ModelForm):
    class Meta:
        model = Items
        fields = ['Technical_items', 'type_Item', 'status_item', 'status_sub_item', 
                  'brand', 'Configuration', 'serial_number', 'Product_code', 'PersonalInfo']
        labels = {
            'Technical_items': 'نام کالا',
            'type_Item': 'نوع کالا',
            'status_item': 'وضعیت کالا',
            'status_sub_item': 'زیر مجموعه وضعیت',
            'brand': 'برند',
            'Configuration': 'پیکربندی',
            'serial_number': 'شماره سریال',
            'Product_code': 'کد محصول',
            'PersonalInfo': 'دارنده حساب'
        }
        widgets = {
            'Technical_items': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'نام کالا'}),
            'type_Item': forms.Select(attrs={'class': 'form-control'}),
            'status_item': forms.Select(attrs={'class': 'form-control'}),
            'status_sub_item': forms.Select(attrs={'class': 'form-control'}),
            'brand': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'برند'}),
            'Configuration': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'پیکربندی'}),
            'serial_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'شماره سریال'}),
            'Product_code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'کد محصول'}),
            'PersonalInfo': forms.Select(attrs={'class': 'form-control'}),
        }

class ItemHistoryForm(forms.ModelForm):
    class Meta:
        model = ItemHistory
        fields = ['item', 'from_person', 'to_person', 'action_type', 'description']
        labels = {
            'item': 'کالا',
            'from_person': 'از شخص',
            'to_person': 'به شخص',
            'action_type': 'نوع اقدام',
            'description': 'توضیحات'
        }
        widgets = {
            'item': forms.Select(attrs={'class': 'form-control'}),
            'from_person': forms.Select(attrs={'class': 'form-control'}),
            'to_person': forms.Select(attrs={'class': 'form-control'}),
            'action_type': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'توضیحات'}),
        }

class DocumentForm(forms.ModelForm):
    class Meta:
        model = Documents
        fields = ['name_document', 'start_date', 'end_date', 'Training_hours', 
                  'Training_costs', 'Training_location', 'Type_of_training', 'PersonalInfo']
        labels = {
            'name_document': 'نام مدرک',
            'start_date': 'تاریخ شروع',
            'end_date': 'تاریخ پایان',
            'Training_hours': 'ساعت آموزشی',
            'Training_costs': 'هزینه آموزشی (ریال)',
            'Training_location': 'محل آموزشی',
            'Type_of_training': 'نوع آموزش',
            'PersonalInfo': 'شرکت کنندگان'
        }
        widgets = {
            'name_document': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'نام مدرک'}),
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'Training_hours': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'ساعت آموزشی'}),
            'Training_costs': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'هزینه آموزشی'}),
            'Training_location': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'محل آموزشی'}),
            'Type_of_training': forms.Select(attrs={'class': 'form-control'}),
            'PersonalInfo': forms.SelectMultiple(attrs={'class': 'form-control', 'size': '5'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        
        if start_date and end_date and start_date > end_date:
            self.add_error('end_date', "تاریخ پایان نمی‌تواند قبل از تاریخ شروع باشد")
        
        return cleaned_data

class MissionForm(forms.ModelForm):
    class Meta:
        model = Mission
        fields = ['types_of_missions', 'Mission_Description', 'mission_location', 
                  'start_date', 'time_frame', 'PersonalInfo']
        labels = {
            'types_of_missions': 'نوع ماموریت',
            'Mission_Description': 'توضیحات (موضوع) ماموریت',
            'mission_location': 'محل (مقصد) ماموریت',
            'start_date': 'تاریخ شروع',
            'time_frame': 'بازه زمانی ماموریت',
            'PersonalInfo': 'حاضرین در ماموریت'
        }
        widgets = {
            'types_of_missions': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'نوع ماموریت'}),
            'Mission_Description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'توضیحات ماموریت'}),
            'mission_location': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'محل ماموریت'}),
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'time_frame': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'تعداد روز ماموریت'}),
            'PersonalInfo': forms.SelectMultiple(attrs={'class': 'form-control', 'size': '5'}),
        }

class ResultForm(forms.ModelForm):
    class Meta:
        model = Results
        fields = ['Date_of_submission', 'Internal_meetings', 'Meeting_Minutes', 'PersonalInfo']
        labels = {
            'Date_of_submission': 'تاریخ تحویل',
            'Internal_meetings': 'جلسات داخلی',
            'Meeting_Minutes': 'صورت جلسات',
            'PersonalInfo': 'دارنده حساب'
        }
        widgets = {
            'Date_of_submission': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'Internal_meetings': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'تعداد جلسات داخلی'}),
            'Meeting_Minutes': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'صورت جلسات'}),
            'PersonalInfo': forms.Select(attrs={'class': 'form-control'}),
        }

# فرم جستجو و فیلتر
class ItemSearchForm(forms.Form):
    search_query = forms.CharField(
        max_length=100, 
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'جستجو در نام کالا، برند، شماره سریال...'}),
        label="جستجو"
    )
    type_Item = forms.ChoiceField(
        choices=[('', 'همه')] + list(Items.TYPE_CHOICES),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label="نوع کالا"
    )
    status_item = forms.ChoiceField(
        choices=[('', 'همه')] + list(Items.STATUS_CHOICES),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label="وضعیت کالا"
    )
    PersonalInfo = forms.ModelChoiceField(
        queryset=PersonalInfo.objects.all(),
        required=False,
        empty_label="همه",
        widget=forms.Select(attrs={'class': 'form-control'}),
        label="دارنده حساب"
    )

class PersonSearchForm(forms.Form):
    search_query = forms.CharField(
        max_length=100, 
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'جستجو در نام، نام خانوادگی، شماره پرسنلی...'}),
        label="جستجو"
    )
    Educational_degree = forms.ChoiceField(
        choices=[('', 'همه')] + list(PersonalInfo.STATUS_CHOICES),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label="مدرک تحصیلی"
    ) 