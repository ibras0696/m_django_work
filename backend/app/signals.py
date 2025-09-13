from django.db.models.signals import pre_save, post_save, post_delete
from django.dispatch import receiver
from django.utils import timezone
from celery.app.control import Control
from django.conf import settings
from .models import Task
from .tasks import send_due_notification

@receiver(pre_save, sender=Task)
def task_snapshot_before_save(sender, instance: Task, **kwargs):
    """
    Снимем "старые" поля из базы, чтобы в post_save понять, что поменялось.
    Если запись новая — старых значений нет.
    """
    if instance.pk:
        try:
            old = Task.objects.get(pk=instance.pk)
            instance._old_due_at = old.due_at
            instance._old_notify_job_id = old.notify_job_id
            instance._old_status = old.status
        except Task.DoesNotExist:
            instance._old_due_at = None
            instance._old_notify_job_id = ""
            instance._old_status = None
    else:
        instance._old_due_at = None
        instance._old_notify_job_id = ""
        instance._old_status = None


@receiver(post_save, sender=Task)
def task_schedule_after_save(sender, instance: Task, created: bool, **kwargs):
    """
    Логика перепланирования:
    - Если дедлайна нет → отменить старый job, если был.
    - Если дедлайн есть → отменить старый job (если был) и поставить новый на eta=due_at.
    - Если статус DONE → отменить job (не надо уведомлять).
    """
    # Если статус DONE — просто отменяем и выходим
    if instance.status == Task.Status.DONE:
        if instance._old_notify_job_id:
            _revoke(instance._old_notify_job_id)
            instance.notify_job_id = ""
            instance.save(update_fields=["notify_job_id"])
        return

    due = instance.due_at
    old_due = getattr(instance, "_old_due_at", None)
    old_job = getattr(instance, "_old_notify_job_id", "")

    # Если дедлайн пустой → отменить старое и выйти
    if not due:
        if old_job:
            _revoke(old_job)
            instance.notify_job_id = ""
            instance.save(update_fields=["notify_job_id"])
        return

    # Если дедлайн не изменился и job уже есть — ничего не делаем
    if old_due == due and instance.notify_job_id:
        return

    # Отменяем старую задачу, если была
    if old_job:
        _revoke(old_job)

    # Важно: если due_at уже в прошлом — запускаем немедленно
    eta = due if due > timezone.now() else None
    celery_res = send_due_notification.apply_async(args=[instance.id], eta=eta)
    instance.notify_job_id = celery_res.id
    instance.save(update_fields=["notify_job_id"])


@receiver(post_delete, sender=Task)
def task_cleanup_after_delete(sender, instance: Task, **kwargs):
    """При удалении таски отменяем отложенную задачу (если была)."""
    if instance.notify_job_id:
        _revoke(instance.notify_job_id)


def _revoke(job_id: str):
    """
    Безопасная отмена отложенной задачи.
    terminate=False — не убиваем воркеров, просто отменяем задачу в очереди/скедулере.
    """
    try:
        # Control требует Celery app — берёт из настроенного приложения
        Control(app=None).revoke(job_id, terminate=False)
    except Exception:
        # в тестовом не бросаем дальше (не критично, если нечего отменять)
        pass
