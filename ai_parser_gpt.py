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
DATE_WORDS = [
    "오늘",
    "내일",
    "모레",
    "글피",
    "이번주",
    "이번 주",
    "다음주",
    "다음 주",
    "다다음주",
    "다다음 주",
    "다음다음주",
    "다음 다음 주",
    "이번달",
    "이번 달",
    "다음달",
    "다음 달",
]
TIME_WORDS = ["오전", "오후", "아침", "점심", "저녁"]
ADD_WORDS = ["추가해줘", "추가", "잡아줘", "잡아", "예약해줘", "예약", "넣어줘", "넣어", "등록해줘", "등록"]
DELETE_WORDS = ["삭제해줘", "삭제", "지워줘", "지워", "없애줘", "없애"]
LIST_WORDS = ["보여줘", "보여", "조회해줘", "조회", "확인해줘", "확인"]
UPDATE_WORDS = ["수정해줘", "수정", "변경해줘", "변경", "바꿔줘", "바꿔"]
SKIP_WORDS = ["건너뛰어줘", "건너뛰", "쉬어", "제외해줘", "제외", "빼줘", "빼"]
GENERAL_WORDS = ["일정", "스케줄"]
PERIOD_WORDS = ["무기한", "계속"]
CONTROL_WORDS = ["반복", "종료일", "끝나는날", "끝나는 날", "회차", "이번", "만"]
RECURRENCE_WORDS = {
    "매주": "weekly",
    "매달": "monthly",
    "매월": "monthly",
    "매년": "yearly",
    "매해": "yearly",
}

PARTICLES = ["에서", "으로", "에게", "한테", "부터", "까지", "을", "를", "에", "랑", "과", "와", "로"]
NUMBER_PATTERN = r"\d+|[가-힣]+"


def _remove_words(text, words):                         #단어 삭제 함수
    for word in sorted(words, key=len, reverse=True):   #길이가 긴 순서대로 정렬(길이 짧은 순으로 정렬 후 리버스로 뒤집음)
        text = text.replace(word, "")                   #단어를 word로 교체하거나, 받아온 word가 없으면 빈 문자열로 교체
    return text

def extract_title(text: str): #제목 추출용 함수
    original = text

    #text가 아래 작성된 패턴과 일치되면 대체 문자열으로 교체한다. (대충 re.sub()의 기능을 작성했음. 자세한거는 더 공부하기)
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

    #text에서 위에 있는 문자열 리스트에 따라 시간, 명령, 조사 등을 위 리스트에 따라 바꿈
    text = _remove_words(text, DATE_WORDS)
    text = _remove_words(text, list(WEEKDAY_MAP.keys()))
    text = _remove_words(text, TIME_WORDS)
    text = _remove_words(text, ADD_WORDS + DELETE_WORDS + LIST_WORDS + UPDATE_WORDS + SKIP_WORDS)
    text = _remove_words(text, GENERAL_WORDS)
    text = _remove_words(text, PERIOD_WORDS)
    text = _remove_words(text, CONTROL_WORDS)
    text = _remove_words(text, RECURRENCE_WORDS.keys())

    words = text.split() #text를 공백으로 나누어서 단어 리스트로 만듬
    cleaned_words = []

    for w in words:      #각 단어에서 조사 제거
        for p in PARTICLES:
            if w.endswith(p):
                w = w[:-len(p)]
        if w:            #w가 빈 문자열이 아니면 cleaned_words에 추가
            cleaned_words.append(w)

    text = " ".join(cleaned_words).strip() #공백을 사이에 두고 cleaned_words를 합쳐서 text로 만듬

    if not text:     #text가 빈 문자열이면 "일정"이라는 기본 제목을 반환
        return "일정"

    if len(text) < 2: #text가 한글자면 원문 반환
        return original.strip()

    return text

def extract_duration(text: str): #이벤트 지속시간 처리용 함수
    duration_text = re.sub(TIME_PATTERN, " ", text) #TIME_PATTERN 정규식과 text를 비교해서 일치하면 공백으로 반환

    match = re.search(rf"({NUMBER_PATTERN})\s*시간\s*반", duration_text) #해당 정규식과 duration_text를 비교해서 겹치는 부분을 저장 (몇시 반 처리용)
    if match:#겹치는 부분이 있다면 아래 조건문 실행
        hour = parse_korean_number(match.group(1)) #시간은 parse_korean_number 함수에 match의 첫번째 요소를 넣어 계산한 것
        if hour is not None:        #시간이 있다면 시간을 분으로 변환한 것과 30분을 합쳐서 반환
            return (hour * 60) + 30

    if re.search(r"반\s*시간", duration_text): #반 처리용
        return 30

    match = re.search(rf"({NUMBER_PATTERN})\s*시간(?:\s*({NUMBER_PATTERN})\s*분)?", duration_text) #몇시간 몇분 처리용
    if match:
        hour = parse_korean_number(match.group(1))
        minute = parse_korean_number(match.group(2)) if match.group(2) else 0

        if hour is not None and minute is not None:
            return (hour * 60) + minute

    match = re.search(rf"({NUMBER_PATTERN})\s*분(?:\s*(?:동안|간))?", duration_text) #몇분 처리용
    if match:
        minute = parse_korean_number(match.group(1))
        if minute is not None:
            return minute

    return 60  #없다면 기본값 60분 반환

def has_time_expression(text: str): #시간 표현 검사 함수
    #text에 TIME_PATTERN에 맞는 표현이 있거나, TIME_WORDS 리스트에 있는 단어가 text에 포함되어 있으면 True 반환
    return bool(re.search(TIME_PATTERN, text)) or any(word in text for word in TIME_WORDS)

def has_duration_expression(text: str): #기간 표현 검사 함수
    duration_text = re.sub(TIME_PATTERN, " ", text)
    patterns = [
        rf"({NUMBER_PATTERN})\s*시간\s*반",
        r"반\s*시간",
        rf"({NUMBER_PATTERN})\s*시간(?:\s*({NUMBER_PATTERN})\s*분)?",
        rf"({NUMBER_PATTERN})\s*분(?:\s*(?:동안|간))?",
    ]
    #text에 patterns에 있는 정규식과 일치하는 표현이 있으면 True 반환
    return any(re.search(pattern, duration_text) for pattern in patterns) 

def build_delete_condition(text: str, now=None): #삭제 준비 함수
    condition = {}

    if has_date_expression(text):                   #시간 표현이 있다면 아래 명령 실행
        dt = parse_korean_datetime(text, now=now)   #text에 대해 parse_korean_datetime 함수를 이용해서 dt에 날짜와 시간 정보 저장
        condition["date"] = dt.strftime("%Y-%m-%d") #comdition에 날짜 정보 저장

    title = extract_title(text)     #text에서 제목 추출
    if title and title != "일정":    #제목이 있는데 제목에 일정이 없다면 아래 명령 실행
        condition["title"] = title  #condition에 제목 저장

    return condition

def detect_action(text: str): #명령 행위 판단용 함수
    if any(k in text for k in SKIP_WORDS):
        return "skip_occurrence"
    if any(k in text for k in UPDATE_WORDS):
        return "update"
    if any(k in text for k in ADD_WORDS):
        return "add"
    if any(k in text for k in DELETE_WORDS):
        return "delete"
    if any(k in text for k in LIST_WORDS):
        return "list"
    return "unknown"

def is_period_command(text: str): #기간 명령 판단 함수
    if "부터" not in text:
        return False

    return "기간" in text or any(word in text for word in PERIOD_WORDS)

def extract_recurrence(text: str): #반복 설정 추출 함수
    for word, recurrence in RECURRENCE_WORDS.items(): #RECURRENCE_WORDS 딕셔너리에 있는 단어와 반복 설정 모두 꺼내옴
        if word in text:                              #text에 word가 있다면 해당 반복 설정 반환
            return recurrence

    return "none"

def parse(text: str, now=None): #메인 파서
    action = detect_action(text)

    dt = parse_korean_datetime(text, now=now)
    date, time = to_engine_format(dt) #dt를 엔진 포멧에 맞추어 변환

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

    elif action == "skip_occurrence":
        title = extract_title(text)
        return {
            "action": "skip_occurrence",
            "occurrence_date": date,
            "condition": {
                "date": date,
                "title": title if title != "일정" else None,
            },
        }

    elif action == "update":
        title = extract_title(text)
        if "종료일" in text or "끝나는날" in text or "끝나는 날" in text:
            return {
                "action": "update_recurrence_end",
                "condition": {
                    "title": title if title != "일정" else None,
                },
                "recurrence_end": date,
            }

        updates = {}
        if title != "일정":
            updates["title"] = title
        if has_time_expression(text):
            updates["time"] = time
        if has_duration_expression(text):
            updates["duration"] = extract_duration(text)

        return {
            "action": "update_occurrence",
            "occurrence_date": date,
            "condition": {
                "date": date,
                "title": title if title != "일정" else None,
            },
            "updates": updates,
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
