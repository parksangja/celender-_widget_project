import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime

from ai_parser_gpt import parse as parse_locally
from holiday_updater import load_env_value


OPENAI_API_URL = "https://api.openai.com/v1/responses"
OPENAI_API_KEY_ENV = "OPENAI_API_KEY"
OPENAI_MODEL_ENV = "OPENAI_MODEL"
DEFAULT_OPENAI_MODEL = "gpt-5.4-mini"


class OpenAICalendarError(Exception):
    pass


@dataclass
class CalendarAIResult:
    command: dict
    source: str
    message: str
    raw_text: str = ""


def get_openai_api_key(env_path=None):
    env_key = os.environ.get(OPENAI_API_KEY_ENV, "").strip()
    if env_key:
        return env_key

    return load_env_value(OPENAI_API_KEY_ENV, env_path)


def get_openai_model(env_path=None):
    env_model = os.environ.get(OPENAI_MODEL_ENV, "").strip()
    if env_model:
        return env_model

    return load_env_value(OPENAI_MODEL_ENV, env_path) or DEFAULT_OPENAI_MODEL


def is_openai_configured(env_path=None):
    return bool(get_openai_api_key(env_path))


def parse_calendar_command(text, now=None):
    if not is_openai_configured():
        return CalendarAIResult(
            parse_locally(text, now=now),
            "local",
            "OpenAI API 키가 없어 로컬 파서로 해석했습니다.",
        )

    try:
        return parse_with_openai(text, now=now)
    except Exception as err:
        return CalendarAIResult(
            parse_locally(text, now=now),
            "local_fallback",
            f"{format_openai_error_message(err)}\n현재는 로컬 파서로 처리했습니다.",
        )


def parse_with_openai(text, now=None, requester=None):
    now = now or datetime.now()
    payload = build_request_payload(text, now)
    response = send_openai_request(payload, requester=requester)
    raw_text = extract_output_text(response)
    command = normalize_command(json.loads(raw_text), now=now)

    return CalendarAIResult(command, "openai", "OpenAI API로 해석했습니다.", raw_text)


def build_request_payload(text, now):
    return {
        "model": get_openai_model(),
        "instructions": build_instructions(now),
        "input": text,
        "text": {
            "format": {
                "type": "json_schema",
                "name": "calendar_command",
                "strict": True,
                "schema": command_schema(),
            }
        },
    }


def build_instructions(now):
    today = now.strftime("%Y-%m-%d")
    current_time = now.strftime("%H:%M")
    return f"""
You convert Korean natural language calendar requests into JSON commands.
Return only JSON matching the schema.

Current date: {today}
Current time: {current_time}

Rules:
- action must be one of add, add_period, list, delete, unknown.
- Use YYYY-MM-DD for dates and HH:MM 24-hour time.
- If the user omits the date for an add or list request, use the current date.
- If the user omits duration for a timed event, use 60 minutes.
- For timed events, use action add with title, date, time, duration.
- For period events, use action add_period with title, start_date, end_date.
- If a period is indefinite or says 무기한/계속, set end_date to null.
- For list, set date.
- For delete, put known filters inside condition.
- recurrence applies only to timed add events: none, weekly, monthly, yearly.
- Use recurrence_end only when the user clearly gives a repeat end date.
- If the request cannot be understood as a calendar command, action must be unknown.
- Do not invent a color unless the user explicitly says one.
""".strip()


def command_schema():
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
            "reply",
        ],
        "properties": {
            "action": {
                "type": "string",
                "enum": ["add", "add_period", "list", "delete", "unknown"],
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
            "reply": {"type": "string"},
        },
    }


def send_openai_request(payload, requester=None):
    api_key = get_openai_api_key()
    if not api_key:
        raise OpenAICalendarError("OPENAI_API_KEY가 설정되어 있지 않습니다.")

    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        OPENAI_API_URL,
        data=data,
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
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


def format_openai_error_message(err):
    message = str(err).strip()
    if message:
        return message

    return "OpenAI 해석에 실패했습니다."


def format_openai_http_error(status_code, detail):
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


def parse_openai_error_detail(detail):
    try:
        data = json.loads(detail)
    except json.JSONDecodeError:
        return {}

    error_data = data.get("error", {})
    if not isinstance(error_data, dict):
        return {}

    return error_data


def extract_output_text(response):
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


def normalize_command(data, now=None):
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

    return {"action": "unknown"}
