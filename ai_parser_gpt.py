import re
from korean_datetime_parser import WEEKDAY_MAP, has_date_expression, parse_korean_datetime

def to_engine_format(dt): #엔진과 연결하기 위한 함수(엔진과 출력형식 맞추는 용도)
    if not hasattr(dt, "strftime"):
        raise TypeError(f"dt is not datetime: {type(dt)}")
    return dt.strftime("%Y-%m-%d"), dt.strftime("%H:%M")

DATE_WORDS = ["오늘", "내일", "모레", "글피", "이번주", "다음주", "이번달", "이번 달", "다음달", "다음 달"]
TIME_WORDS = ["오전", "오후", "아침", "점심", "저녁"]
ADD_WORDS = ["추가해줘", "추가", "잡아줘", "잡아", "예약해줘", "예약", "넣어줘", "넣어", "등록해줘", "등록"]
DELETE_WORDS = ["삭제해줘", "삭제", "지워줘", "지워", "없애줘", "없애"]
LIST_WORDS = ["보여줘", "보여", "조회해줘", "조회", "확인해줘", "확인"]
GENERAL_WORDS = ["일정", "스케줄"]

PARTICLES = ["에서", "으로", "에게", "한테", "을", "를", "에", "랑", "과", "와"]


def _remove_words(text, words):
    for word in sorted(words, key=len, reverse=True):
        text = text.replace(word, "")
    return text

def extract_title(text: str): #제목 추출용 함수
    original = text

    # 기간 표현을 시간 표현보다 먼저 지워야 "2시간"에서 "간"이 남지 않는다.
    text = re.sub(r"\d+\s*시간", " ", text)
    text = re.sub(r"\d+\s*분", " ", text)
    text = re.sub(r"\d{1,2}\s*시(?:\s*\d{1,2}\s*분)?", " ", text)
    text = re.sub(r"\d{4}\s*년\s*\d{1,2}\s*월\s*\d{1,2}\s*일", " ", text)
    text = re.sub(r"\d{1,2}\s*월\s*\d{1,2}\s*일", " ", text)
    text = re.sub(r"(?:다음\s*달|다음달|이번\s*달|이번달)\s*\d{1,2}\s*일", " ", text)
    text = re.sub(r"\d{4}[-/.]\d{1,2}[-/.]\d{1,2}", " ", text)
    text = re.sub(r"(?<!\d)\d{1,2}[/.]\d{1,2}(?!\d)", " ", text)
    text = re.sub(r"(?<!\d)\d{1,2}\s*일(?!차)", " ", text)

    text = _remove_words(text, DATE_WORDS)
    text = _remove_words(text, list(WEEKDAY_MAP.keys()))
    text = _remove_words(text, TIME_WORDS)
    text = _remove_words(text, ADD_WORDS + DELETE_WORDS + LIST_WORDS)
    text = _remove_words(text, GENERAL_WORDS)

    words = text.split()
    cleaned_words = []

    for w in words:
        for p in PARTICLES:
            if w.endswith(p):
                w = w[:-len(p)]
        cleaned_words.append(w)

    text = " ".join(cleaned_words).strip()  

    if not text:
        return "일정"

    if len(text) < 2:
        return original.strip()

    return text

def extract_duration(text: str): #이벤트 지속시간 처리용 함수
    match = re.search(r"(\d+)\s*시간", text)
    if match:
        return int(match.group(1)) * 60

    match = re.search(r"(\d+)\s*분", text)
    if match:
        return int(match.group(1))

    return 60  # 기본값

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

def parse(text: str, now=None): #메인 파서
    action = detect_action(text)

    dt = parse_korean_datetime(text, now=now)
    date, time = to_engine_format(dt)

    if action == "add":
        return {
            "action": "add",
            "title": extract_title(text),
            "date": date,
            "time": time,
            "duration": extract_duration(text),
            "tag": None,
            "priority": None
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
