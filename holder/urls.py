from django.urls import path
from . import views
#ارسال فرم برای دیده شدن
urlpatterns = [
    path('register/', views.register, name='register'),
    path('login/', views.login, name='login'),
    path('logout/', views.logout, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('', views.login, name='home'),  
    
#دریافت اطلاعات فرم برای هر فرد
    path('add-document/', views.add_document, name='add_document'),
    path('add-mission/', views.add_mission, name='add_mission'),
    path('add-result/', views.add_result, name='add_result'),
    path('add-item/', views.add_item, name='add_item'),
    
# Ajax endpoints
    path('get-status-sub-items/', views.get_status_sub_items, name='get_status_sub_items'),
    
# Change request endpoints
    path('approve-request/<int:request_id>/', views.approve_change_request, name='approve_change_request'),
    path('reject-request/<int:request_id>/', views.reject_change_request, name='reject_change_request'),
] 