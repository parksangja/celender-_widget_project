import re                             #문자열 처리 표준 라이브러리
from korean_datetime_parser import (  #korean_datetime_parser 파일에서 한국어를 해석하기 위해 만든 상수와 함수를 가져온다
    TIME_PATTERN,
    WEEKDAY_MAP,
    has_date_expression,
    parse_korean_datetime,
    parse_korean_number,
)

def to_engine_format(dt): #엔진과 연결하기 위한 함수(엔진과 출력형식 맞추는 용도)
    if not hasattr(dt, "strftime"): #hasattr 함수: dt라는 오브젝트에 "strftime"라는 속성이 있는지 검사하는 함수 (이와 유사한 함수로 getattr, setattr이 있음)
        raise TypeError(f"dt is not datetime: {type(dt)}")
    return dt.strftime("%Y-%m-%d"), dt.strftime("%H:%M")

#시간, 명령 해석을 위한 문자열 리스트들
DATE_WORDS = ["오늘", "내일", "모레", "글피", "이번주", "다음주", "이번달", "이번 달", "다음달", "다음 달"]
TIME_WORDS = ["오전", "오후", "아침", "점심", "저녁"]
ADD_WORDS = ["추가해줘", "추가", "잡아줘", "잡아", "예약해줘", "예약", "넣어줘", "넣어", "등록해줘", "등록"]
DELETE_WORDS = ["삭제해줘", "삭제", "지워줘", "지워", "없애줘", "없애"]
LIST_WORDS = ["보여줘", "보여", "조회해줘", "조회", "확인해줘", "확인"]
GENERAL_WORDS = ["일정", "스케줄"]
PERIOD_WORDS = ["무기한", "계속"]
RECURRENCE_WORDS = {
    "매주": "weekly",
    "매달": "monthly",
    "매월": "monthly",
    "매년": "yearly",
    "매해": "yearly",
}

PARTICLES = ["에서", "으로", "에게", "한테", "부터", "까지", "을", "를", "에", "랑", "과", "와"]
NUMBER_PATTERN = r"\d+|[가-힣]+"


def _remove_words(text, words):                         #단어 삭제 함수
    for word in sorted(words, key=len, reverse=True):   #길이가 긴 순서대로 정렬(길이 짧은 순으로 정렬 후 리버스로 뒤집음)
        text = text.replace(word, "")                   #단어를 빈 문자열로 교체해 삭제
    return text

def extract_title(text: str): #제목 추출용 함수
    original = text

    #text가 아래 작성된 페턴과 일치되면 대체 문자열으로 교체한다. (대충 re.sub()의 기능을 작성했음. 자세한거는 더 공부하기)
    text = re.sub(rf"({NUMBER_PATTERN})\s*시간\s*반", " ", text)
    text = re.sub(r"반\s*시간", " ", text)
    text = re.sub(rf"({NUMBER_PATTERN})\s*시간(?:\s*({NUMBER_PATTERN})\s*분)?", " ", text)
    text = re.sub(rf"({NUMBER_PATTERN})\s*분(?:\s*(?:동안|간))?", " ", text)
    text = re.sub(TIME_PATTERN, " ", text)
    text = re.sub(r"\d{4}\s*년\s*음력\s*윤?\s*\d{1,2}\s*월\s*\d{1,2}\s*일", " ", text)
    text = re.sub(r"음력\s*\d{4}\s*년\s*윤?\s*\d{1,2}\s*월\s*\d{1,2}\s*일", " ", text)
    text = re.sub(r"음력\s*윤?\s*\d{1,2}\s*월\s*\d{1,2}\s*일", " ", text)
    text = re.sub(r"\d{4}\s*년\s*\d{1,2}\s*월\s*\d{1,2}\s*일", " ", text)
    text = re.sub(r"\d{1,2}\s*월\s*\d{1,2}\s*일", " ", text)
    text = re.sub(r"(?:다음\s*달|다음달|이번\s*달|이번달)\s*\d{1,2}\s*일", " ", text)
    text = re.sub(r"\d{4}[-/.]\d{1,2}[-/.]\d{1,2}", " ", text)
    text = re.sub(r"(?<!\d)\d{1,2}[/.]\d{1,2}(?!\d)", " ", text)
    text = re.sub(r"(?<!\d)\d{1,2}\s*일(?!차)", " ", text)

    #text에서 위에 있는 문자열 리스트에 따라 시간, 명령, 조사 등을 삭제
    text = _remove_words(text, DATE_WORDS)
    text = _remove_words(text, list(WEEKDAY_MAP.keys()))
    text = _remove_words(text, TIME_WORDS)
    text = _remove_words(text, ADD_WORDS + DELETE_WORDS + LIST_WORDS)
    text = _remove_words(text, GENERAL_WORDS)
    text = _remove_words(text, PERIOD_WORDS)
    text = _remove_words(text, RECURRENCE_WORDS.keys())

    words = text.split()
    cleaned_words = []

    for w in words:
        for p in PARTICLES:
            if w.endswith(p):
                w = w[:-len(p)]
        if w:
            cleaned_words.append(w)

    text = " ".join(cleaned_words).strip()  

    if not text:
        return "일정"

    if len(text) < 2:
        return original.strip()

    return text

def extract_duration(text: str): #이벤트 지속시간 처리용 함수
    duration_text = re.sub(TIME_PATTERN, " ", text)

    match = re.search(rf"({NUMBER_PATTERN})\s*시간\s*반", duration_text)
    if match:
        hour = parse_korean_number(match.group(1))
        if hour is not None:
            return (hour * 60) + 30

    if re.search(r"반\s*시간", duration_text):
        return 30

    match = re.search(rf"({NUMBER_PATTERN})\s*시간(?:\s*({NUMBER_PATTERN})\s*분)?", duration_text)
    if match:
        hour = parse_korean_number(match.group(1))
        minute = parse_korean_number(match.group(2)) if match.group(2) else 0

        if hour is not None and minute is not None:
            return (hour * 60) + minute

    match = re.search(rf"({NUMBER_PATTERN})\s*분(?:\s*(?:동안|간))?", duration_text)
    if match:
        minute = parse_korean_number(match.group(1))
        if minute is not None:
            return minute

    return 60 

def build_delete_condition(text: str, now=None):
    condition = {}

    if has_date_expression(text):
        dt = parse_korean_datetime(text, now=now)
        condition["date"] = dt.strftime("%Y-%m-%d")

    title = extract_title(text)
    if title and title != "일정":
        condition["title"] = title

    return condition

def detect_action(text: str): #명령 행위 판단용 함수
    if any(k in text for k in ADD_WORDS):
        return "add"
    if any(k in text for k in DELETE_WORDS):
        return "delete"
    if any(k in text for k in LIST_WORDS):
        return "list"
    return "unknown"

def is_period_command(text: str):
    if "부터" not in text:
        return False

    return "기간" in text or any(word in text for word in PERIOD_WORDS)

def extract_recurrence(text: str):
    for word, recurrence in RECURRENCE_WORDS.items():
        if word in text:
            return recurrence

    return "none"

def parse(text: str, now=None): #메인 파서
    action = detect_action(text)

    dt = parse_korean_datetime(text, now=now)
    date, time = to_engine_format(dt)

    if action == "add":
        if is_period_command(text):
            return {
                "action": "add_period",
                "title": extract_title(text),
                "start_date": date,
                "end_date": None,
                "tag": "period",
                "priority": None,
            }

        return {
            "action": "add",
            "title": extract_title(text),
            "date": date,
            "time": time,
            "duration": extract_duration(text),
            "tag": None,
            "priority": None,
            "recurrence": extract_recurrence(text),
            "recurrence_end": None,
        }

    elif action == "list":
        return {
            "action": "list",
            "date": date
        }

    elif action == "delete":
        return {
            "action": "delete",
            "condition": build_delete_condition(text, now=now)
        }

    return {"action": "unknown"}
