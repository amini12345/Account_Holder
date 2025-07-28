from django.db.models import Count, Q
from .models import PersonalInfo, Items, Documents, Mission, Results

def admin_stats(request):
    """
    Context processor to provide statistics for the admin dashboard
    """
    if not request.path.startswith('/admin/'):
        return {}
    
    try:
        # Calculate statistics
        total_persons = PersonalInfo.objects.count()
        total_items = Items.objects.count()
        items_in_repair = Items.objects.filter(status_item='hardware').count()
        items_in_warehouse = Items.objects.filter(status_item='warehouse').count()
        items_in_delivery = Items.objects.filter(status_item='Delivery').count()
        total_documents = Documents.objects.count()
        total_missions = Mission.objects.count()
        total_results = Results.objects.count()
        
        # Additional statistics
        active_persons = PersonalInfo.objects.annotate(
            items_count=Count('items')
        ).filter(items_count__gt=0).count()
        
        technical_items = Items.objects.filter(type_Item='Technical').count()
        non_technical_items = Items.objects.filter(type_Item='Non-technical').count()
        
        online_trainings = Documents.objects.filter(Type_of_training='online').count()
        offline_trainings = Documents.objects.filter(Type_of_training='offline').count()
        
        return {
            'total_persons': total_persons,
            'total_items': total_items,
            'items_in_repair': items_in_repair,
            'items_in_warehouse': items_in_warehouse,
            'items_in_delivery': items_in_delivery,
            'total_documents': total_documents,
            'total_missions': total_missions,
            'total_results': total_results,
            'active_persons': active_persons,
            'technical_items': technical_items,
            'non_technical_items': non_technical_items,
            'online_trainings': online_trainings,
            'offline_trainings': offline_trainings,
        }
    except Exception as e:
        # Return empty stats if there's an error (e.g., during migrations)
        return {
            'total_persons': 0,
            'total_items': 0,
            'items_in_repair': 0,
            'items_in_warehouse': 0,
            'items_in_delivery': 0,
            'total_documents': 0,
            'total_missions': 0,
            'total_results': 0,
            'active_persons': 0,
            'technical_items': 0,
            'non_technical_items': 0,
            'online_trainings': 0,
            'offline_trainings': 0,
        }