from rest_framework import serializers
from .models import Task, Category

class CategorySerializer(serializers.ModelSerializer):
    """
    Сериализатор категории.
    Используется как вложенный (read-only) внутри задач,
    а также может применяться отдельно, если нужно отдавать/принимать категории.
    """
    class Meta:
        model = Category
        # Отдаём идентификатор, имя и дату создания
        fields = ("id", "name", "created_at")


class TaskSerializer(serializers.ModelSerializer):
    """
    Сериализатор задачи.
    Две ключевые идеи:
    1) Отдаём связанные категории как вложенные объекты (categories) — только для чтения.
    2) Принимаем категории на запись через список ID (category_ids) — только для записи.
    Такой паттерн удобен: клиент отправляет компактные ID, а получает развернутые объекты.
    """

    # Вложенное представление категорий в ответе (read-only),
    # чтобы не пришлось на клиенте делать второй запрос за именами категорий.
    categories = CategorySerializer(many=True, read_only=True)

    # Входное поле для установки связей M2M:
    # список целых чисел — первичных ключей Category.
    # - write_only=True: поле не попадает в ответы
    # - required=False: можно не присылать вообще
    # - default=list: если поле не пришло, validated_data получит []
    category_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False,
        default=list
    )

    class Meta:
        model = Task
        fields = (
            "id",
            "title",
            "description",
            "status",
            "categories",   # read-only, вложенные объекты
            "category_ids", # write-only, список ID для входа
            "created_at",
            "due_at",
        )

    def create(self, validated_data):
        """
        Создание задачи:
        - извлекаем category_ids из валидированных данных;
        - создаём Task, привязывая автора как request.user (берётся из context);
        - если список категорий передан — выставляем связи через set().

        NB: Если среди category_ids есть несуществующие ID, они тихо игнорируются,
        т.к. берём Category.objects.filter(id__in=...).
        """
        cat_ids = validated_data.pop("category_ids", [])
        # self.context["request"] ожидается в контексте сериализатора (DRF делает это сам во вьюсетах)
        task = Task.objects.create(user=self.context["request"].user, **validated_data)

        if cat_ids:
            # set(...) перезаписывает множество связей
            task.categories.set(Category.objects.filter(id__in=cat_ids))
        return task

    def update(self, instance, validated_data):
        """
        Обновление задачи:
        - забираем category_ids, если пришли (может не прийти вовсе);
        - обновляем остальные простые поля;
        - если category_ids передали (в т.ч. пустой список) — перезаписываем связи.
          Пустой список эквивалентен «очистить все категории».

        NB: Если category_ids НЕ пришли, связи остаются без изменений.
        """
        cat_ids = validated_data.pop("category_ids", None)

        # Обновляем простые (не M2M) поля
        for k, v in validated_data.items():
            setattr(instance, k, v)
        instance.save()

        # Если клиент явно прислал category_ids — синхронизируем связи
        if cat_ids is not None:
            instance.categories.set(Category.objects.filter(id__in=cat_ids))
        return instance
