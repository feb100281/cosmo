from django.http import JsonResponse
from corporate.models import Items

def admin_alert_counts(request):
    # staff-only защита будет через admin_view в urls.py
    no_subcat = Items.objects.filter(subcat__isnull=True).count()
    no_cat = Items.objects.filter(cat__isnull=True).count()

    return JsonResponse({
        "no_subcat": no_subcat,
        "no_cat": no_cat,
        "total": no_subcat + no_cat,
    })
