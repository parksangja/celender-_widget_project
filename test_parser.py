import unittest
from datetime import datetime

from ai_parser_gpt import extract_title, parse


class ParserTest(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 5, 1, 12, 0)

    def test_add_event(self):
        result = parse("오늘 오후 3시 회의 추가해줘", now=self.now)

        self.assertEqual(result["action"], "add")
        self.assertEqual(result["title"], "회의")
        self.assertEqual(result["date"], "2026-05-01")
        self.assertEqual(result["time"], "15:00")
        self.assertEqual(result["duration"], 60)

    def test_add_event_with_duration(self):
        result = parse("내일 오전 10시 운동 30분 잡아줘", now=self.now)

        self.assertEqual(result["action"], "add")
        self.assertEqual(result["title"], "운동")
        self.assertEqual(result["date"], "2026-05-02")
        self.assertEqual(result["time"], "10:00")
        self.assertEqual(result["duration"], 30)

    def test_next_weekday(self):
        result = parse("다음주 월요일 오후 2시 수업 보여줘", now=self.now)

        self.assertEqual(result["action"], "list")
        self.assertEqual(result["date"], "2026-05-04")

    def test_delete_event_title(self):
        result = parse("오늘 회의 삭제해줘", now=self.now)

        self.assertEqual(result["action"], "delete")
        self.assertEqual(result["condition"]["date"], "2026-05-01")
        self.assertEqual(result["condition"]["title"], "회의")

    def test_title_does_not_leave_duration_tail(self):
        title = extract_title("내일 오후 3시 회의 2시간 추가해줘")

        self.assertEqual(title, "회의")

    def test_month_day(self):
        result = parse("5월 3일 오후 2시 회의 추가해줘", now=self.now)

        self.assertEqual(result["action"], "add")
        self.assertEqual(result["title"], "회의")
        self.assertEqual(result["date"], "2026-05-03")
        self.assertEqual(result["time"], "14:00")

    def test_year_month_day(self):
        result = parse("2027년 1월 2일 오전 9시 병원 예약해줘", now=self.now)

        self.assertEqual(result["action"], "add")
        self.assertEqual(result["title"], "병원")
        self.assertEqual(result["date"], "2027-01-02")
        self.assertEqual(result["time"], "09:00")

    def test_this_week_weekday(self):
        result = parse("이번주 금요일 오후 6시 약속 추가해줘", now=self.now)

        self.assertEqual(result["action"], "add")
        self.assertEqual(result["title"], "약속")
        self.assertEqual(result["date"], "2026-05-01")
        self.assertEqual(result["time"], "18:00")

    def test_next_month_day(self):
        result = parse("다음달 10일 오후 1시 회의 추가해줘", now=self.now)

        self.assertEqual(result["action"], "add")
        self.assertEqual(result["title"], "회의")
        self.assertEqual(result["date"], "2026-06-10")
        self.assertEqual(result["time"], "13:00")


if __name__ == "__main__":
    unittest.main()
