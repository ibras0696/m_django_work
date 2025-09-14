from django.contrib import admin
from .models import Task, Category

print(">>> admin.py LOADED")

# Регистрируем модель Category в админке
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    """Настройки отображения и управления категориями в админке."""
    
    # Какие поля показывать в списке категорий
    list_display = ("id", "name", "created_at")
    
    # По каким полям можно искать через поисковую строку
    search_fields = ("name",)
    
    # Порядок сортировки по умолчанию — по имени
    ordering = ("name",)


# Регистрируем модель Task в админке
@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    """Настройки отображения и управления задачами в админке."""
    
    # Поля, которые будут видны в списке задач
    list_display = ("id", "title", "user", "status", "due_at", "created_at")
    
    # Фильтры справа: по статусу, дедлайну и пользователю
    list_filter = ("status", "due_at", "user")
    
    # Поля, по которым работает поиск
    search_fields = ("title", "description")
    
    # Сортировка по умолчанию — новые задачи сверху
    ordering = ("-created_at",)
    
    # Для связей ManyToMany (categories) и ForeignKey (user)
    # в админке будут использоваться поля с автодополнением (поиск),
    # что удобно при большом количестве категорий или пользователей
    autocomplete_fields = ("categories", "user")
