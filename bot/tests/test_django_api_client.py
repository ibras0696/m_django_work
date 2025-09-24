import sys
import unittest
import types

# Stub httpx BEFORE importing module under test to avoid import-time failure
httpx_stub = types.ModuleType("httpx")
class _HTTPStatusError(Exception):
    def __init__(self, *args, request=None, response=None):
        super().__init__(*args)
        self.request = request
        self.response = response
httpx_stub.HTTPStatusError = _HTTPStatusError
sys.modules.setdefault("httpx", httpx_stub)

import bot.service.django_api as api_mod


class FakeResponse:
    def __init__(self, status_code=200, data=None):
        self.status_code = status_code
        self._data = data or {}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self):
        return self._data


class FakeHTTPX:
    def __init__(self):
        self.calls = []  # list of dicts with method, url, kwargs
        self._queue = []  # queued responses per call
        # provide HTTPStatusError attribute so code expecting httpx.HTTPStatusError doesn't break
        self.HTTPStatusError = type("HTTPStatusError", (Exception,), {})

    def queue(self, status_code=200, data=None):
        self._queue.append(FakeResponse(status_code=status_code, data=data))

    def _next(self):
        if not self._queue:
            return FakeResponse(200, {})
        return self._queue.pop(0)

    def post(self, url, **kwargs):
        self.calls.append({"method": "POST", "url": url, **kwargs})
        return self._next()

    def get(self, url, **kwargs):
        self.calls.append({"method": "GET", "url": url, **kwargs})
        return self._next()

    def patch(self, url, **kwargs):
        self.calls.append({"method": "PATCH", "url": url, **kwargs})
        return self._next()


class TestDjangoAPI(unittest.TestCase):
    def setUp(self):
        # replace httpx in module with fake
        self.fx = FakeHTTPX()
        self._orig_httpx = getattr(api_mod, "httpx", None)
        api_mod.httpx = self.fx
        self.api = api_mod.DjangoAPI(base="http://backend:8000")

    def tearDown(self):
        # restore original httpx to avoid interference with other tests
        if self._orig_httpx is not None:
            api_mod.httpx = self._orig_httpx

    def test_get_tokens(self):
        self.fx.queue(200, {"access": "a", "refresh": "r"})
        res = self.api.get_tokens("u", "p")
        self.assertEqual(res, {"access": "a", "refresh": "r"})
        call = self.fx.calls[0]
        self.assertEqual(call["method"], "POST")
        self.assertTrue(call["url"].endswith("/api/token/"))
        self.assertEqual(call["json"], {"username": "u", "password": "p"})

    def test_me(self):
        self.fx.queue(200, {"id": 1, "username": "u"})
        res = self.api.me("acc")
        self.assertEqual(res["id"], 1)
        call = self.fx.calls[-1]
        self.assertEqual(call["method"], "GET")
        self.assertTrue(call["url"].endswith("/api/v1/me"))
        self.assertIn("Authorization", call["headers"])  # Bearer header

    def test_create_task(self):
        payload = {"title": "X"}
        self.fx.queue(200, {"id": 10, "title": "X"})
        res = self.api.create_task("acc", payload)
        self.assertEqual(res["id"], 10)
        call = self.fx.calls[-1]
        self.assertEqual(call["method"], "POST")
        self.assertTrue(call["url"].endswith("/api/v1/tasks/"))
        self.assertEqual(call["json"], payload)

    def test_refresh(self):
        self.fx.queue(200, {"access": "new"})
        res = self.api.refresh("r1")
        self.assertEqual(res["access"], "new")
        call = self.fx.calls[-1]
        self.assertEqual(call["method"], "POST")
        self.assertTrue(call["url"].endswith("/api/token/refresh/"))
        self.assertEqual(call["json"], {"refresh": "r1"})

    def test_bot_auth(self):
        payload = {"telegram_user_id": 100, "chat_id": 200, "username": "tg"}
        self.fx.queue(200, {"user": {"id": 1}, "access": "a", "refresh": "r"})
        res = self.api.bot_auth(payload, internal_token="sec")
        self.assertIn("access", res)
        call = self.fx.calls[-1]
        self.assertEqual(call["method"], "POST")
    self.assertTrue(call["url"].endswith("/api/v1/bot/auth/"))
        self.assertEqual(call["json"], payload)
        self.assertEqual(call["headers"].get("X-Internal-Token"), "sec")

    def test_list_tasks_and_filters(self):
        self.fx.queue(200, [{"id": 1}])
        res = self.api.list_tasks("acc", status="todo")
        self.assertEqual(res, [{"id": 1}])
        call = self.fx.calls[-1]
        self.assertEqual(call["method"], "GET")
        self.assertTrue(call["url"].endswith("/api/v1/tasks/"))
        self.assertEqual(call["params"], {"status": "todo"})

    def test_update_task(self):
        self.fx.queue(200, {"id": 5, "status": "done"})
        res = self.api.update_task("acc", 5, {"status": "done"})
        self.assertEqual(res["status"], "done")
        call = self.fx.calls[-1]
        self.assertEqual(call["method"], "PATCH")
        self.assertTrue(call["url"].endswith("/api/v1/tasks/5/"))
        self.assertEqual(call["json"], {"status": "done"})

    def test_list_tasks_paginated(self):
        self.fx.queue(200, {"count": 1, "results": []})
        res = self.api.list_tasks_paginated("acc", status=None, page=2)
        self.assertIn("count", res)
        call = self.fx.calls[-1]
        self.assertEqual(call["method"], "GET")
        self.assertEqual(call["params"], {"page": 2})

    def test_list_categories_paginated_and_create(self):
        self.fx.queue(200, {"count": 0, "results": []})
        res = self.api.list_categories_paginated("acc", page=3)
        self.assertIn("results", res)
        call = self.fx.calls[-1]
        self.assertEqual(call["method"], "GET")
        self.assertEqual(call["params"], {"page": 3})

        self.fx.queue(200, {"id": 1, "name": "C"})
        cres = self.api.create_category("acc", "C")
        self.assertEqual(cres["name"], "C")
        ccall = self.fx.calls[-1]
        self.assertEqual(ccall["method"], "POST")
        self.assertTrue(ccall["url"].endswith("/api/v1/categories/"))
        self.assertEqual(ccall["json"], {"name": "C"})


if __name__ == "__main__":
    unittest.main()
