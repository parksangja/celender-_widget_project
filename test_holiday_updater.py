import json
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

import holiday_updater
from holiday_updater import (
    load_cached_public_holidays,
    parse_public_holiday_response,
    save_holiday_cache,
    update_holiday_cache,
)
from korean_calendar_utils import get_korean_holidays


class HolidayUpdaterTest(unittest.TestCase):
    def test_parse_public_holiday_json_response(self):
        payload = {
            "response": {
                "header": {"resultCode": "00", "resultMsg": "NORMAL SERVICE."},
                "body": {
                    "items": {
                        "item": [
                            {
                                "dateName": "임시공휴일",
                                "locdate": 20261005,
                                "isHoliday": "Y",
                            },
                            {
                                "dateName": "기념일",
                                "locdate": 20261006,
                                "isHoliday": "N",
                            },
                        ]
                    }
                },
            }
        }

        result = parse_public_holiday_response(json.dumps(payload, ensure_ascii=False))

        self.assertEqual(result, {"2026-10-05": ["임시공휴일"]})

    def test_update_cache_fetches_when_cache_is_old(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_path = Path(temp_dir) / "holiday_cache.json"
            now = datetime(2026, 5, 18, 12, 0)
            save_holiday_cache(
                {
                    "updated_at": (now - timedelta(days=3)).isoformat(timespec="seconds"),
                    "years": {},
                },
                str(cache_path),
            )

            result = update_holiday_cache(
                [2026],
                service_key="dummy",
                now=now,
                cache_path=str(cache_path),
                fetcher=lambda year: {"2026-10-05": ["임시공휴일"]},
            )

            self.assertTrue(result.updated)
            self.assertEqual(result.years, [2026])
            self.assertEqual(
                load_cached_public_holidays(2026, str(cache_path)),
                {"2026-10-05": ["임시공휴일"]},
            )

    def test_update_cache_skips_when_cache_is_fresh(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_path = Path(temp_dir) / "holiday_cache.json"
            now = datetime(2026, 5, 18, 12, 0)
            save_holiday_cache(
                {
                    "updated_at": now.isoformat(timespec="seconds"),
                    "years": {"2026": {"2026-10-05": ["임시공휴일"]}},
                },
                str(cache_path),
            )
            calls = []

            result = update_holiday_cache(
                [2026],
                service_key="dummy",
                now=now,
                cache_path=str(cache_path),
                fetcher=lambda year: calls.append(year),
            )

            self.assertFalse(result.updated)
            self.assertEqual(result.reason, "fresh_cache")
            self.assertEqual(calls, [])

    def test_cached_public_holidays_are_merged_into_calendar_holidays(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_path = Path(temp_dir) / "holiday_cache.json"
            save_holiday_cache(
                {
                    "updated_at": "2026-05-18T12:00:00",
                    "years": {"2026": {"2026-10-05": ["임시공휴일"]}},
                },
                str(cache_path),
            )

            old_cache_path = holiday_updater.HOLIDAY_CACHE_PATH
            holiday_updater.HOLIDAY_CACHE_PATH = str(cache_path)
            try:
                holidays = get_korean_holidays(2026)
            finally:
                holiday_updater.HOLIDAY_CACHE_PATH = old_cache_path

            self.assertIn("임시공휴일", holidays["2026-10-05"])


if __name__ == "__main__":
    unittest.main()
