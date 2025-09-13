# 0) Быстрый план запуска

```bash
# Сборка и старт всего стека
docker-compose up --build -d

# Логи (в реальном времени)
docker-compose logs -f backend
docker-compose logs -f worker
docker-compose logs -f bot
docker-compose logs -f db
docker-compose logs -f redis

# Остановка, снос контейнеров
docker-compose down

# Полный снос вместе с томами БД/кеша (ОСТОРОЖНО!)
docker-compose down -v
```

# 1) Важные адреса (локально)

* Backend health: `http://localhost:8000/healthz`
* Admin: `http://localhost:8000/admin`
* Bot health: `http://localhost:8080/internal/healthz`
* JWT:

  * `POST /api/token/`
  * `POST /api/token/refresh`
* API:

  * `GET|POST /api/v1/categories/`
  * `GET|PATCH|DELETE /api/v1/categories/{id}/`
  * `GET|POST /api/v1/tasks/`
  * `GET|PATCH|DELETE /api/v1/tasks/{id}/`

# 2) .env файлы (в корне репо)

**.env.db**

```
POSTGRES_DB=app
POSTGRES_USER=app
POSTGRES_PASSWORD=app
```

**.env.backend**

```
# Django
SECRET_KEY=dev-secret
DEBUG=1
ALLOWED_HOSTS=*
TIME_ZONE=America/Adak
WORKER_ID=0

# DB & Celery
DATABASE_URL=postgres://app:app@db:5432/app
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/1

# Bot internal call
BOT_INTERNAL_URL=http://bot:8080/internal/notify-due
BOT_INTERNAL_TOKEN=supersecret
```

**.env.bot**

```
TELEGRAM_TOKEN=put-your-telegram-bot-token
INTERNAL_TOKEN=supersecret
DJANGO_API_BASE=http://backend:8000
```

# 3) Управление Django из контейнера

```bash
# миграции
docker-compose exec backend python manage.py makemigrations
docker-compose exec backend python manage.py migrate

# суперпользователь
docker-compose exec backend python manage.py createsuperuser

# открыть Django shell
docker-compose exec backend python manage.py shell
```

# 4) Получить JWT и ходить в API (через curl)

```bash
# 4.1 Получить токены
curl -s http://localhost:8000/api/token/ \
  -H "Content-Type: application/json" \
  -d '{"username":"<login>","password":"<pass>"}'

# Сохраним access токен в переменную (bash/git-bash)
ACCESS=<вставь_значение_access_из_ответа>
```

```bash
# 4.2 Создать категорию
curl -s -X POST http://localhost:8000/api/v1/categories/ \
  -H "Authorization: Bearer $ACCESS" \
  -H "Content-Type: application/json" \
  -d '{"name":"Work"}'

# 4.3 Получить список категорий
curl -s http://localhost:8000/api/v1/categories/ \
  -H "Authorization: Bearer $ACCESS"
```

```bash
# 4.4 Создать задачу
# ВАЖНО: due_at в ISO8601, TZ = America/Adak (укажи оффсет, например -09:00)
curl -s -X POST http://localhost:8000/api/v1/tasks/ \
  -H "Authorization: Bearer $ACCESS" \
  -H "Content-Type: application/json" \
  -d '{
        "title":"Demo task",
        "description":"check DRF",
        "category_ids":[<ID_категории>],
        "due_at":"2025-09-12T10:00:00-09:00"
      }'

# 4.5 Список моих задач (фильтры)
curl -s "http://localhost:8000/api/v1/tasks/?status=todo" \
  -H "Authorization: Bearer $ACCESS"

curl -s "http://localhost:8000/api/v1/tasks/?category=<ID_категории>&due_before=2025-09-30T00:00:00-09:00" \
  -H "Authorization: Bearer $ACCESS"

# 4.6 Обновить задачу
curl -s -X PATCH http://localhost:8000/api/v1/tasks/<TASK_ID>/ \
  -H "Authorization: Bearer $ACCESS" \
  -H "Content-Type: application/json" \
  -d '{"status":"done"}'

# 4.7 Удалить задачу
curl -s -X DELETE http://localhost:8000/api/v1/tasks/<TASK_ID>/ \
  -H "Authorization: Bearer $ACCESS"
```

# 5) Проверка Celery (ETA-уведомление)

```bash
# Смок-тест: due_at в прошлом => уведомление уйдёт сразу
curl -s -X POST http://localhost:8000/api/v1/tasks/ \
  -H "Authorization: Bearer $ACCESS" \
  -H "Content-Type: application/json" \
  -d '{
        "title":"Ping me now",
        "description":"due in past",
        "category_ids":[],
        "due_at":"2000-01-01T00:00:00-09:00"
      }'

# Логи:
docker-compose logs -f worker
docker-compose logs -f bot   # ждём строку: [BOT] Notify user_id=... task_id=... title=... due_at=...
```

# 6) Модели (краткая дока)

**Category**

* `id: BigInteger (PK, snowflake_id)` — генерим в приложении (без uuid/random/serial)
* `name: Char(64), unique`
* `created_at: DateTime, auto_now_add`

**Task**

* `id: BigInteger (PK, snowflake_id)`
* `user: FK → auth_user`
* `title: Char(200)`
* `description: Text, blank=True`
* `status: todo|in_progress|done (default=todo)`
* `categories: M2M → Category, blank=True`
* `created_at: DateTime, auto_now_add (для бота обязателен)`
* `due_at: DateTime, null=True`
* `notify_job_id: Char(64), служебный id отложенной Celery-задачи`

Индексы: `(user, status)`, `(due_at)`.

Генератор ключей (`app/ids.py`): Snowflake-подобный `BigInt` = `(timestamp_ms << 22) | (worker_id << 12) | sequence`.

# 7) API (сводка)

|  Метод | Путь                       | Описание                    | Тело / Параметры                                     |
| -----: | -------------------------- | --------------------------- | ---------------------------------------------------- |
|   POST | `/api/token/`              | Выдать JWT (access/refresh) | `{"username","password"}`                            |
|   POST | `/api/token/refresh/`      | Обновить access по refresh  | `{"refresh"}`                                        |
|    GET | `/api/v1/categories/`      | Список категорий            | —                                                    |
|   POST | `/api/v1/categories/`      | Создать категорию           | `{"name"}`                                           |
|    GET | `/api/v1/categories/{id}/` | Получить категорию          | —                                                    |
|  PATCH | `/api/v1/categories/{id}/` | Обновить категорию          | `{"name"}`                                           |
| DELETE | `/api/v1/categories/{id}/` | Удалить категорию           | —                                                    |
|    GET | `/api/v1/tasks/`           | Список моих задач + фильтры | `?status=&category=&due_before=&due_after=`          |
|   POST | `/api/v1/tasks/`           | Создать задачу              | `{"title","description?","category_ids?","due_at?"}` |
|    GET | `/api/v1/tasks/{id}/`      | Получить задачу             | —                                                    |
|  PATCH | `/api/v1/tasks/{id}/`      | Обновить задачу             | любые поля модели                                    |
| DELETE | `/api/v1/tasks/{id}/`      | Удалить задачу              | —                                                    |

**Заголовок авторизации для всех защищённых ручек:**
`Authorization: Bearer <ACCESS>`

# 8) Что за таймзона и даты

* В `settings.py`: `TIME_ZONE = "America/Adak"`, `USE_TZ = True`.
* Присылай `due_at` в ISO8601 **с оффсетом** (например, `2025-09-12T10:00:00-09:00`).
* Если оффсет не пришлёшь — DRF постарается разобрать, но лучше не полагаться.

# 9) Частые проблемы → быстрые фиксы

* **Админка «без стилей»** → проверь:

  * `STATIC_URL="/static/"`, `STATIC_ROOT=BASE_DIR/"staticfiles"`;
  * `whitenoise.middleware.WhiteNoiseMiddleware` сразу после `SecurityMiddleware`;
  * в Dockerfile есть `python manage.py collectstatic --noinput`.

* **Backend не видит БД** → в `.env.backend`:

  * `DATABASE_URL=postgres://app:app@db:5432/app` (именно `@db`, не `@localhost`);
  * в compose у `db` сделай `healthcheck`, у `backend` — `depends_on: condition: service_healthy`.

* **Postgres не стартует, требует пароль** → убедись, что `db` берёт `env_file: .env.db`; если менял env — сделай `docker-compose down -v` (снесёт том).

* **Celery не отправляет** → смотри:

  * поднят ли `worker` (`docker-compose ps`);
  * `CELERY_BROKER_URL`/`RESULT_BACKEND` указывают на `redis://redis:6379/...`;
  * логи `worker` и `bot` на ошибки сети/авторизации.

# 10) Мини-FAQ

* **Где менять связи user\_id ↔ chat\_id?** — в боте (своя табличка/файл/БД). Внутренний POST из backend присылает `user_id`, бот должен знать соответствующий `chat_id`.

* **Можно ли боту лезть в БД Django?** — нет. Только REST. Владелец схемы — Django.

* **Как отменяется уведомление при переносе/закрытии задачи?** — сигнал `post_save` делает revoke старого job по `notify_job_id` и ставит новый (или чистит поле, если `due_at` пуст / статус `DONE`).

---
