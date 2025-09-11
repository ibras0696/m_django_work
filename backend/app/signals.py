from django.db.models.signals import pre_save
from django.dispatch import receiver
from .models import Task, Category
from .ids import snowflake_id

# Сигнал для установки Snowflake ID перед сохранением категории
@receiver(pre_save, sender=Category)
def category_set_id(sender, instance: Category, **kwargs):
    if not instance.id: # Если ID ещё не установлен
        instance.id = snowflake_id() # Генерируем новый Snowflake ID

# Сигнал для установки Snowflake ID перед сохранением задачи
@receiver(pre_save, sender=Task)
def task_set_id(sender, instance: Task, **kwargs):
    if not instance.id: # Если ID ещё не установлен
        instance.id = snowflake_id() # Генерируем новый Snowflake ID
