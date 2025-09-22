# bot/django_api.py
import os
import httpx
from typing import Any, Callable, Optional

DJANGO_API_BASE = os.getenv("DJANGO_API_BASE", "http://backend:8000")


class DjangoAPI:
    """
    Клиент для взаимодействия с Django REST API.
    1. Получение JWT по username/password (dev-вариант).
    2. Получение информации о текущем пользователе.
    3. Получение списка задач текущего пользователя.
    4. Интеграция бота: получить/создать пользователя по Telegram ID
       и вернуть ему JWT для работы с обычным API.
    """

    def __init__(self, base: str = DJANGO_API_BASE):
        """
        Клиент для взаимодействия с Django REST API.
        :param base: базовый URL, например "http://backend:8000"
        """
        self.base = base.rstrip("/")

    def _url(self, path: str) -> str:
        """
        Построить полный URL для API.
        :param path: путь, например "/api/v1/me"
        :return: полный URL, например "http://backend:8000/api/v1/me
        """
        return f"{self.base}{path}"

    def get_tokens(self, username: str, password: str) -> dict[str, Any]:
        """
        Получить JWT по username/password (dev-вариант).
        :param username: имя пользователя
        :param password: пароль
        :return: {"access": str, "refresh": str}
        """

        r = httpx.post(self._url("/api/token/"), json={"username": username, "password": password}, timeout=5.0)
        r.raise_for_status()
        return r.json()

    def me(self, access: str) -> dict[str, Any]:
        """
        Получить информацию о текущем пользователе.
        :param access: JWT access token
        :return: информация о пользователе
        """
        r = httpx.get(self._url("/api/v1/me"), headers={"Authorization": f"Bearer {access}"}, timeout=5.0)
        r.raise_for_status()
        return r.json()

    # def list_tasks(self, access: str) -> list[dict[str, Any]]:
    #     """
    #     Получить список задач текущего пользователя.
    #     :param access: JWT access token
    #     :return: список задач
    #     """
    #     r = httpx.get(self._url("/api/v1/tasks/"), headers={"Authorization": f"Bearer {access}"}, timeout=5.0)
    #     r.raise_for_status()
    #     return r.json()

    def create_task(self, access: str, payload: dict[str, Any]) -> dict[str, Any]:
        """
        Создать задачу через Django API.
        :param access: JWT access token
        :param payload: данные задачи, например {"title": "...", "due_at": "..."}
        :return: созданный объект задачи
        """
        r = httpx.post(self._url("/api/v1/tasks/"), json=payload, headers={"Authorization": f"Bearer {access}"},
                       timeout=5.0)
        r.raise_for_status()
        return r.json()

    def refresh(self, refresh_token: str) -> dict[str, Any]:
        """
        Обновить access по refresh-токену через SimpleJWT endpoint.
        :param refresh_token: refresh token
        :return: словарь с новым access (и, возможно, refresh)
        """
        r = httpx.post(self._url("/api/token/refresh/"), json={"refresh": refresh_token}, timeout=5.0)
        r.raise_for_status()
        return r.json()

    def bot_auth(self, payload: dict[str, Any], internal_token: str) -> dict[str, Any]:
        """
        Интеграция бота: получить/создать пользователя по Telegram ID
        и вернуть ему JWT для работы с обычным API.
        :param payload: {"telegram_user_id": int, "chat_id": int, "username": str}
        :param internal_token: секретный токен для внутренней аутентификации бота
        :return: {"user": {"id": int, "username": str}, "access": str, "refresh": str}
        """
        headers = {"X-Internal-Token": internal_token}
        r = httpx.post(self._url("/api/v1/bot/auth"), json=payload,
                       headers=headers,
                       # headers={"Authorization": f"Bearer {internal_token}"},
                       timeout=5.0)
        r.raise_for_status()
        return r.json()

    def list_tasks(self, access: str, *, status: Optional[str] = None) -> list[dict[str, Any]]:
        """
        Получить список задач текущего пользователя, с опциональным фильтром по статусу.
        :param access: JWT access token
        :param status: опциональный статус для фильтрации (например, "todo", "in_progress", "done")
        :return: список задач
        """
        params = {}
        if status:
            params["status"] = status
        r = httpx.get(self._url("/api/v1/tasks/"),
                      headers={"Authorization": f"Bearer {access}"},
                      params=params, timeout=5.0)
        r.raise_for_status()
        return r.json()

    def update_task(self, access: str, task_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        """
        Обновить задачу по ID.
        :param access: JWT access token
        :param task_id: ID задачи
        :param payload: данные для обновления задачи
        :return: обновлённый объект задачи
        """
        r = httpx.patch(self._url(f"/api/v1/tasks/{task_id}/"),
                        headers={"Authorization": f"Bearer {access}",
                                 "Content-Type": "application/json"},
                        json=payload, timeout=5.0)
        r.raise_for_status()
        return r.json()

    def list_tasks_paginated(self, access: str, *, status: str | None = None, page: int = 1) -> dict:
        """
        Получить список задач текущего пользователя с пагинацией.
        :param access: JWT access token
        :param status: опциональный статус для фильтрации (например, "todo", "in_progress", "done")
        :param page: номер страницы (по умолчанию 1)
        :return: dict с полями {count, next, previous, results}
        """
        params = {"page": page}
        if status: params["status"] = status
        r = httpx.get(self._url("/api/v1/tasks/"),
                      headers={"Authorization": f"Bearer {access}"},
                      params=params, timeout=5.0)
        r.raise_for_status()
        return r.json()  # dict: {count,next,previous,results}

    def list_categories_paginated(self, access: str, page: int = 1) -> dict:
        """
        Получить список категорий с пагинацией.
        :param access: JWT access token
        :param page: номер страницы (по умолчанию 1)
        :return: dict с полями {count, next, previous, results}
        """
        r = httpx.get(self._url("/api/v1/categories/"),
                      headers={"Authorization": f"Bearer {access}"},
                      params={"page": page}, timeout=5.0)
        r.raise_for_status()
        return r.json()

    def create_category(self, access: str, name: str) -> dict:
        """
        Создать категорию.
        :param access: JWT access token
        :param name: имя категории
        :return: созданный объект категории
        """
        r = httpx.post(self._url("/api/v1/categories/"),
                       headers={"Authorization": f"Bearer {access}", "Content-Type": "application/json"},
                       json={"name": name}, timeout=5.0)
        r.raise_for_status()
        return r.json()

# Вспомогательная обёртка: выполнить вызов, а при 401 — обновить access по refresh и повторить
async def with_auto_refresh(
        chat_id: int,
        store,
        call: Callable[[str], Any],  # функция, принимающая access, например lambda access: api.list_tasks(access)
        refresh_fn: Callable[[str], dict]  # функция, которая по refresh вернёт {"access": "..."}
):
    """
    Вспомогательная обёртка: выполнить вызов, а при 401 — обновить access по refresh и повторить.
    :param chat_id: Telegram chat_id
    :param store: объект хранилища с методами get_auth(chat_id) и update_access(chat_id, new_access)
    :param call: функция, принимающая access, например lambda access: api.list_tasks(access)
    :param refresh_fn: функция, которая по refresh вернёт {"access": "..."}
    :return: результат вызова call

    """
    auth = await store.get_auth(chat_id)
    if not auth:
        raise RuntimeError("not authenticated")
    user_id, access, refresh = auth
    try:
        return call(access)
    except httpx.HTTPStatusError as e:
        if e.response.status_code != 401:
            raise
        # пробуем обновить токен
        new = refresh_fn(refresh)
        new_access = new.get("access")
        if not new_access:
            raise RuntimeError("refresh failed: no access")
        await store.update_access(chat_id, new_access)
        return call(new_access)


api = DjangoAPI()
