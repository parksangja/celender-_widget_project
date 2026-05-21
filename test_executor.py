import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from ai_parser_gpt import parse
from calendar_engine import CalendarEngine
from executor import execute


class ExecutorTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.storage_path = Path(self.temp_dir.name) / "events.json"
        self.engine = CalendarEngine(str(self.storage_path))
        self.now = datetime(2026, 5, 1, 12, 0)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_execute_add(self):
        result = execute(
            {
                "action": "add",
                "title": "회의",
                "date": "2026-05-01",
                "time": "15:00",
                "duration": 60,
                "tag": None,
                "priority": None,
            },
            self.engine,
        )

        self.assertEqual(result["title"], "회의")
        self.assertEqual(result["date"], "2026-05-01")
        self.assertEqual(self.engine.list_events("2026-05-01"), [result])

    def test_execute_list(self):
        execute(
            {
                "action": "add",
                "title": "회의",
                "date": "2026-05-01",
                "time": "15:00",
                "duration": 60,
            },
            self.engine,
        )
        execute(
            {
                "action": "add",
                "title": "운동",
                "date": "2026-05-02",
                "time": "18:00",
                "duration": 60,
            },
            self.engine,
        )

        result = execute({"action": "list", "date": "2026-05-01"}, self.engine)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["title"], "회의")

    def test_execute_delete(self):
        execute(
            {
                "action": "add",
                "title": "회의",
                "date": "2026-05-01",
                "time": "15:00",
                "duration": 60,
            },
            self.engine,
        )
        execute(
            {
                "action": "add",
                "title": "운동",
                "date": "2026-05-01",
                "time": "18:00",
                "duration": 60,
            },
            self.engine,
        )

        deleted = execute(
            {
                "action": "delete",
                "condition": {
                    "date": "2026-05-01",
                    "title": "회의",
                },
            },
            self.engine,
        )

        remaining = self.engine.list_events("2026-05-01")
        self.assertEqual(len(deleted), 1)
        self.assertEqual(deleted[0]["title"], "회의")
        self.assertEqual(len(remaining), 1)
        self.assertEqual(remaining[0]["title"], "운동")

    def test_update_timed_event_keeps_id_and_color(self):
        added = self.engine.add_event(
            "회의",
            "2026-05-01",
            "15:00",
            60,
            color="#2DBE78",
        )

        updated = self.engine.update_event(
            added["id"],
            title="팀 회의",
            date="2026-05-01",
            time="16:00",
            duration=30,
            color="#F59F00",
        )

        self.assertEqual(updated["id"], added["id"])
        self.assertEqual(updated["title"], "팀 회의")
        self.assertEqual(updated["time"], "16:00")
        self.assertEqual(updated["duration"], 30)
        self.assertEqual(updated["color"], "#F59F00")

    def test_update_period_event(self):
        added = self.engine.add_period_event(
            "시험기간",
            "2026-05-01",
            color="#9C36B5",
        )

        updated = self.engine.update_event(
            added["id"],
            title="중간고사 기간",
            start_date="2026-05-02",
            end_date="2026-05-10",
            color="#15AABF",
        )

        self.assertEqual(updated["id"], added["id"])
        self.assertEqual(updated["type"], "period")
        self.assertEqual(updated["title"], "중간고사 기간")
        self.assertEqual(updated["start_date"], "2026-05-02")
        self.assertEqual(updated["end_date"], "2026-05-10")
        self.assertEqual(updated["color"], "#15AABF")

    def test_delete_requires_condition(self):
        with self.assertRaises(ValueError):
            execute({"action": "delete", "condition": {}}, self.engine)

    def test_unknown_action(self):
        with self.assertRaises(ValueError):
            execute({"action": "unknown"}, self.engine)

    def test_parse_to_execute_flow(self):
        add_command = parse("오늘 오후 3시 회의 추가해줘", now=self.now)
        added = execute(add_command, self.engine)

        list_command = parse("오늘 일정 보여줘", now=self.now)
        listed = execute(list_command, self.engine)

        delete_command = parse("오늘 회의 삭제해줘", now=self.now)
        deleted = execute(delete_command, self.engine)

        self.assertEqual(added["title"], "회의")
        self.assertEqual(len(listed), 1)
        self.assertEqual(listed[0]["title"], "회의")
        self.assertEqual(len(deleted), 1)
        self.assertEqual(self.engine.list_events("2026-05-01"), [])


if __name__ == "__main__":
    unittest.main()
