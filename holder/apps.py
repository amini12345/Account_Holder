from django.apps import AppConfig


class HolderConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'holder'
    verbose_name = "مدیریت فعالیت ها"
    
    def ready(self):
        import holder.signals
