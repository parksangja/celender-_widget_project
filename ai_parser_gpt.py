import re
from datetime import datetime, timedelta
from korean_datetime_parser import parse_korean_datetime

def to_engine_format(dt): #엔진과 연결하기 위한 함수(엔진과 출력형식 맞추는 용도)
    if not hasattr(dt, "strftime"):
        raise TypeError(f"dt is not datetime: {type(dt)}")
    return dt.strftime("%Y-%m-%d"), dt.strftime("%H:%M")

def extract_title(text: str): #제목 추출용 함수
    # 시간/날짜 관련 단어 제거
    cleaned = re.sub(
        r"(오늘|내일|모레|글피|다음주|오전|오후|\d{1,2}시|\d{1,2}분)",
        "",
        text
    )

    # 명령어 제거
    cleaned = re.sub(r"(추가해줘|잡아줘|넣어줘|예약해줘)", "", cleaned)

    # 공백 정리
    cleaned = cleaned.strip()

    # fallback
    return cleaned if cleaned else "일정"

def extract_duration(text: str): #이벤트 지속시간 처리용 함수
    match = re.search(r"(\d+)\s*시간", text)
    if match:
        return int(match.group(1)) * 60

    match = re.search(r"(\d+)\s*분", text)
    if match:
        return int(match.group(1))

    return 60  # 기본값

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
        # 간단 버전: id 기반 삭제는 나중에
        return {
            "action": "delete",
            "id": 1  # placeholder
        }

    return {"action": "unknown"}