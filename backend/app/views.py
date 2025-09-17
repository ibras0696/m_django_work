from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated, BasePermission
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from django.utils.dateparse import parse_datetime
from django.contrib.auth import get_user_model
from django.conf import settings

from .models import Task, Category, BotProfile
from .serializers import TaskSerializer, CategorySerializer


class CategoryViewSet(viewsets.ModelViewSet):
    # CRUD по категориям. Здесь категории общие (нет фильтра по user).
    queryset = Category.objects.all().order_by("name")
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated]  # доступ только авторизованным


class TaskViewSet(viewsets.ModelViewSet):
    # CRUD по задачам текущего пользователя
    serializer_class = TaskSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # База: только задачи текущего пользователя, с предзагрузкой категорий и сортировкой по дате создания (новые сверху)
        qs = (
            Task.objects
            .filter(user=self.request.user)
            .prefetch_related("categories")
            .order_by("-created_at")
        )

        # Фильтр по статусу (?status=todo|in_progress|done ... — зависит от модели)
        status_ = self.request.query_params.get("status")
        if status_:
            qs = qs.filter(status=status_)

        # Фильтр по категории через её id (?category=3)
        category = self.request.query_params.get("category")
        if category:
            qs = qs.filter(categories__id=category)

        # Фильтр: дедлайн до (включительно). Ожидается ISO-дата/время.
        # Примеры: 2025-09-20T18:00:00Z или 2025-09-20T21:00:00+03:00
        due_before = self.request.query_params.get("due_before")
        if due_before:
            dt = parse_datetime(due_before)
            if dt:
                qs = qs.filter(due_at__lte=dt)

        # Фильтр: дедлайн после (включительно)
        due_after = self.request.query_params.get("due_after")
        if due_after:
            dt = parse_datetime(due_after)
            if dt:
                qs = qs.filter(due_at__gte=dt)

        return qs

    def perform_create(self, serializer):
        # Сохранение идёт через сериализатор; user берётся внутри TaskSerializer.create()
        serializer.save()


class MeView(APIView):
    """
    Возвращает сведения о текущем пользователе:
    id, username, email — этого достаточно для бота.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        return Response({
            "id": user.id,
            "username": user.get_username(),
            "email": getattr(user, "email", None),
        })


class IsBotInternal(BasePermission):
    """
    Пускаем только если заголовок X-Internal-Token совпадает с BOT_INTERNAL_TOKEN.
    Так мы не используем Authorization и не конфликтуем с JWT.
    """
    def has_permission(self, request, view):
        given = request.headers.get("X-Internal-Token", "")
        expected = getattr(settings, "BOT_INTERNAL_TOKEN", "")
        return bool(expected) and given == expected


class BotAuthView(APIView):
    
    authentication_classes = []     # ← отключаем разбор Authorization
    permission_classes = [IsBotInternal]

    def post(self, request):
        tg_id = int(request.data.get("telegram_user_id", 0))
        chat_id = int(request.data.get("chat_id", 0))
        username = (request.data.get("username") or "").strip() or f"tg_{tg_id}"

        if not tg_id or not chat_id:
            # telegram_user_id и chat_id обязательны
            return Response({"detail": "telegram_user_id and chat_id are required"}, status=status.HTTP_400_BAD_REQUEST)

        User = get_user_model()
        # Ищем профиль по telegram_user_id
        prof = BotProfile.objects.select_related("user").filter(telegram_user_id=tg_id).first()
        if prof:
            if prof.chat_id != chat_id:
                prof.chat_id = chat_id
                prof.save(update_fields=["chat_id"])
            user = prof.user
        else:
            base_username = username
            i = 0
            while User.objects.filter(username=username).exists():
                i += 1
                username = f"{base_username}_{i}"
            user = User.objects.create_user(username=username)
            user.set_unusable_password()
            user.save()
            BotProfile.objects.create(user=user, telegram_user_id=tg_id, chat_id=chat_id)

        refresh = RefreshToken.for_user(user)
        # Возвращаем user.id, username, access и refresh токены
        return Response({
            "user": {"id": user.id, "username": user.username},
            "access": str(refresh.access_token),
            "refresh": str(refresh),
        }, status=status.HTTP_200_OK)