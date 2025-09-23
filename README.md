# Task Manager — Django + Telegram Bot

Проект для портфолио: персональный менеджер задач с веб‑API на Django и Telegram‑ботом на Aiogram. Всё упаковано в Docker, поднимается одной командой, демонстрирует продакшн‑подходы и чистую архитектуру.

## ✨ Ключевые особенности

- ⚙️ Backend: Django 5 + DRF + SimpleJWT (JWT‑аутентификация)
- 🤖 Бот: Aiogram 3 + FastAPI (сервер для внутренних маршрутов и жизненного цикла)
- 🗃️ Данные: PostgreSQL (через Docker), Redis для Celery
- 🧵 Фоновые задания: Celery (уведомления по дедлайнам — контур готов)
- 📦 Запуск в один шаг: Docker Compose поднимает БД, backend и бота
- 🧭 Предметная модель: Задачи, Категории, привязка пользователя к Telegram
- 🧩 Продуманный UX в боте: пагинация, фильтры, защита от дублей и ошибок

## 🧱 Архитектура

Монорепозиторий из двух сервисов:

```
backend/   # Django + DRF API
bot/       # FastAPI + Aiogram (Telegram Bot)
```

Поток данных:

- Бот авторизуется во внутреннем эндпоинте `/api/v1/bot/auth` (заголовок X‑Internal‑Token)
- Токены access/refresh хранятся локально в SQLite по chat_id
- DRF выдаёт JWT (SimpleJWT); все REST‑вызовы — через Bearer‑токен
- Celery‑воркер (опционально) может слать уведомления боту через внутренний HTTP‑маршрут

## 📚 Модель предметной области

- Task: id (snowflake), title, status (todo/in_progress/done), due_at, created_at, user, M2M категории
- Category: id (snowflake), name
- BotProfile: связь Django‑пользователя с Telegram (telegram_user_id, chat_id)

Пагинация: стандартная PageNumberPagination, размер страницы — 5.

## 🗺️ Основные эндпоинты API

- POST `/api/v1/bot/auth` — внутренняя авторизация бота (выдаёт JWT для TG‑пользователя)
- GET `/api/v1/me` — профиль текущего пользователя
- `/api/v1/tasks/` — CRUD + фильтры: status, category, due_before, due_after (пагинация)
- `/api/v1/categories/` — CRUD (пагинация)

## 🤖 UX Telegram‑бота

Команды:

- `/start` — привязка Telegram‑аккаунта, сохранение токенов
- `/help` — краткая справка
- `/tasks [todo|in_progress|done]` — список с пагинацией
- `/tasks_compact [фильтр]` — компактный режим (вся страница одним сообщением)
- `/done <id>` — отметить задачу выполненной
- `/cancel <id>` — снять дедлайн
- `/add` — пошаговое добавление (заголовок → категории → дедлайн → подтверждение)

Пагинация:

- Вверху: «Твои задачи (всего: N) — Стр. i/j»
- Стрелки ◀️ ▶️ листают страницы; «Стр. N» — нейтральная кнопка (без перерисовки)

Надёжность:

- Авто‑реавторизация в боте при отсутствии токенов (после перезапуска)
- Аккуратная обработка краевых случаев: «message is not modified», быстрые клики, разный формат API

## 🧪 Быстрый старт (Docker)

Требования: Docker и Docker Compose.

1) Подготовьте переменные окружения (.env.backend, .env.db, .env.bot):

```
# .env.db
POSTGRES_DB=app
POSTGRES_USER=app
POSTGRES_PASSWORD=app

# .env.backend
DATABASE_URL=postgres://app:app@db:5432/app
SECRET_KEY=dev-secret
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/1
BOT_INTERNAL_URL=http://bot:8080/internal/notify-due
BOT_INTERNAL_TOKEN=supersecret

# .env.bot
TELEGRAM_TOKEN=123456:ABC...   # токен вашего бота
INTERNAL_TOKEN=supersecret
DJANGO_API_BASE=http://backend:8000
```

2) Запустите сервисы:

```
docker-compose up --build -d
```

3) Откройте Telegram и отправьте `/start` вашему боту.

## 🧑‍💻 Заметки для разработчиков

- Миграции применяются автоматически при старте backend (collectstatic → migrate → gunicorn)
- Идентификаторы Task/Category — snowflake по умолчанию (короткие, уникальные, удобно сортировать)
- Размер страницы DRF — 5 (см. `backend/proj/settings.py`)

Структура проекта (сокращённо):

```
backend/app/
	models.py         # Task, Category, BotProfile
	views.py          # TaskViewSet, CategoryViewSet, MeView, BotAuthView
	urls.py           # /api/v1/... endpoints
bot/
	main.py           # FastAPI + Aiogram (polling lifecycle)
	storage.py        # SQLite: chat_id → tokens
	service/django_api.py  # HTTP‑клиент + with_auto_refresh
	handlers/         # start, help, tasks, pagination, add, actions
	utils/            # форматирование, пагинация‑клавиатуры, авто‑auth
```

## 🧭 С чего начать чтение кода

- Фильтры бэкенда: `backend/app/views.py::TaskViewSet.get_queryset`
- Пагинация бота: `bot/handlers/pager.py` и клавиатуры `bot/utils/pager.py`
- Паттерн with_auto_refresh: `bot/service/django_api.py`

## ✅ Чек‑лист возможностей

- [x] JWT‑аутентификация через внутренний бот‑эндпоинт
- [x] Пагинация и фильтры по задачам (статус/категории/диапазон дедлайна)
- [x] Компактный режим списка
- [x] Добавление с выбором категорий и разбором дат
- [x] Устойчивый UX в боте (локи, состояние, обработка ошибок)
- [x] Запуск через Docker Compose

## 🖼️ Скриншоты / Демо

Добавьте сюда 2–3 скрина или GIF:

- /tasks с пагинацией и кнопками действий
- /add — шаги создания
- /tasks_compact — страница одним сообщением

## 🔐 Безопасность

- Внутренняя аутентификация бота через X‑Internal‑Token (без JWT)
- Вызовы пользователя — строго по JWT Bearer; токены на стороне бота хранятся локально per‑chat

## 🗺️ Roadmap

- [ ] Перенос хранения токенов в backend (серверные сессии)
- [ ] Рассылка уведомлений о дедлайнах через Celery + внутренний маршрут бота
- [ ] Быстрые фильтры и inline‑поиск в боте
- [ ] Тесты для DRF и хендлеров бота

## 🧩 Стек

- Django 5, DRF, SimpleJWT
- Aiogram 3, FastAPI
- PostgreSQL, Redis, Celery
- Docker, Docker Compose

## 📄 Лицензия

MIT — используйте и адаптируйте свободно.

## 🧪 Тесты (Docker)

Запуск юнит‑тестов из контейнеров (ничего не нужно ставить локально):

- Backend (Django + DRF):

```bash
docker compose build backend-tests
docker compose run --rm backend-tests
```

- Bot (Aiogram + утилиты):

```bash
docker compose build bot-tests
docker compose run --rm bot-tests
```

- Запустить оба и завершить после выполнения:

```bash
docker compose up --build --abort-on-container-exit bot-tests backend-tests
```

Примечания:

- Backend‑тесты используют отдельную тестовую БД; миграции применяются автоматически `manage.py test`.
- Если в VS Code задача "pytest -q" запускается вне контейнера и падает с `Exit Code: 127`, то локально не установлен pytest. Используйте Docker‑команды выше или установите pytest на хосте.