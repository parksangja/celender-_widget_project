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

    def test_weekly_recurring_event_appears_on_next_week(self):
        added = self.engine.add_event(
            "운동",
            "2026-05-01",
            "18:00",
            60,
            recurrence="weekly",
        )

        next_week = self.engine.list_events("2026-05-08")

        self.assertEqual(added["recurrence"], "weekly")
        self.assertEqual(len(next_week), 1)
        self.assertEqual(next_week[0]["title"], "운동")
        self.assertEqual(next_week[0]["date"], "2026-05-08")

    def test_monthly_recurring_event_appears_next_month(self):
        self.engine.add_event(
            "결제일",
            "2026-05-01",
            "09:00",
            30,
            recurrence="monthly",
        )

        result = self.engine.list_events("2026-06-01")

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["title"], "결제일")
        self.assertEqual(result[0]["recurrence"], "monthly")

    def test_monthly_recurring_event_on_month_end_uses_target_month_end(self):
        self.engine.add_event(
            "월말 정산",
            "2026-01-31",
            "09:00",
            30,
            recurrence="monthly",
        )

        february = self.engine.list_events("2026-02-28")
        march = self.engine.list_events("2026-03-31")
        april = self.engine.list_events("2026-04-30")
        not_month_end = self.engine.list_events("2026-04-29")

        self.assertEqual(february[0]["title"], "월말 정산")
        self.assertEqual(february[0]["date"], "2026-02-28")
        self.assertEqual(march[0]["date"], "2026-03-31")
        self.assertEqual(april[0]["date"], "2026-04-30")
        self.assertEqual(not_month_end, [])

    def test_monthly_recurring_event_on_short_month_end_does_not_duplicate_same_day(self):
        self.engine.add_event(
            "월말 점검",
            "2026-02-28",
            "09:00",
            30,
            recurrence="monthly",
        )

        same_day = self.engine.list_events("2026-03-28")
        month_end = self.engine.list_events("2026-03-31")

        self.assertEqual(same_day, [])
        self.assertEqual(len(month_end), 1)
        self.assertEqual(month_end[0]["title"], "월말 점검")

    def test_monthly_recurring_event_not_on_month_end_keeps_same_day_only(self):
        self.engine.add_event(
            "30일 정산",
            "2026-01-30",
            "09:00",
            30,
            recurrence="monthly",
        )

        self.assertEqual(self.engine.list_events("2026-02-28"), [])
        self.assertEqual(self.engine.list_events("2026-03-30")[0]["title"], "30일 정산")

    def test_yearly_recurring_event_appears_next_year(self):
        self.engine.add_event(
            "기념일",
            "2026-05-01",
            "09:00",
            30,
            recurrence="yearly",
        )

        result = self.engine.list_events("2027-05-01")

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["title"], "기념일")
        self.assertEqual(result[0]["recurrence"], "yearly")

    def test_recurring_event_respects_end_date(self):
        self.engine.add_event(
            "운동",
            "2026-05-01",
            "18:00",
            60,
            recurrence="weekly",
            recurrence_end="2026-05-10",
        )

        self.assertEqual(len(self.engine.list_events("2026-05-08")), 1)
        self.assertEqual(self.engine.list_events("2026-05-15"), [])

    def test_skip_single_recurring_occurrence(self):
        self.engine.add_event(
            "운동",
            "2026-05-01",
            "18:00",
            60,
            recurrence="weekly",
        )

        skipped = execute(
            {
                "action": "skip_occurrence",
                "occurrence_date": "2026-05-08",
                "condition": {"date": "2026-05-08", "title": "운동"},
            },
            self.engine,
        )

        self.assertEqual(skipped["title"], "운동")
        self.assertEqual(self.engine.list_events("2026-05-08"), [])
        self.assertEqual(len(self.engine.list_events("2026-05-15")), 1)

    def test_update_single_recurring_occurrence(self):
        self.engine.add_event(
            "운동",
            "2026-05-01",
            "18:00",
            60,
            recurrence="weekly",
        )

        updated = execute(
            {
                "action": "update_occurrence",
                "occurrence_date": "2026-05-08",
                "condition": {"date": "2026-05-08", "title": "운동"},
                "updates": {"time": "19:00", "title": "저녁 운동"},
            },
            self.engine,
        )

        original = self.engine.list_events("2026-05-01")[0]
        changed = self.engine.list_events("2026-05-08")[0]
        next_week = self.engine.list_events("2026-05-15")[0]

        self.assertEqual(updated["title"], "저녁 운동")
        self.assertEqual(changed["time"], "19:00")
        self.assertEqual(changed["is_override"], True)
        self.assertEqual(original["time"], "18:00")
        self.assertEqual(next_week["title"], "운동")

    def test_skip_occurrence_ignores_empty_title_condition(self):
        self.engine.add_event(
            "운동",
            "2026-05-01",
            "18:00",
            60,
            recurrence="weekly",
        )

        skipped = execute(
            {
                "action": "skip_occurrence",
                "occurrence_date": "2026-05-08",
                "condition": {"date": "2026-05-08", "title": None},
            },
            self.engine,
        )

        self.assertEqual(skipped["title"], "운동")
        self.assertEqual(self.engine.list_events("2026-05-08"), [])

    def test_update_occurrence_ignores_empty_title_condition(self):
        self.engine.add_event(
            "운동",
            "2026-05-01",
            "18:00",
            60,
            recurrence="weekly",
        )

        updated = execute(
            {
                "action": "update_occurrence",
                "occurrence_date": "2026-05-08",
                "condition": {"date": "2026-05-08", "title": None},
                "updates": {"time": "19:00"},
            },
            self.engine,
        )

        self.assertEqual(updated["title"], "운동")
        self.assertEqual(updated["time"], "19:00")
        self.assertTrue(updated["is_override"])

    def test_update_recurrence_end_command(self):
        self.engine.add_event(
            "운동",
            "2026-05-01",
            "18:00",
            60,
            recurrence="weekly",
        )

        updated = execute(
            {
                "action": "update_recurrence_end",
                "condition": {"title": "운동"},
                "recurrence_end": "2026-05-10",
            },
            self.engine,
        )

        self.assertEqual(updated["recurrence_end"], "2026-05-10")
        self.assertEqual(len(self.engine.list_events("2026-05-08")), 1)
        self.assertEqual(self.engine.list_events("2026-05-15"), [])

    def test_update_recurring_event_keeps_recurrence_end(self):
        added = self.engine.add_event(
            "운동",
            "2026-05-01",
            "18:00",
            60,
            recurrence="weekly",
            recurrence_end="2026-05-10",
        )

        updated = self.engine.update_event(added["id"], title="저녁 운동")

        self.assertEqual(updated["title"], "저녁 운동")
        self.assertEqual(updated["recurrence"], "weekly")
        self.assertEqual(updated["recurrence_end"], "2026-05-10")

    def test_parse_recurring_event_to_execute_flow(self):
        command = parse("매주 금요일 오후 6시 운동 추가해줘", now=self.now)
        added = execute(command, self.engine)

        result = self.engine.list_events("2026-05-08")

        self.assertEqual(added["recurrence"], "weekly")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["title"], "운동")

    def test_delete_requires_condition(self):
        with self.assertRaises(ValueError):
            execute({"action": "delete", "condition": {}}, self.engine)

    def test_delete_rejects_empty_condition_values(self):
        self.engine.add_event("회의", "2026-05-01", "15:00", 60)

        with self.assertRaises(ValueError):
            execute({"action": "delete", "condition": {"title": None}}, self.engine)

        self.assertEqual(len(self.engine.list_events("2026-05-01")), 1)

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
