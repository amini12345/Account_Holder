from django.contrib.auth import views
from django.urls import path
from .views import (
    dashboard, HomeView, ItemCreateView, ItemUpdateView,
    ItemDeleteView, item_detail, ajax_search_items, profiles_view, history_view, export_excel,
    export_excel_fields_selection, generate_excel, import_excel, process_excel, confirm_import,
    documents_list, document_add, document_detail, document_edit, document_delete,
    missions_list, mission_add, mission_edit, mission_delete,
    results_list, result_add, result_edit, result_delete
)
from .viewsreq import (
    ItemUpdateViewWithApproval, change_requests_list, change_request_detail, 
    approve_change_request_admin, reject_change_request_admin, bulk_transfer_items
)
from .excel_import_enhanced import process_excel_enhanced, confirm_import_enhanced, get_sub_status_options
from .excel_comparison import compare_excel_with_items
from .excel_add_items import add_selected_items, get_item_preview
from .excel_edit_item import edit_item_from_comparison, get_sub_status_options_for_edit, apply_excel_data_to_item
from .pdf_export import export_pdf, export_pdf_fields_selection, generate_pdf

app_name = "account"
urlpatterns = [
    path("login/", views.LoginView.as_view(), name="login"),
    #path("logout/", views.LogoutView.as_view(), name="logout"),
    #path(
        #"password_change/", views.PasswordChangeView.as_view(), name="password_change"
    #),
    #path(
        #"password_change/done/",
       # views.PasswordChangeDoneView.as_view(),
       # name="password_change_done",
    #),
   # path("password_reset/", views.PasswordResetView.as_view(), name="password_reset"),
    #path(
        #"password_reset/done/",
       # views.PasswordResetDoneView.as_view(),
       # name="password_reset_done",
   # ),
    #path(
       # "reset/<uidb64>/<token>/",
       # views.PasswordResetConfirmView.as_view(),
       # name="password_reset_confirm",
   # ),
   # path(
       # "reset/done/",
       # views.PasswordResetCompleteView.as_view(),
       # name="password_reset_complete",
   # ),
]

urlpatterns += [
    path("dashboard/", dashboard, name="dashboard"),
    path("", HomeView.as_view(), name="home"),
    path("profiles/", profiles_view, name="profiles"),
    path("history/", history_view, name="history"),
    path("item/add/", ItemCreateView.as_view(), name="item_add"),
    path("item/<int:pk>/", item_detail, name="item_detail"),
    path("item/<int:pk>/edit/", ItemUpdateViewWithApproval.as_view(), name="item_edit"),
    path("item/<int:pk>/delete/", ItemDeleteView.as_view(), name="item_delete"),
    path("ajax/search/", ajax_search_items, name="ajax_search"),
    path("export/excel/fields/", export_excel_fields_selection, name="export_excel_fields_selection"),
    path("export/excel/generate/", generate_excel, name="generate_excel"),
    path("export/excel/", export_excel, name="export_excel"),
    path("export/pdf/fields/", export_pdf_fields_selection, name="export_pdf_fields_selection"),
    path("export/pdf/generate/", generate_pdf, name="generate_pdf"),
    path("export/pdf/", export_pdf, name="export_pdf"),
    path("import/excel/", import_excel, name="import_excel"),
    path("process/excel/", process_excel_enhanced, name="process_excel"),
    path("confirm/import/", confirm_import_enhanced, name="confirm_import"),
    path("compare/excel/", compare_excel_with_items, name="compare_excel"),
    path("add/selected-items/", add_selected_items, name="add_selected_items"),
    path("ajax/item-preview/", get_item_preview, name="get_item_preview"),
    path("ajax/sub-status-options/", get_sub_status_options, name="get_sub_status_options"),
    
    # Excel comparison edit URLs
    path("item/<int:item_id>/edit-from-comparison/", edit_item_from_comparison, name="edit_item_from_comparison"),
    path("ajax/sub-status-options-for-edit/", get_sub_status_options_for_edit, name="get_sub_status_options_for_edit"),
    path("ajax/apply-excel-data/<int:item_id>/", apply_excel_data_to_item, name="apply_excel_data_to_item"),
    
    # Documents URLs
    path("documents/", documents_list, name="documents_list"),
    path("document/add/", document_add, name="document_add"),
    path("document/<int:pk>/", document_detail, name="document_detail"),
    path("document/<int:pk>/edit/", document_edit, name="document_edit"),
    path("document/<int:pk>/delete/", document_delete, name="document_delete"),
    
    # Missions URLs
    path("missions/", missions_list, name="missions_list"),
    path("mission/add/", mission_add, name="mission_add"),
    path("mission/<int:pk>/edit/", mission_edit, name="mission_edit"),
    path("mission/<int:pk>/delete/", mission_delete, name="mission_delete"),
    
    # Results URLs
    path("results/", results_list, name="results_list"),
    path("result/add/", result_add, name="result_add"),
    path("result/<int:pk>/edit/", result_edit, name="result_edit"),
    path("result/<int:pk>/delete/", result_delete, name="result_delete"),
    
    # Change Request URLs
    path("change-requests/", change_requests_list, name="change_requests_list"),
    path("change-request/<int:pk>/", change_request_detail, name="change_request_detail"),
    path("change-request/<int:request_id>/approve/", approve_change_request_admin, name="approve_change_request_admin"),
    path("change-request/<int:request_id>/reject/", reject_change_request_admin, name="reject_change_request_admin"),
    path("bulk-transfer/", bulk_transfer_items, name="bulk_transfer_items"),
]