from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Category",
            fields=[
                ("id", models.BigIntegerField(primary_key=True, serialize=False, editable=False)),
                ("name", models.CharField(max_length=64, unique=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name="Task",
            fields=[
                ("id", models.BigIntegerField(primary_key=True, serialize=False, editable=False)),
                ("title", models.CharField(max_length=200)),
                ("description", models.TextField(blank=True)),
                (
                    "status",
                    models.CharField(
                        max_length=20,
                        choices=[
                            ("todo", "To Do"),
                            ("in_progress", "In Progress"),
                            ("done", "Done"),
                        ],
                        default="todo",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("due_at", models.DateTimeField(blank=True, null=True)),
                ("notify_job_id", models.CharField(max_length=64, blank=True, default="")),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="tasks",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="BotProfile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("telegram_user_id", models.BigIntegerField(unique=True)),
                ("chat_id", models.BigIntegerField(unique=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="bot_profile",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.AddField(
            model_name="task",
            name="categories",
            field=models.ManyToManyField(blank=True, related_name="tasks", to="app.category"),
        ),
        migrations.AddIndex(
            model_name="task",
            index=models.Index(fields=["user", "status"], name="app_task_user_status_idx"),
        ),
        migrations.AddIndex(
            model_name="task",
            index=models.Index(fields=["due_at"], name="app_task_due_at_idx"),
        ),
        migrations.AddIndex(
            model_name="botprofile",
            index=models.Index(fields=["user"], name="app_botprof_user_idx"),
        ),
        migrations.AddIndex(
            model_name="botprofile",
            index=models.Index(fields=["telegram_user_id"], name="app_botprof_tg_idx"),
        ),
    ]
