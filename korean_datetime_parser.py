import re
from datetime import datetime, timedelta

WEEKDAY_MAP = {
    "월요일": 0,
    "화요일": 1,
    "수요일": 2,
    "목요일": 3,
    "금요일": 4,
    "토요일": 5,
    "일요일": 6,
}


def _date_or_none(year, month, day):
    try:
        return datetime(year=year, month=month, day=day).date()
    except ValueError:
        return None


def _add_months(year, month, amount):
    total_month = (year * 12) + (month - 1) + amount
    return total_month // 12, (total_month % 12) + 1


def _find_weekday(text):
    for k, v in WEEKDAY_MAP.items():
        if k in text:
            return v
    return None


def _next_weekday_from(base_date, weekday):
    delta = (weekday - base_date.weekday()) % 7
    return base_date + timedelta(days=delta)


def _weekday_in_this_week(base_date, weekday):
    start_of_this_week = base_date - timedelta(days=base_date.weekday())
    return start_of_this_week + timedelta(days=weekday)


def _weekday_in_next_week(base_date, weekday):
    start_of_this_week = base_date - timedelta(days=base_date.weekday())
    start_of_next_week = start_of_this_week + timedelta(days=7)
    return start_of_next_week + timedelta(days=weekday)


def _parse_written_date(text, now):
    match = re.search(r"(\d{4})\s*년\s*(\d{1,2})\s*월\s*(\d{1,2})\s*일", text)
    if match:
        year, month, day = map(int, match.groups())
        return _date_or_none(year, month, day)

    match = re.search(r"(\d{1,2})\s*월\s*(\d{1,2})\s*일", text)
    if match:
        month, day = map(int, match.groups())
        return _date_or_none(now.year, month, day)

    match = re.search(r"(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})", text)
    if match:
        year, month, day = map(int, match.groups())
        return _date_or_none(year, month, day)

    match = re.search(r"(?<!\d)(\d{1,2})[/.](\d{1,2})(?!\d)", text)
    if match:
        month, day = map(int, match.groups())
        return _date_or_none(now.year, month, day)

    match = re.search(r"(?:다음\s*달|다음달)\s*(\d{1,2})\s*일", text)
    if match:
        year, month = _add_months(now.year, now.month, 1)
        return _date_or_none(year, month, int(match.group(1)))

    match = re.search(r"(?:이번\s*달|이번달)\s*(\d{1,2})\s*일", text)
    if match:
        return _date_or_none(now.year, now.month, int(match.group(1)))

    match = re.search(r"(?<!\d)(\d{1,2})\s*일(?!차)", text)
    if match:
        return _date_or_none(now.year, now.month, int(match.group(1)))

    return None


def has_date_expression(text):
    if any(k in text for k in ["오늘", "내일", "모레", "글피", "이번주", "다음주", "이번달", "이번 달", "다음달", "다음 달"]):
        return True
    if _find_weekday(text) is not None:
        return True

    date_patterns = [
        r"\d{4}\s*년\s*\d{1,2}\s*월\s*\d{1,2}\s*일",
        r"\d{1,2}\s*월\s*\d{1,2}\s*일",
        r"\d{4}[-/.]\d{1,2}[-/.]\d{1,2}",
        r"(?<!\d)\d{1,2}[/.]\d{1,2}(?!\d)",
        r"(?<!\d)\d{1,2}\s*일(?!차)",
    ]
    return any(re.search(pattern, text) for pattern in date_patterns)


def parse_korean_datetime(text: str, now=None): #날짜, 요일, 시간 처리용 함수
    now = now or datetime.now()
    date = now.date()
    written_date = _parse_written_date(text, now)
    weekday = _find_weekday(text)

    if written_date is not None:
        date = written_date

    elif "다음주" in text and weekday is not None:
        date = _weekday_in_next_week(date, weekday)

    elif "이번주" in text and weekday is not None:
        date = _weekday_in_this_week(date, weekday)

    elif "오늘" in text:
        date = now.date()

    elif "내일" in text:
        date = now.date() + timedelta(days=1)

    elif "모레" in text:
        date = now.date() + timedelta(days=2)

    elif "글피" in text:
        date = now.date() + timedelta(days=3)

    elif "다음주" in text:
        date += timedelta(days=7)

    elif weekday is not None:
        date = _next_weekday_from(date, weekday)

    hour = 9  # 기본값
    minute = 0

    # "오전/오후"
    am_pm = None
    if "오전" in text or "아침" in text:
        am_pm = "AM"
    elif "오후" in text or "점심" in text or "저녁" in text:
        am_pm = "PM"

    # "3시", "3시 30분"
    time_match = re.search(r'(\d{1,2})시(?:\s*(\d{1,2})분)?', text)

    if time_match:
        hour = int(time_match.group(1))
        if time_match.group(2):
            minute = int(time_match.group(2))

    # 오전/오후 보정
    if am_pm == "PM" and hour < 12:
        hour += 12
    if am_pm == "AM" and hour == 12:
        hour = 0

    result = datetime(
        year=date.year,
        month=date.month,
        day=date.day,
        hour=hour,
        minute=minute
    )

    return result
