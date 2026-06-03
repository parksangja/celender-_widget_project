import json
import tempfile
import unittest
from pathlib import Path

from calendar_engine import CalendarEngine
from data_safety import backup_path, save_json_safely
from holiday_updater import load_holiday_cache


class DataSafetyTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_safe_json_save_creates_backup(self):
        path = self.temp_path / "sample.json"
        path.write_text('{"old": true}\n', encoding="utf-8")

        save_json_safely(path, {"new": True})

        self.assertEqual(json.loads(path.read_text(encoding="utf-8")), {"new": True})
        self.assertEqual(
            json.loads(Path(backup_path(path)).read_text(encoding="utf-8")),
            {"old": True},
        )

    def test_calendar_engine_recovers_events_from_backup(self):
        path = self.temp_path / "events.json"
        path.write_text("{ broken json", encoding="utf-8")
        Path(backup_path(path)).write_text(
            json.dumps(
                [
                    {
                        "id": 1,
                        "type": "timed",
                        "title": "회의",
                        "date": "2026-05-30",
                        "time": "15:00",
                        "duration": 60,
                    }
                ],
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        engine = CalendarEngine(str(path))

        self.assertEqual(engine.list_events("2026-05-30")[0]["title"], "회의")
        self.assertEqual(json.loads(path.read_text(encoding="utf-8"))[0]["title"], "회의")
        self.assertTrue(list(self.temp_path.glob("events.json.corrupt-*")))

    def test_calendar_engine_ignores_malformed_event_record(self):
        path = self.temp_path / "events.json"
        path.write_text(
            json.dumps(
                [
                    {"id": 1, "title": "날짜 없음"},
                    {
                        "id": 2,
                        "type": "timed",
                        "title": "운동",
                        "date": "2026-05-30",
                        "time": "18:00",
                        "duration": 60,
                    },
                ],
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        engine = CalendarEngine(str(path))

        self.assertEqual(len(engine.list_events("2026-05-30")), 1)
        self.assertEqual(engine.list_events("2026-05-30")[0]["title"], "운동")

    def test_holiday_cache_recovers_from_backup(self):
        path = self.temp_path / "holiday_cache.json"
        path.write_text("{ broken json", encoding="utf-8")
        Path(backup_path(path)).write_text(
            json.dumps(
                {
                    "updated_at": "2026-05-30T09:00:00",
                    "years": {"2026": {"2026-06-03": ["지방선거"]}},
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        cache = load_holiday_cache(str(path))

        self.assertEqual(cache["years"]["2026"]["2026-06-03"], ["지방선거"])
        self.assertEqual(json.loads(path.read_text(encoding="utf-8"))["years"]["2026"]["2026-06-03"], ["지방선거"])
        self.assertTrue(list(self.temp_path.glob("holiday_cache.json.corrupt-*")))


if __name__ == "__main__":
    unittest.main()
