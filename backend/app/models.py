from django.db import models
from django.conf import settings


# Create your models here.

# Модель для категорий задач
class Category(models.Model):
    """
    Модель категории задач.
    Категории могут использоваться для группировки задач.
    """
    id = models.BigIntegerField(primary_key=True, editable=False) # Используем BigIntegerField для совместимости с Snowflake ID
    name = models.CharField(max_length=64, unique=True) # Уникальное имя категории
    created_at = models.DateTimeField(auto_now_add=True) # Время создания категории

    def __str__(self) -> str:
        return self.name # Важно для админки и отладки

# Модель для задач
class Task(models.Model):
    """
    Модель задачи.
    Каждая задача связана с пользователем и может иметь несколько категорий.
    """
    # Статусы задач
    class Status(models.TextChoices):
        TODO = "todo", "To Do" # (value, label)
        IN_PROGRESS = "in_progress", "In Progress" # (value, label)
        DONE = "done", "Done" # (value, label)
 
    id = models.BigIntegerField(primary_key=True, editable=False) # Используем BigIntegerField для совместимости с Snowflake ID
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="tasks") 
    title = models.CharField(max_length=200) # Заголовок задачи
    description = models.TextField(blank=True) # Описание задачи
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.TODO) # Статус задачи с выбором
    categories = models.ManyToManyField(Category, related_name="tasks", blank=True) # Категории задачи
    created_at = models.DateTimeField(auto_now_add=True) 
    due_at = models.DateTimeField(null=True, blank=True) # Срок выполнения задачи
    notify_job_id = models.CharField(max_length=64, blank=True, default="") # ID задачи уведомления в Celery

    class Meta:
        indexes = [
            models.Index(fields=["user", "status"]), 
            models.Index(fields=["due_at"]),
        ]

    def __str__(self) -> str:
        return f"[{self.pk}] {self.title}"

# Модель для связи пользователя Django с его Telegram-аккаунтом
class BotProfile(models.Model):
    """
    Связка Django-пользователя с Telegram.
    Один user <-> один telegram_user_id/chat_id.
    """
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="bot_profile") # Связь с пользователем Django
    telegram_user_id = models.BigIntegerField(unique=True) # Уникальный ID пользователя в Telegram
    chat_id = models.BigIntegerField(unique=True) # Уникальный ID чата в Telegram
    created_at = models.DateTimeField(auto_now_add=True) #  Время создания записи

    def __str__(self) -> str:
        return f"user={self.user_id} tg={self.telegram_user_id} chat={self.chat_id}"
    # Метаданные модели
    class Meta:
        indexes = [
            models.Index(fields=["user"]), # Индекс по полю user для быстрого поиска
            models.Index(fields=["telegram_user_id"]), # Индекс по полю telegram_user_id для быстрого поиска
        ]