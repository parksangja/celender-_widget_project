##한국어 명렁을 처리하기 위한 파일
#
import re
from datetime import datetime, timedelta

from korean_lunar_calendar import KoreanLunarCalendar

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
#정규식 의미:
#조건:정규식 바로 앞글자가 한글이나 숫자가 아니면 됨
#한자리 또는 두자리 수 숫자 또는 한국어 숫자 패턴 + 앞에 공백 0개 이상의 시(간) + 한자리 또는 두자리 수 숫자 또는 한국어 숫자 패턴 + 앞에 공백 0개 이상의 분 또는 반

def lunar_to_solar(year, month, day, leap_month=False): #음력을 양력으로 변환하는 함수
    calendar = KoreanLunarCalendar()
    is_valid = calendar.setLunarDate(year, month, day, leap_month)

    if not is_valid:
        raise ValueError("Invalid lunar date")

    return datetime.strptime(calendar.SolarIsoFormat(), "%Y-%m-%d").date()


def has_lunar_date_expression(text): #음력 날짜 표현이 있는지 검사하는 함수
    lunar_patterns = [
        r"\d{4}\s*년\s*음력\s*윤?\s*\d{1,2}\s*월\s*\d{1,2}\s*일",
        r"음력\s*\d{4}\s*년\s*윤?\s*\d{1,2}\s*월\s*\d{1,2}\s*일",
        r"음력\s*윤?\s*\d{1,2}\s*월\s*\d{1,2}\s*일",
    ]
    return any(re.search(pattern, text) for pattern in lunar_patterns)


def parse_korean_number(value):
    value = value.strip()       #가져온 인수의 공백 제거
    if value.isdigit():         #숫자면 그냥 int씌워서 반환
        return int(value)

    if value in KOREAN_NUMBER_MAP:       #위 딕셔너리에 있는 글자면 그에 맞게 반환
        return KOREAN_NUMBER_MAP[value]

    if "십" in value:   #받아온 인수가 '십 얼마'라면 십의자리수랑 일의 자리수랑 분리함
        tens_text, ones_text = value.split("십", 1) #십을 기준으로 한번만 나눔
        tens = 1 if tens_text == "" else KOREAN_NUMBER_MAP.get(tens_text) #십 앞에 문자가 없으면 1로, 있으면 딕셔너리에서 꺼내옴
        ones = 0 if ones_text == "" else KOREAN_NUMBER_MAP.get(ones_text) #일의 자리도 마찬가지

        if tens is not None and ones is not None: #십의 자리랑 일의 자리가 있으면 아래처럼 숫자 만들어서 반환
            return tens * 10 + ones

    return None


def _date_or_none(year, month, day): #날짜인지 아닌지 학인하는 함수
    try:
        return datetime(year=year, month=month, day=day).date() #3개 중에 하나 없으면 에러
    except ValueError:
        return None


def _add_months(year, month, amount): #개월 수 더하는 함수 (2026년 5월 1개월)
    total_month = (year * 12) + (month - 1) + amount #총 개월수
    return total_month // 12, (total_month % 12) + 1 #total_month//12는 년도, (total_month % 12) + 1는 몇월


def _find_weekday(text): #월요일부터 일요일 중에 하나 감지해서 해당 요일에 해당하는 숫자 반환하는 함수
    for k, v in WEEKDAY_MAP.items():
        if k in text:
            return v
    return None


def _next_weekday_from(base_date, weekday):     #기준일로부터 어떤 요일이 얼마나 남았는지 계산하는 함수
    delta = (weekday - base_date.weekday()) % 7 #예시) 수요일 기준 다음주 월요일 계산 시, 수요일은 2, 월요일은 0 -> (0-2)%7=5
    return base_date + timedelta(days=delta)    #예시) 그래서 5일 남음


def _weekday_in_this_week(base_date, weekday): #어떤 요일이 실제 주에서 언제인지 계산하는 함수
    start_of_this_week = base_date - timedelta(days=base_date.weekday()) #기준일로 월요일을 구함
    return start_of_this_week + timedelta(days=weekday) #월요일에 weekday더해서 실제 요일 반환


def _weekday_in_next_week(base_date, weekday): #다음주 계산 함수 (위 _weekday_in_this_week랑 똑같이 작동함)
    start_of_this_week = base_date - timedelta(days=base_date.weekday())
    start_of_next_week = start_of_this_week + timedelta(days=7)
    return start_of_next_week + timedelta(days=weekday)


def _parse_written_date(text, now): #실제 한국 날짜를 작성하는 함수
    lunar_match = re.search(r"(\d{4})\s*년\s*음력\s*(윤)?\s*(\d{1,2})\s*월\s*(\d{1,2})\s*일", text) #text를 주어진 정규식과 비교해 겹치는 것을 산출
    #정규식 의미: 4자리수 + 공백 0개 이상 + 년 + 음력 + 윤(있어도 되고 없어도 됨) + 1자리 또는 2자리수의 월 + 1자리 또는 2자리수의 달
    if lunar_match: #만약 정규식과 겹치는게 있다면 아래 명령 실행
        year = int(lunar_match.group(1)) #첫번째 그룹인 연도를 가져옴
        leap_month = lunar_match.group(2) is not None #두번째 그룹(윤)이 있으면 True, 없으면 False
        month = int(lunar_match.group(3)) #세번째 그룹인 달을 가져옴
        day = int(lunar_match.group(4))   #네번째 그룹인 일을 가져옴
        return lunar_to_solar(year, month, day, leap_month) #계산한거 가지고 실제 음력으로 변환해서 반환

    lunar_match = re.search(r"음력\s*(\d{4})\s*년\s*(윤)?\s*(\d{1,2})\s*월\s*(\d{1,2})\s*일", text)
    if lunar_match:
        year = int(lunar_match.group(1))
        leap_month = lunar_match.group(2) is not None
        month = int(lunar_match.group(3))
        day = int(lunar_match.group(4))
        return lunar_to_solar(year, month, day, leap_month)

    lunar_match = re.search(r"음력\s*(윤)?\s*(\d{1,2})\s*월\s*(\d{1,2})\s*일", text) #연도 없는 버전
    if lunar_match:
        leap_month = lunar_match.group(1) is not None
        month = int(lunar_match.group(2))
        day = int(lunar_match.group(3))
        return lunar_to_solar(now.year, month, day, leap_month) #받은 연도가 없기 때문에 현재 연도로 계산

    match = re.search(r"(\d{4})\s*년\s*(\d{1,2})\s*월\s*(\d{1,2})\s*일", text) #양력 버전
    if match:
        year, month, day = map(int, match.groups())
        return _date_or_none(year, month, day)

    match = re.search(r"(\d{1,2})\s*월\s*(\d{1,2})\s*일", text)
    if match:
        month, day = map(int, match.groups())
        return _date_or_none(now.year, month, day)

    match = re.search(r"(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})", text) #한글 없이 숫자로 된 날짜 가져오는 함수
    #정규식 의미: 네자리수 숫자 + -/. 세 문자중 하나 + 한자리 또는 두자리수 숫자 + -/. 세 문자중 하나 + 한자리 또는 두자리수 숫자
    if match:
        year, month, day = map(int, match.groups())
        return _date_or_none(year, month, day)

    match = re.search(r"(?<!\d)(\d{1,2})[/.](\d{1,2})(?!\d)", text)
    #(?<!\d)의미는 부정형 뒷쪽 확인. 현재 위치의 바로 앞글자가 숫자가 아니여야 함.
    if match:
        month, day = map(int, match.groups())
        return _date_or_none(now.year, month, day)

    match = re.search(r"(?:다음\s*달|다음달)\s*(\d{1,2})\s*일", text)
    #?:다음\s*달|다음달 : 다음달이 있는지 검사하여, 있어도 match에 포함하지 않음
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


def has_date_expression(text): #날짜 표현이 있는지 검사하는 함수
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
    
    #기본 설정: 오전 9시 00분
    hour = 9
    minute = 0
    time_match = re.search(TIME_PATTERN, text) #받아온 text를 위의 정규식에 맞추어 시간을 찾음

    if not time_match:                         #패턴에 따라 찾은 시간이 없다면 기본 설정 시간과 분을 반환
        return hour, minute

    parsed_hour = parse_korean_number(time_match.group(1)) #시간을 정규식에 따라 계산한 그룹 중 첫번째 그룹에서 가져옴
    if parsed_hour is None:
        return hour, minute

    hour = parsed_hour

    if time_match.group(2): #정규식으로 계산해서 분이나 반이 있으면 아래 명령 실행
        parsed_minute = parse_korean_number(time_match.group(2)) #반일때는 None 반환
        if parsed_minute is not None:
            minute = parsed_minute
    elif "반" in time_match.group(0): #또는 전체 정규식에 반이 있으면 분을 30으로 정함
        minute = 30

    return hour, minute


def parse_korean_datetime(text: str, now=None): #한국어 시간 표현 해석 파서
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
