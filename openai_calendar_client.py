import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime

from ai_parser_gpt import parse as parse_locally
from holiday_updater import load_env_value
from korean_datetime_parser import has_lunar_date_expression, parse_korean_datetime


OPENAI_API_URL = "https://api.openai.com/v1/responses"
OPENAI_API_KEY_ENV = "OPENAI_API_KEY"
OPENAI_MODEL_ENV = "OPENAI_MODEL"
DEFAULT_OPENAI_MODEL = "gpt-5.4-mini"


class OpenAICalendarError(Exception):
    pass

#@dataclass는 클래스 내부에서 꼭 써야하는 self와 __init__ 등을 줄여 파이썬에게 알아서 만들어달라고 부탁할 수 있게 만들어진 데코레이터
@dataclass
class CalendarAIResult:
    command: dict
    source: str
    message: str
    raw_text: str = ""


def get_openai_api_key(env_path=None):#API를 가져옴
    env_key = os.environ.get(OPENAI_API_KEY_ENV, "").strip()
    if env_key:
        return env_key

    return load_env_value(OPENAI_API_KEY_ENV, env_path)


def get_openai_model(env_path=None):#AI모델을 가져옴
    env_model = os.environ.get(OPENAI_MODEL_ENV, "").strip()
    if env_model:
        return env_model

    return load_env_value(OPENAI_MODEL_ENV, env_path) or DEFAULT_OPENAI_MODEL


def is_openai_configured(env_path=None):#가져온 API키가 있으면 True, 없으면 False 반환
    return bool(get_openai_api_key(env_path))


def parse_calendar_command(text, now=None):#명령을 실행하는 함수
    if not is_openai_configured(): #API가 없으면 아래 코드로 반환
        return CalendarAIResult( #출력
            parse_locally(text, now=now),#ai없는 파서로 해석해 출력
            "local",
            "OpenAI API 키가 없어 로컬 파서로 해석했습니다.",
        )

    try:
        return parse_with_openai(text, now=now) #ai에게 명령 보냄
    except Exception as err:
        return CalendarAIResult(
            parse_locally(text, now=now), #로컬 파서로 명령 실행
            "local_fallback",
            f"{format_openai_error_message(err)}\n현재는 로컬 파서로 처리했습니다.",
        )


def parse_with_openai(text, now=None, requester=None):#AI로 실행한 명령 출력 함수 requester가 있으면 테스트, 없이 None이면 실제 API불러와 실행
    now = now or datetime.now()
    payload = build_request_payload(text, now)                   #ai에 보낼 데이터 생성
    response = send_openai_request(payload, requester=requester) #응답 보내도 답 받음
    raw_text = extract_output_text(response)                     #답에서 결과 추출
    command = normalize_command(json.loads(raw_text), now=now)   #결과를 일반화 해서 명령을 만듬
    command = apply_lunar_date_from_text(command, text, now=now) #만약 음력 명령이면 추가 실행

    return CalendarAIResult(command, "openai", "OpenAI API로 해석했습니다.", raw_text)


def build_request_payload(text, now):#AI에게 보낼 데이터를 만드는 함수
    return {
        "model": get_openai_model(), #환경변수 파일에서 정하는 모델
        "instructions": build_instructions(now), #구조는 아래 규칙에 따름
        "input": text, #사용자 입력
        "text": {
            "format": {
                "type": "json_schema", #정해진 json 형식으로 답하라
                "name": "calendar_command",
                "strict": True, #구조에 무조건 맞추어라
                "schema": command_schema(), #개요는 아래 명령 개요를 따른다
            }
        },
    }


def build_instructions(now):#AI가 지켜야 할 구조 및 규칙을 적은 함수
    today = now.strftime("%Y-%m-%d")
    current_time = now.strftime("%H:%M")
    return f"""
You convert Korean natural language calendar requests into JSON commands.
Return only JSON matching the schema.

Current date: {today}
Current time: {current_time}

Rules:
- action must be one of add, add_period, list, delete, skip_occurrence, update_occurrence, update_recurrence_end, unknown.
- Use YYYY-MM-DD for dates and HH:MM 24-hour time.
- If the user writes a lunar date with 음력, convert it to a Gregorian YYYY-MM-DD date.
- If the user omits the date for an add or list request, use the current date.
- If the user omits duration for a timed event, use 60 minutes.
- For timed events, use action add with title, date, time, duration.
- For period events, use action add_period with title, start_date, end_date.
- If a period is indefinite or says 무기한/계속, set end_date to null.
- For list, set date.
- For delete, put known filters inside condition.
- For skipping one recurring occurrence, use skip_occurrence with occurrence_date and condition.
- For editing only one recurring occurrence, use update_occurrence with occurrence_date, condition, and updates.
- For changing recurrence end date, use update_recurrence_end with condition and recurrence_end.
- recurrence applies only to timed add events: none, weekly, monthly, yearly.
- Use recurrence_end only when the user clearly gives a repeat end date.
- If the request cannot be understood as a calendar command, action must be unknown.
- Do not invent a color unless the user explicitly says one.
""".strip()


def apply_lunar_date_from_text(command, text, now=None):#사용자 명령에 음력이 있으면 실행되는 함수
    if not has_lunar_date_expression(text):
        return command

    now = now or datetime.now()
    solar_date = parse_korean_datetime(text, now=now).strftime("%Y-%m-%d")#받은 음력 날짜를 양력으로 변환
    action = command.get("action")
    command = dict(command)

    if action in {"add", "list"}:
        command["date"] = solar_date

    elif action == "add_period":
        command["start_date"] = solar_date

    elif action == "delete":
        condition = dict(command.get("condition") or {})
        condition["date"] = solar_date
        command["condition"] = condition

    elif action in {"skip_occurrence", "update_occurrence"}:
        condition = dict(command.get("condition") or {})
        command["occurrence_date"] = solar_date
        condition["date"] = solar_date
        command["condition"] = condition

    elif action == "update_recurrence_end":
        command["recurrence_end"] = solar_date

    return command


def command_schema(): #명령 개요
    nullable_string = {"type": ["string", "null"]}
    nullable_integer = {"type": ["integer", "null"]}

    return {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "action",
            "title",
            "date",
            "time",
            "duration",
            "start_date",
            "end_date",
            "condition",
            "tag",
            "priority",
            "color",
            "recurrence",
            "recurrence_end",
            "occurrence_date",
            "updates",
            "reply",
        ],
        "properties": {
            "action": {
                "type": "string",
                "enum": [
                    "add",
                    "add_period",
                    "list",
                    "delete",
                    "skip_occurrence",
                    "update_occurrence",
                    "update_recurrence_end",
                    "unknown",
                ],
            },
            "title": nullable_string,
            "date": nullable_string,
            "time": nullable_string,
            "duration": nullable_integer,
            "start_date": nullable_string,
            "end_date": nullable_string,
            "condition": {
                "type": "object",
                "additionalProperties": False,
                "required": ["date", "time", "title"],
                "properties": {
                    "date": nullable_string,
                    "time": nullable_string,
                    "title": nullable_string,
                },
            },
            "tag": nullable_string,
            "priority": nullable_string,
            "color": nullable_string,
            "recurrence": {
                "type": "string",
                "enum": ["none", "weekly", "monthly", "yearly"],
            },
            "recurrence_end": nullable_string,
            "occurrence_date": nullable_string,
            "updates": {
                "type": "object",
                "additionalProperties": False,
                "required": ["title", "date", "time", "duration", "tag", "priority", "color"],
                "properties": {
                    "title": nullable_string,
                    "date": nullable_string,
                    "time": nullable_string,
                    "duration": nullable_integer,
                    "tag": nullable_string,
                    "priority": nullable_string,
                    "color": nullable_string,
                },
            },
            "reply": {"type": "string"},
        },
    }


def send_openai_request(payload, requester=None):#build_request_payload로 만든 명령을 AI에게 보내는 함수
    api_key = get_openai_api_key()
    if not api_key:
        raise OpenAICalendarError("OPENAI_API_KEY가 설정되어 있지 않습니다.")

    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")#명령을 받아 json형식으로 data를 만듬
    request = urllib.request.Request( #openai_api url을 열고 data를 보냄.
        OPENAI_API_URL,
        data=data,
        method="POST", #POST 형식으로 보냄
        headers={
            "Authorization": f"Bearer {api_key}", #api키로 인증
            "Content-Type": "application/json",   #보내는 내용의 타입은 어플리케이션에 사용할 json 파일
        },
    )

    try:
        if requester is not None:
            return requester(request, data)

        with urllib.request.urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as err:
        detail = err.read().decode("utf-8", errors="replace")
        raise OpenAICalendarError(format_openai_http_error(err.code, detail)) from err
    except urllib.error.URLError as err:
        raise OpenAICalendarError(f"OpenAI API 연결 실패: {err.reason}") from err


def format_openai_error_message(err):#형식 에러 처리 함수
    message = str(err).strip()
    if message:
        return message

    return "OpenAI 해석에 실패했습니다."


def format_openai_http_error(status_code, detail):#인터넷 패킷 에러 처리 함수
    error_data = parse_openai_error_detail(detail)
    error_code = error_data.get("code")
    error_type = error_data.get("type")
    error_message = error_data.get("message")

    if status_code == 429 and (
        error_code == "insufficient_quota" or error_type == "insufficient_quota"
    ):
        return "OpenAI API 사용 한도가 부족합니다.\n결제/크레딧 설정을 확인해주세요."

    if status_code == 401:
        return "OpenAI API 키가 올바르지 않습니다.\n.env의 OPENAI_API_KEY를 확인해주세요."

    if status_code == 429:
        return "OpenAI API 요청이 너무 많습니다.\n잠시 후 다시 시도해주세요."

    if error_message:
        return f"OpenAI API 오류 {status_code}: {error_message}"

    return f"OpenAI API 오류 {status_code}가 발생했습니다."


def parse_openai_error_detail(detail):#에러의 세부사항을 처리하는 함수
    try:
        data = json.loads(detail)
    except json.JSONDecodeError:
        return {}

    error_data = data.get("error", {})
    if not isinstance(error_data, dict):
        return {}

    return error_data


def extract_output_text(response):#AI가 처리한 데이터를 받아와 결과물을 추출하는 함수
    if "output_text" in response and response["output_text"]:
        return response["output_text"]

    chunks = []
    for item in response.get("output", []):
        for content in item.get("content", []):
            if content.get("type") == "output_text" and content.get("text"):
                chunks.append(content["text"])
            elif content.get("type") == "refusal":
                raise OpenAICalendarError(content.get("refusal", "OpenAI 응답이 거절되었습니다."))

    if not chunks:
        raise OpenAICalendarError("OpenAI 응답에서 텍스트를 찾지 못했습니다.")

    return "".join(chunks).strip()


def normalize_command(data, now=None):#추출한 결과물을 일반화해 출력하는 함수
    now = now or datetime.now()
    action = data.get("action", "unknown")
    if action == "add":
        if not data.get("date"):
            data["date"] = now.strftime("%Y-%m-%d")

        return {
            "action": "add",
            "title": data.get("title") or "일정",
            "date": data.get("date"),
            "time": data.get("time") or "09:00",
            "duration": data.get("duration") or 60,
            "tag": data.get("tag"),
            "priority": data.get("priority"),
            "color": data.get("color"),
            "recurrence": data.get("recurrence") or "none",
            "recurrence_end": data.get("recurrence_end"),
        }

    if action == "add_period":
        if not data.get("start_date") and not data.get("date"):
            return {"action": "unknown"}

        return {
            "action": "add_period",
            "title": data.get("title") or "기간",
            "start_date": data.get("start_date") or data.get("date"),
            "end_date": data.get("end_date"),
            "tag": data.get("tag") or "period",
            "priority": data.get("priority"),
            "color": data.get("color"),
        }

    if action == "list":
        return {
            "action": "list",
            "date": data.get("date") or now.strftime("%Y-%m-%d"),
        }

    if action == "delete":
        condition = {
            key: value
            for key, value in (data.get("condition") or {}).items()
            if value
        }
        return {
            "action": "delete",
            "condition": condition,
        }

    if action == "skip_occurrence":
        occurrence_date = data.get("occurrence_date") or data.get("date")
        if not occurrence_date:
            return {"action": "unknown"}

        condition = {
            key: value
            for key, value in (data.get("condition") or {}).items()
            if value
        }
        condition.setdefault("date", occurrence_date)
        return {
            "action": "skip_occurrence",
            "occurrence_date": occurrence_date,
            "condition": condition,
        }

    if action == "update_occurrence":
        occurrence_date = data.get("occurrence_date") or data.get("date")
        if not occurrence_date:
            return {"action": "unknown"}

        condition = {
            key: value
            for key, value in (data.get("condition") or {}).items()
            if value
        }
        condition.setdefault("date", occurrence_date)
        updates = {
            key: value
            for key, value in (data.get("updates") or {}).items()
            if value is not None
        }
        return {
            "action": "update_occurrence",
            "occurrence_date": occurrence_date,
            "condition": condition,
            "updates": updates,
        }

    if action == "update_recurrence_end":
        condition = {
            key: value
            for key, value in (data.get("condition") or {}).items()
            if value
        }
        if not condition or not data.get("recurrence_end"):
            return {"action": "unknown"}

        return {
            "action": "update_recurrence_end",
            "condition": condition,
            "recurrence_end": data.get("recurrence_end"),
        }

    return {"action": "unknown"}
