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

def parse_korean_datetime(text: str): #날짜, 요알, 시간 처리용 함수
    now = datetime.now()

    date = now.date()

    if "오늘" in text:
        date = now.date()

    elif "내일" in text:
        date = now.date() + timedelta(days=1)

    elif "모레" in text:
        date = now.date() + timedelta(days=2)

    elif "글피" in text:
        date = now.date() + timedelta(days=3)

    elif "다음주" in text:
        date += timedelta(days=7)

    for k, v in WEEKDAY_MAP.items():
        if k in text:
            current_weekday = date.weekday()
            delta = (v - current_weekday) % 7

            # "다음주 월요일"이면 +7 보정
            if "다음주" in text:
                delta += 7 if delta == 0 else 0

            date = date + timedelta(days=delta)

    hour = 9  # 기본값
    minute = 0

    # "오전/오후"
    am_pm = None
    if "오전" in text:
        am_pm = "AM"
    elif "오후" in text:
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