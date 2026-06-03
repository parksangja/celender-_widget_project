import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path

from PyQt6.QtCore import QDate

from ai_parser_gpt import parse
from calendar_engine import CalendarEngine
from executor import execute
from holiday_updater import get_korean_holidays, save_holiday_cache
from korean_datetime_parser import lunar_to_solar
from ui_support import (
    is_ai_confirmation_acceptance,
    is_ai_confirmation_rejection,
    qdate_to_storage_date,
)


class CalendarFeatureTest(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 5, 1, 12, 0)
        self.temp_dir = tempfile.TemporaryDirectory()
        self.storage_path = Path(self.temp_dir.name) / "events.json"
        self.engine = CalendarEngine(str(self.storage_path))

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_lunar_to_solar(self):
        self.assertEqual(lunar_to_solar(2026, 1, 1), date(2026, 2, 17))

    def test_parse_lunar_date(self):
        result = parse("2026년 음력 1월 1일 오후 3시 세배 추가해줘", now=self.now)

        self.assertEqual(result["action"], "add")
        self.assertEqual(result["title"], "세배")
        self.assertEqual(result["date"], "2026-02-17")
        self.assertEqual(result["time"], "15:00")

    def test_qdate_lunar_input_converts_to_solar_storage_date(self):
        self.assertEqual(
            qdate_to_storage_date(QDate(2026, 1, 1), use_lunar=True),
            "2026-02-17",
        )

    def test_ai_confirmation_reply_words(self):
        self.assertTrue(is_ai_confirmation_acceptance("실행"))
        self.assertTrue(is_ai_confirmation_acceptance("  OK  "))
        self.assertTrue(is_ai_confirmation_rejection("취소"))
        self.assertTrue(is_ai_confirmation_rejection("아니요"))
        self.assertFalse(is_ai_confirmation_acceptance("회의 추가해줘"))
        self.assertFalse(is_ai_confirmation_rejection("회의 추가해줘"))

    def test_korean_holidays(self):
        cache_path = Path(self.temp_dir.name) / "holiday_cache.json"
        save_holiday_cache(
            {
                "updated_at": "2026-05-19T21:30:00",
                "years": {
                    "2026": {
                        "2026-02-17": ["설날"],
                        "2026-05-24": ["부처님오신날"],
                        "2026-05-25": ["부처님오신날 대체공휴일"],
                        "2026-06-03": ["제9회 전국동시지방선거일"],
                    }
                },
            },
            str(cache_path),
        )

        holidays = get_korean_holidays(2026, cache_path=str(cache_path))

        self.assertIn("설날", holidays["2026-02-17"])
        self.assertIn("부처님오신날", holidays["2026-05-24"])
        self.assertIn("부처님오신날 대체공휴일", holidays["2026-05-25"])
        self.assertIn("제9회 전국동시지방선거일", holidays["2026-06-03"])

    def test_parse_indefinite_period(self):
        result = parse("오늘부터 무기한 시험기간 추가해줘", now=self.now)

        self.assertEqual(result["action"], "add_period")
        self.assertEqual(result["title"], "시험기간")
        self.assertEqual(result["start_date"], "2026-05-01")
        self.assertIsNone(result["end_date"])

    def test_period_event_is_active_after_start_date(self):
        command = parse("오늘부터 무기한 시험기간 추가해줘", now=self.now)
        added = execute(command, self.engine)

        before = self.engine.list_events("2026-04-30")
        on_start = self.engine.list_events("2026-05-01")
        later = self.engine.list_events("2026-05-15")

        self.assertEqual(added["type"], "period")
        self.assertEqual(before, [])
        self.assertEqual(on_start[0]["title"], "시험기간")
        self.assertEqual(later[0]["title"], "시험기간")


if __name__ == "__main__":
    unittest.main()
