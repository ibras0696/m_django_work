import sys
import types
import unittest
from datetime import datetime, timezone, timedelta

# Inject a minimal aiogram.types stub so importing bot.utils.ui doesn't require aiogram installed
aiogram_mod = types.ModuleType("aiogram")
aiogram_types_mod = types.ModuleType("aiogram.types")

class InlineKeyboardMarkup:  # minimal stub for import side-effects
    def __init__(self, *args, **kwargs):
        # store for inspection if needed
        self.kwargs = kwargs


class InlineKeyboardButton:
    def __init__(self, *args, **kwargs):
        pass


aiogram_types_mod.InlineKeyboardMarkup = InlineKeyboardMarkup
aiogram_types_mod.InlineKeyboardButton = InlineKeyboardButton
aiogram_mod.types = aiogram_types_mod
sys.modules.setdefault("aiogram", aiogram_mod)
sys.modules.setdefault("aiogram.types", aiogram_types_mod)

from bot.utils.ui import escape_md, fmt_task_line, fmt_task_preview, kb_task_actions, kb_categories_page


class TestUIFormatting(unittest.TestCase):
    def test_escape_md(self):
        s = "_[*`"
        self.assertEqual(escape_md(s), "\\_\\[\\*\\`")

    def test_fmt_task_line(self):
        task = {
            "id": 123,
            "title": "Title _ [*`",
            "status": "todo",
            "categories": [{"id": 1, "name": "Cat_1"}],
            "created_at": "2025-09-23T12:00:00Z",
            "due_at": "2025-09-24T12:00:00Z",
        }
        text = fmt_task_line(task)
        # Contains escaped title and basic fields
        self.assertIn("[123]", text)
        self.assertIn("*Title \\_ \\[\\*\\`*", text)
        self.assertIn("Категории: Cat\\_1", text)
        self.assertIn("Создано: 2025-09-23T12:00:00Z", text)
        self.assertIn("Дедлайн: 2025-09-24T12:00:00Z", text)

    def test_fmt_task_preview_with_due(self):
        due = datetime.now(timezone.utc) + timedelta(hours=1)
        text = fmt_task_preview("Do _ this", due)
        self.assertIn("Новая задача", text)
        self.assertIn("*Do \\_ this*", text)
        self.assertIn("Дедлайн:", text)
        self.assertIn("осталось", text)

    def test_fmt_task_preview_without_due(self):
        text = fmt_task_preview("No due", None)
        self.assertIn("Дедлайн: *—*", text)

    def test_kb_task_actions(self):
        kb = kb_task_actions(42, has_due=True)
        # our stubbed InlineKeyboardMarkup doesn't have structure, but import should succeed
        self.assertIsNotNone(kb)

    def test_kb_categories_page(self):
        cats = [{"id": 1, "name": "A"}, {"id": 2, "name": "B"}]
        kb = kb_categories_page(cats, page=2, has_prev=True, has_next=True, selected={2})
        self.assertIsNotNone(kb)


if __name__ == "__main__":
    unittest.main()
