import json
import os
import unittest
from datetime import datetime

from openai_calendar_client import (
    OPENAI_API_KEY_ENV,
    extract_output_text,
    format_openai_http_error,
    normalize_command,
    parse_with_openai,
)


class TestOpenAICalendarClient(unittest.TestCase):
    def test_extract_output_text_from_nested_response(self):
        response = {
            "output": [
                {
                    "content": [
                        {
                            "type": "output_text",
                            "text": '{"action":"list","date":"2026-05-21"}',
                        }
                    ]
                }
            ]
        }

        self.assertEqual(
            extract_output_text(response),
            '{"action":"list","date":"2026-05-21"}',
        )

    def test_normalize_add_command_keeps_recurrence(self):
        command = normalize_command(
            {
                "action": "add",
                "title": "운동",
                "date": "2026-05-22",
                "time": "18:00",
                "duration": 90,
                "recurrence": "weekly",
                "recurrence_end": "2026-06-30",
            }
        )

        self.assertEqual(command["action"], "add")
        self.assertEqual(command["title"], "운동")
        self.assertEqual(command["recurrence"], "weekly")
        self.assertEqual(command["recurrence_end"], "2026-06-30")

    def test_normalize_list_command_defaults_to_today(self):
        command = normalize_command(
            {"action": "list", "date": None},
            now=datetime(2026, 5, 21, 13, 0),
        )

        self.assertEqual(command, {"action": "list", "date": "2026-05-21"})

    def test_quota_error_is_user_friendly(self):
        detail = json.dumps(
            {
                "error": {
                    "message": "You exceeded your current quota.",
                    "type": "insufficient_quota",
                    "param": None,
                    "code": "insufficient_quota",
                }
            }
        )

        self.assertEqual(
            format_openai_http_error(429, detail),
            "OpenAI API 사용 한도가 부족합니다.\n결제/크레딧 설정을 확인해주세요.",
        )

    def test_parse_with_openai_uses_structured_response(self):
        original_key = os.environ.get(OPENAI_API_KEY_ENV)
        os.environ[OPENAI_API_KEY_ENV] = "test-key"

        def fake_requester(_request, data):
            payload = json.loads(data.decode("utf-8"))
            self.assertEqual(payload["text"]["format"]["type"], "json_schema")

            return {
                "output_text": json.dumps(
                    {
                        "action": "add_period",
                        "title": "프로젝트",
                        "date": None,
                        "time": None,
                        "duration": None,
                        "start_date": "2026-05-21",
                        "end_date": None,
                        "condition": {"date": None, "time": None, "title": None},
                        "tag": "period",
                        "priority": None,
                        "color": "#2DBE78",
                        "recurrence": "none",
                        "recurrence_end": None,
                        "reply": "기간 일정으로 해석했습니다.",
                    },
                    ensure_ascii=False,
                )
            }

        try:
            result = parse_with_openai(
                "오늘부터 프로젝트 기간 시작",
                now=datetime(2026, 5, 21, 13, 0),
                requester=fake_requester,
            )
        finally:
            if original_key is None:
                os.environ.pop(OPENAI_API_KEY_ENV, None)
            else:
                os.environ[OPENAI_API_KEY_ENV] = original_key

        self.assertEqual(result.source, "openai")
        self.assertEqual(result.command["action"], "add_period")
        self.assertEqual(result.command["end_date"], None)
        self.assertEqual(result.command["color"], "#2DBE78")


if __name__ == "__main__":
    unittest.main()
