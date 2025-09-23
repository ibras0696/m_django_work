# bot/datetime_parse.py
from __future__ import annotations
import re
from datetime import datetime, timedelta, timezone

# В Adak -09:00 круглый год (упрощаем; в проде лучше pytz/zoneinfo)
ADAK = timezone(timedelta(hours=-9))

iso_re = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2})?([+-]\d{2}:\d{2})$"
)


def parse_due(text: str) -> datetime | None:
    """
    Парсит дату/время из строки.
    Поддерживаются форматы:
    1) ISO 8601 с часовым поясом, например: "2023-10-05T14:30:00-09:00"
    2) Относительные времена: "in 15m", "in 2h"
    3) Сегодня в HH:MM, например: "today 14:30"
    4) Завтра в HH:MM, например: "tomorrow 09:00"
    :param text: строка с датой/временем
    :return: datetime в часовом поясе Adak или None, если не удалось распарсить
    """
    raw = text.strip()
    # 1) ISO with offset (сохраняем регистр, т.к. ISO требует 'T')
    if iso_re.match(raw):
        try:
            return datetime.fromisoformat(raw)
        except Exception:
            return None

    # для остальных паттернов можно безопасно привести к нижнему регистру
    t = raw.lower()

    # 2) relative: in Xm / in Xh
    m = re.match(r"in\s+(\d+)\s*(m|min|minute|minutes)$", t)
    if m:
        delta = timedelta(minutes=int(m.group(1)))
        return datetime.now(ADAK) + delta
    m = re.match(r"in\s+(\d+)\s*(h|hour|hours)$", t)
    if m:
        delta = timedelta(hours=int(m.group(1)))
        return datetime.now(ADAK) + delta

    # 3) today HH:MM
    m = re.match(r"today\s+(\d{1,2}):(\d{2})$", t)
    if m:
        hh, mm = int(m.group(1)), int(m.group(2))
        now = datetime.now(ADAK)
        return now.replace(hour=hh, minute=mm, second=0, microsecond=0)

    # 4) tomorrow HH:MM
    m = re.match(r"tomorrow\s+(\d{1,2}):(\d{2})$", t)
    if m:
        hh, mm = int(m.group(1)), int(m.group(2))
        now = datetime.now(ADAK) + timedelta(days=1)
        return now.replace(hour=hh, minute=mm, second=0, microsecond=0)

    return None
