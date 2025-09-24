from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from django.http import JsonResponse
from .views import TaskViewSet, CategoryViewSet, MeView, BotAuthView


# Health-check ручка.
# Возвращает JSON {"ok": True, "service": "backend"}.
# Обычно такие эндпоинты используют системы мониторинга (например, Kubernetes, Nginx).
def healthz(_):
    return JsonResponse({"ok": True, "service": "backend"})


# Создаём роутер DRF. Он сам генерирует маршруты для ViewSet.
router = DefaultRouter()

# Регистрируем ViewSet для задач.
# basename="task" нужен, чтобы маршруты имели имена "task-list", "task-detail".
# В итоге появятся пути: /api/v1/tasks/, /api/v1/tasks/{id}/
router.register(r"api/v1/tasks", TaskViewSet, basename="task")

# Регистрируем ViewSet для категорий.
# Аналогично: /api/v1/categories/, /api/v1/categories/{id}/
router.register(r"api/v1/categories", CategoryViewSet, basename="category")

# Основной список маршрутов.
urlpatterns = [
    # Health-check endpoint
    path("healthz", healthz),

    # JWT-эндпоинт для получения пары токенов (access + refresh)
    path("api/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),

    # JWT-эндпоинт для обновления access-токена по refresh-токену
    path("api/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/v1/me/", MeView.as_view(), name="me"),
    path("api/v1/bot/auth/", BotAuthView.as_view(), name="bot_auth")
]

# Добавляем к urlpatterns все маршруты, которые сгенерировал DefaultRouter
urlpatterns += router.urls
