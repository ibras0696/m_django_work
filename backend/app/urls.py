from django.urls import path
from django.http import JsonResponse

def healthz(_):
    return JsonResponse({"ok": True, "service": "backend"})

urlpatterns = [path("healthz", healthz)]
