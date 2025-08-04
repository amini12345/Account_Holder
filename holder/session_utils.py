"""
ابزارهای مدیریت Session برای پنل کاربری
"""

class HolderSessionManager:
    """مدیریت Session برای پنل کاربری با جلوگیری از تداخل"""
    
    PREFIX = 'holder_'
    USER_ID_KEY = f'{PREFIX}user_id'
    USER_NAME_KEY = f'{PREFIX}user_name'
    LOGGED_IN_KEY = f'{PREFIX}logged_in'
    
    @classmethod
    def login_user(cls, request, user):
        """ورود کاربر و تنظیم session"""
        request.session[cls.USER_ID_KEY] = user.Personnel_number
        request.session[cls.USER_NAME_KEY] = f"{user.name} {user.family}"
        request.session[cls.LOGGED_IN_KEY] = True
        request.session.modified = True
    
    @classmethod
    def logout_user(cls, request):
        """خروج کاربر و پاک کردن session های مربوطه"""
        keys_to_remove = [key for key in request.session.keys() 
                         if key.startswith(cls.PREFIX)]
        for key in keys_to_remove:
            del request.session[key]
        request.session.modified = True
    
    @classmethod
    def get_user_id(cls, request):
        """دریافت شناسه کاربر"""
        return request.session.get(cls.USER_ID_KEY)
    
    @classmethod
    def get_user_name(cls, request):
        """دریافت نام کاربر"""
        return request.session.get(cls.USER_NAME_KEY)
    
    @classmethod
    def is_authenticated(cls, request):
        """بررسی اینکه آیا کاربر وارد شده است"""
        return cls.USER_ID_KEY in request.session and request.session.get(cls.LOGGED_IN_KEY, False)
    
    @classmethod
    def check_conflicts(cls, request):
        """بررسی تداخل با سیستم احراز هویت Django"""
        conflicts = []
        
        # بررسی Django authentication
        if request.user.is_authenticated:
            conflicts.append({
                'type': 'django_auth',
                'message': 'کاربر در پنل مدیریت وارد شده است',
                'user': request.user.username
            })
        
        # بررسی session های مشکوک
        suspicious_keys = ['user_id', 'user_name', '_auth_user_id']
        for key in suspicious_keys:
            if key in request.session and not key.startswith(cls.PREFIX):
                conflicts.append({
                    'type': 'session_conflict',
                    'message': f'کلید session مشکوک: {key}',
                    'key': key,
                    'value': request.session[key]
                })
        
        return conflicts