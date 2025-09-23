import unittest
from datetime import datetime, timedelta, timezone

from bot.utils.datetime_pars import parse_due, ADAK


class TestParseDue(unittest.TestCase):
    def test_iso_with_offset(self):
        dt = parse_due("2024-10-05T14:30:00-09:00")
        self.assertIsInstance(dt, datetime)
        # offset -9 hours
        self.assertEqual(dt.utcoffset(), timedelta(hours=-9))
        self.assertEqual(dt.year, 2024)
        self.assertEqual(dt.month, 10)
        self.assertEqual(dt.day, 5)
        self.assertEqual((dt.hour, dt.minute, dt.second), (14, 30, 0))

    def test_in_minutes(self):
        now = datetime.now(ADAK)
        dt = parse_due("in 15m")
        self.assertIsNotNone(dt)
        # within 2 minutes tolerance around expected
        expected = now + timedelta(minutes=15)
        self.assertLess(abs((dt - expected).total_seconds()), 120)

    def test_in_hours(self):
        now = datetime.now(ADAK)
        dt = parse_due("in 2h")
        self.assertIsNotNone(dt)
        expected = now + timedelta(hours=2)
        self.assertLess(abs((dt - expected).total_seconds()), 120)

    def test_today_time(self):
        now = datetime.now(ADAK)
        dt = parse_due("today 14:30")
        self.assertIsNotNone(dt)
        self.assertEqual(dt.tzinfo, ADAK)
        self.assertEqual((dt.year, dt.month, dt.day), (now.year, now.month, now.day))
        self.assertEqual((dt.hour, dt.minute, dt.second), (14, 30, 0))

    def test_tomorrow_time(self):
        now = datetime.now(ADAK) + timedelta(days=1)
        dt = parse_due("tomorrow 09:00")
        self.assertIsNotNone(dt)
        self.assertEqual(dt.tzinfo, ADAK)
        self.assertEqual((dt.year, dt.month, dt.day), (now.year, now.month, now.day))
        self.assertEqual((dt.hour, dt.minute, dt.second), (9, 0, 0))

    def test_invalid(self):
        self.assertIsNone(parse_due("yesterday 10:00"))
        self.assertIsNone(parse_due("in -5m"))
        self.assertIsNone(parse_due("2024-10-05"))


if __name__ == "__main__":
    unittest.main()
