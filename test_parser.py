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

    def test_week_after_next_weekday(self):
        now = datetime(2026, 6, 5, 12, 0)
        result = parse("다다음주 월요일 오후 2시 수업 추가해줘", now=now)

        self.assertEqual(result["action"], "add")
        self.assertEqual(result["title"], "수업")
        self.assertEqual(result["date"], "2026-06-15")
        self.assertEqual(result["time"], "14:00")

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

    def test_half_hour_time(self):
        result = parse("오늘 오후 3시 반 회의 추가해줘", now=self.now)

        self.assertEqual(result["action"], "add")
        self.assertEqual(result["title"], "회의")
        self.assertEqual(result["time"], "15:30")
        self.assertEqual(result["duration"], 60)

    def test_korean_hour_word(self):
        result = parse("오늘 오후 세 시 회의 추가해줘", now=self.now)

        self.assertEqual(result["action"], "add")
        self.assertEqual(result["title"], "회의")
        self.assertEqual(result["time"], "15:00")

    def test_evening_time(self):
        result = parse("오늘 저녁 7시 운동 추가해줘", now=self.now)

        self.assertEqual(result["action"], "add")
        self.assertEqual(result["title"], "운동")
        self.assertEqual(result["time"], "19:00")

    def test_hour_and_half_duration(self):
        result = parse("오늘 오후 2시 회의 1시간 반 추가해줘", now=self.now)

        self.assertEqual(result["action"], "add")
        self.assertEqual(result["title"], "회의")
        self.assertEqual(result["time"], "14:00")
        self.assertEqual(result["duration"], 90)

    def test_minute_duration_with_while(self):
        result = parse("오늘 오후 2시 회의 90분 동안 추가해줘", now=self.now)

        self.assertEqual(result["action"], "add")
        self.assertEqual(result["title"], "회의")
        self.assertEqual(result["time"], "14:00")
        self.assertEqual(result["duration"], 90)

    def test_time_minute_is_not_duration(self):
        result = parse("오늘 오후 3시 30분 회의 추가해줘", now=self.now)

        self.assertEqual(result["action"], "add")
        self.assertEqual(result["title"], "회의")
        self.assertEqual(result["time"], "15:30")
        self.assertEqual(result["duration"], 60)

    def test_weekly_recurrence(self):
        result = parse("매주 금요일 오후 6시 운동 추가해줘", now=self.now)

        self.assertEqual(result["action"], "add")
        self.assertEqual(result["title"], "운동")
        self.assertEqual(result["date"], "2026-05-01")
        self.assertEqual(result["time"], "18:00")
        self.assertEqual(result["recurrence"], "weekly")

    def test_monthly_recurrence(self):
        result = parse("매달 1일 오전 9시 결제일 추가해줘", now=self.now)

        self.assertEqual(result["action"], "add")
        self.assertEqual(result["title"], "결제일")
        self.assertEqual(result["date"], "2026-05-01")
        self.assertEqual(result["recurrence"], "monthly")

    def test_yearly_recurrence(self):
        result = parse("매년 5월 1일 오전 9시 기념일 추가해줘", now=self.now)

        self.assertEqual(result["action"], "add")
        self.assertEqual(result["title"], "기념일")
        self.assertEqual(result["date"], "2026-05-01")
        self.assertEqual(result["recurrence"], "yearly")

    def test_skip_recurring_occurrence(self):
        result = parse("5월 8일 운동 건너뛰어줘", now=self.now)

        self.assertEqual(result["action"], "skip_occurrence")
        self.assertEqual(result["occurrence_date"], "2026-05-08")
        self.assertEqual(result["condition"]["title"], "운동")

    def test_update_single_occurrence_time(self):
        result = parse("5월 8일 운동 오후 7시로 수정해줘", now=self.now)

        self.assertEqual(result["action"], "update_occurrence")
        self.assertEqual(result["occurrence_date"], "2026-05-08")
        self.assertEqual(result["condition"]["title"], "운동")
        self.assertEqual(result["updates"]["time"], "19:00")

    def test_update_recurrence_end(self):
        result = parse("운동 반복 종료일 5월 15일로 수정해줘", now=self.now)

        self.assertEqual(result["action"], "update_recurrence_end")
        self.assertEqual(result["condition"]["title"], "운동")
        self.assertEqual(result["recurrence_end"], "2026-05-15")


if __name__ == "__main__":
    unittest.main()
