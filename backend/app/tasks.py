"""
Задача “отправить уведомление о дедлайне”:
- Проверяет актуальность таски (её статус и due_at)
- Шлёт бот-сервису POST на /internal/notify-due с Bearer-токеном
- Ретраи при временных ошибках сети
"""
from celery import shared_task
from django.utils import timezone
from django.conf import settings
from .models import Task
import httpx

@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def send_due_notification(self, task_id: int):
    # Берём актуальную версию таски
    task = Task.objects.select_related("user").filter(id=task_id).first()
    if not task:
        return  # удалили — некого уведомлять

    # Не уведомляем, если задача завершена ИЛИ дедлайн уже перенесли дальше
    if task.status == Task.Status.DONE:
        return
    if task.due_at and task.due_at > timezone.now():
        # Значит эта задача была запланирована раньше, но дедлайн сдвинулся вперёд
        return

    payload = {
        "user_id": task.user_id,
        "task_id": task.id,
        "title": task.title,
        "due_at": task.due_at.isoformat() if task.due_at else None,
    }
    headers = {"Authorization": f"Bearer {settings.BOT_INTERNAL_TOKEN}"}

    try:
        # Внутренний HTTP-вызов к боту внутри одной docker-сети
        with httpx.Client(timeout=5.0) as client:
            client.post(settings.BOT_INTERNAL_URL, json=payload, headers=headers)
    except Exception as exc:
        # Дадим 3 попытки (см. декоратор)
        raise self.retry(exc=exc)
