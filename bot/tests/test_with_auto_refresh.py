import sys
import types
import unittest
from unittest.mock import AsyncMock, Mock

# stub minimal httpx with HTTPStatusError and Response-like object
httpx_mod = types.ModuleType("httpx")

class HTTPStatusError(Exception):
    def __init__(self, *args, request=None, response=None):
        super().__init__(*args)
        self.request = request
        self.response = response


httpx_mod.HTTPStatusError = HTTPStatusError
sys.modules.setdefault("httpx", httpx_mod)

import bot.service.django_api as api_mod
from bot.service.django_api import with_auto_refresh


class TestWithAutoRefresh(unittest.IsolatedAsyncioTestCase):
    async def test_success_without_refresh(self):
        store = AsyncMock()
        store.get_auth.return_value = (1, "access123", "refresh123")

        call = Mock(return_value={"ok": True})
        refresh_fn = Mock()

        result = await with_auto_refresh(42, store, call, refresh_fn)
        self.assertEqual(result, {"ok": True})
        call.assert_called_once_with("access123")
        refresh_fn.assert_not_called()

    async def test_refresh_on_401(self):
        store = AsyncMock()
        store.get_auth.return_value = (1, "old_access", "refreshX")

        # First call raises 401, second call returns ok
        call = Mock()
        resp401 = Mock()
        resp401.status_code = 401
        E = api_mod.httpx.HTTPStatusError
        call.side_effect = [E("Unauthorized", request=Mock(), response=resp401), {"ok": True}]

        refresh_fn = Mock(return_value={"access": "new_access"})

        result = await with_auto_refresh(99, store, call, refresh_fn)
        self.assertEqual(result, {"ok": True})
        self.assertEqual(call.call_count, 2)
        call.assert_any_call("old_access")
        call.assert_any_call("new_access")
        refresh_fn.assert_called_once_with("refreshX")
        store.update_access.assert_awaited_once_with(99, "new_access")

    async def test_non_401_error_bubbles(self):
        store = AsyncMock()
        store.get_auth.return_value = (1, "acc", "ref")

        call = Mock()
        resp500 = Mock()
        resp500.status_code = 500
        E = api_mod.httpx.HTTPStatusError
        call.side_effect = E("Server error", request=Mock(), response=resp500)

        with self.assertRaises(api_mod.httpx.HTTPStatusError):
            await with_auto_refresh(1, store, call, Mock())

    async def test_refresh_failed_no_access(self):
        store = AsyncMock()
        store.get_auth.return_value = (1, "acc", "refreshZ")

        resp401 = Mock(); resp401.status_code = 401
        E = api_mod.httpx.HTTPStatusError
        call = Mock(side_effect=[E("Unauthorized", request=Mock(), response=resp401)])

        refresh_fn = Mock(return_value={})

        with self.assertRaisesRegex(RuntimeError, "refresh failed"):
            await with_auto_refresh(7, store, call, refresh_fn)

    async def test_not_authenticated(self):
        store = AsyncMock()
        store.get_auth.return_value = None

        with self.assertRaisesRegex(RuntimeError, "not authenticated"):
            await with_auto_refresh(7, store, Mock(), Mock())


if __name__ == "__main__":
    unittest.main()
