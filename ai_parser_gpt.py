import re
from datetime import datetime, timedelta
from korean_datetime_parser import parse_korean_datetime

def to_engine_format(dt): #엔진과 연결하기 위한 함수(엔진과 출력형식 맞추는 용도)
    if not hasattr(dt, "strftime"):
        raise TypeError(f"dt is not datetime: {type(dt)}")
    return dt.strftime("%Y-%m-%d"), dt.strftime("%H:%M")

STOPWORDS = [
    "오늘", "내일", "모레", "글피", "다음주",
    "오전", "오후", "아침", "점심", "저녁",
    "시", "분", "시간",
    "추가해줘", "잡아줘", "예약해줘", "넣어줘",
    "일정", "스케줄"
]

PARTICLES = ["을", "를", "에", "에서", "으로", "랑", "과", "와"]

def extract_title(text: str): #제목 추출용 함수
    original = text

    # ------------------------
    # 1️⃣ 시간 표현 제거
    # ------------------------
    text = re.sub(r'\d{1,2}시(?:\s*\d{1,2}분)?', '', text)
    text = re.sub(r'\d+\s*시간', '', text)
    text = re.sub(r'\d+\s*분', '', text)

    # ------------------------
    # 2️⃣ 불용어 제거
    # ------------------------
    for word in STOPWORDS:
        text = text.replace(word, "")

    # ------------------------
    # 3️⃣ 조사 제거 (끝 단어 기준)
    # ------------------------
    words = text.split()
    cleaned_words = []

    for w in words:
        for p in PARTICLES:
            if w.endswith(p):
                w = w[:-len(p)]
        cleaned_words.append(w)

    text = " ".join(cleaned_words).strip()  

    # ------------------------
    # 4️⃣ fallback 처리
    # ------------------------
    if not text:
        return "일정"

    # 너무 짧으면 원문 일부 사용
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

def build_delete_condition(text: str):
    from korean_datetime_parser import parse_korean_datetime

    condition = {}

    # 날짜 추출
    if any(k in text for k in ["오늘", "내일", "모레", "글피", "다음주"]):
        dt = parse_korean_datetime(text)
        condition["date"] = dt.strftime("%Y-%m-%d")

    # 제목 추출
    title = extract_title(text)
    if title and title != "일정":
        condition["title"] = title

    return condition

def detect_action(text: str): #명령 행위 판단용 함수
    if any(k in text for k in ["추가", "잡아", "예약", "넣어"]):
        return "add"
    if any(k in text for k in ["삭제", "지워"]):
        return "delete"
    if any(k in text for k in ["보여", "조회", "확인"]):
        return "list"
    return "unknown"

def parse(text: str): #메인 파서
    action = detect_action(text)

    # 날짜/시간
    dt = parse_korean_datetime(text)
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
        "condition": build_delete_condition(text)
        }

    return {"action": "unknown"}