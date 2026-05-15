##한국어 명렁을 처리하기 위한 파일
#
import re
from datetime import datetime, timedelta

from korean_calendar_utils import lunar_to_solar

#"몇요일"을 컴퓨터가 알기 쉽게 변환
WEEKDAY_MAP = {
    "월요일": 0,
    "화요일": 1,
    "수요일": 2,
    "목요일": 3,
    "금요일": 4,
    "토요일": 5,
    "일요일": 6,
}

#위와 마친가지로 한국어로 표현된 숫자들을 정수로 변환
KOREAN_NUMBER_MAP = {
    "영": 0,
    "공": 0,
    "한": 1,
    "하나": 1,
    "일": 1,
    "두": 2,
    "둘": 2,
    "이": 2,
    "세": 3,
    "셋": 3,
    "삼": 3,
    "네": 4,
    "넷": 4,
    "사": 4,
    "다섯": 5,
    "오": 5,
    "여섯": 6,
    "육": 6,
    "일곱": 7,
    "칠": 7,
    "여덟": 8,
    "팔": 8,
    "아홉": 9,
    "구": 9,
    "열": 10,
    "열한": 11,
    "열하나": 11,
    "열두": 12,
    "열둘": 12,
}

#정규식에 따라 패턴을 정해주는 듯?(자세한거는 더 공부하기)
KOREAN_NUMBER_WORD_PATTERN = "|".join(sorted(KOREAN_NUMBER_MAP, key=len, reverse=True))
TIME_PATTERN = rf"(?<![가-힣0-9])(\d{{1,2}}|{KOREAN_NUMBER_WORD_PATTERN})\s*시(?!간)(?:\s*(?:(\d{{1,2}}|{KOREAN_NUMBER_WORD_PATTERN})\s*분|반))?"


def parse_korean_number(value):
    value = value.strip()       #가져온 인수의 공백 제거
    if value.isdigit():         #숫자면 그냥 int씌워서 반환
        return int(value)

    if value in KOREAN_NUMBER_MAP:       #위 딕셔너리에 있는 글자면 그에 맞게 반환
        return KOREAN_NUMBER_MAP[value]

    if "십" in value:
        tens_text, ones_text = value.split("십", 1)
        tens = 1 if tens_text == "" else KOREAN_NUMBER_MAP.get(tens_text)
        ones = 0 if ones_text == "" else KOREAN_NUMBER_MAP.get(ones_text)

        if tens is not None and ones is not None:
            return tens * 10 + ones

    return None


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
    lunar_match = re.search(r"(\d{4})\s*년\s*음력\s*(윤)?\s*(\d{1,2})\s*월\s*(\d{1,2})\s*일", text)
    if lunar_match:
        year = int(lunar_match.group(1))
        leap_month = lunar_match.group(2) is not None
        month = int(lunar_match.group(3))
        day = int(lunar_match.group(4))
        return lunar_to_solar(year, month, day, leap_month)

    lunar_match = re.search(r"음력\s*(\d{4})\s*년\s*(윤)?\s*(\d{1,2})\s*월\s*(\d{1,2})\s*일", text)
    if lunar_match:
        year = int(lunar_match.group(1))
        leap_month = lunar_match.group(2) is not None
        month = int(lunar_match.group(3))
        day = int(lunar_match.group(4))
        return lunar_to_solar(year, month, day, leap_month)

    lunar_match = re.search(r"음력\s*(윤)?\s*(\d{1,2})\s*월\s*(\d{1,2})\s*일", text)
    if lunar_match:
        leap_month = lunar_match.group(1) is not None
        month = int(lunar_match.group(2))
        day = int(lunar_match.group(3))
        return lunar_to_solar(now.year, month, day, leap_month)

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
    if any(k in text for k in ["오늘", "내일", "모레", "글피", "이번주", "다음주", "이번달", "이번 달", "다음달", "다음 달", "음력"]):
        return True
    if _find_weekday(text) is not None:
        return True

    date_patterns = [
        r"\d{4}\s*년\s*\d{1,2}\s*월\s*\d{1,2}\s*일",
        r"\d{1,2}\s*월\s*\d{1,2}\s*일",
        r"\d{4}[-/.]\d{1,2}[-/.]\d{1,2}",
        r"(?<!\d)\d{1,2}[/.]\d{1,2}(?!\d)",
        r"(?<!\d)\d{1,2}\s*일(?!차)",
        r"\d{4}\s*년\s*음력\s*윤?\s*\d{1,2}\s*월\s*\d{1,2}\s*일",
        r"음력\s*\d{4}\s*년\s*윤?\s*\d{1,2}\s*월\s*\d{1,2}\s*일",
        r"음력\s*윤?\s*\d{1,2}\s*월\s*\d{1,2}\s*일",
    ]
    return any(re.search(pattern, text) for pattern in date_patterns)


def _parse_time(text): #시간 처리 함수
    if "자정" in text:
        return 0, 0
    if "정오" in text:
        return 12, 0

    hour = 9
    minute = 0
    time_match = re.search(TIME_PATTERN, text) #받아온 text를 위의 TIME_PATTERN에 맞추어 시간을 찾음

    if not time_match:                         #패턴에 따라 찾은 시간이 없다면 기본 설정 시간과 분을 반환
        return hour, minute

    parsed_hour = parse_korean_number(time_match.group(1))
    if parsed_hour is None:
        return hour, minute

    hour = parsed_hour

    if time_match.group(2):
        parsed_minute = parse_korean_number(time_match.group(2))
        if parsed_minute is not None:
            minute = parsed_minute
    elif "반" in time_match.group(0):
        minute = 30

    return hour, minute


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

    hour, minute = _parse_time(text)

    # 오전/오후 처리
    am_pm = None
    if "오전" in text or "아침" in text:
        am_pm = "AM"
    elif "오후" in text or "점심" in text or "저녁" in text:
        am_pm = "PM"

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
