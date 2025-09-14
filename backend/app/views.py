from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response
from django.utils.dateparse import parse_datetime
from .models import Task, Category
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