import json
import os
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timedelta
from xml.etree import ElementTree


BASE_URL = "http://apis.data.go.kr/B090041/openapi/service/SpcdeInfoService/getRestDeInfo"
PROJECT_DIR = os.path.dirname(__file__)
HOLIDAY_CACHE_PATH = os.path.join(PROJECT_DIR, "holiday_cache.json")
ENV_FILE = os.path.join(PROJECT_DIR, ".env")
API_KEY_ENV = "KOREA_HOLIDAY_API_KEY"
UPDATE_INTERVAL_DAYS = 2
REQUEST_TIMEOUT_SECONDS = 8


@dataclass
class HolidayUpdateResult:
    updated: bool
    reason: str
    years: list[int]
    error: str = ""


def get_api_key(env_path=None):
    env_key = os.environ.get(API_KEY_ENV, "").strip()
    if env_key:
        return env_key

    dotenv_key = load_env_value(API_KEY_ENV, env_path or ENV_FILE)
    if dotenv_key:
        return dotenv_key

    return None


def load_env_value(name, env_path=None):
    env_path = env_path or ENV_FILE
    if not os.path.exists(env_path):
        return None

    with open(env_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    prefix = f"{name}="
    for raw_line in lines:
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        if not line.startswith(prefix):
            continue

        value = line.split("=", 1)[1].strip()
        if (value.startswith('"') and value.endswith('"')) or (
            value.startswith("'") and value.endswith("'")
        ):
            value = value[1:-1]

        return value.strip() or None

    return None


def load_holiday_cache(cache_path=None):
    cache_path = cache_path or HOLIDAY_CACHE_PATH
    if not os.path.exists(cache_path):
        return {"updated_at": None, "years": {}}

    try:
        with open(cache_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return {"updated_at": None, "years": {}}

    if not isinstance(data, dict):
        return {"updated_at": None, "years": {}}

    data.setdefault("updated_at", None)
    data.setdefault("years", {})
    return data


def save_holiday_cache(cache, cache_path=None):
    cache_path = cache_path or HOLIDAY_CACHE_PATH
    temp_path = f"{cache_path}.tmp"

    with open(temp_path, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)
        f.write("\n")

    os.replace(temp_path, cache_path)


def is_cache_fresh(cache, now=None, update_interval_days=UPDATE_INTERVAL_DAYS):
    updated_at = cache.get("updated_at")
    if not updated_at:
        return False

    try:
        updated_time = datetime.fromisoformat(updated_at)
    except ValueError:
        return False

    now = now or datetime.now()
    return now - updated_time < timedelta(days=update_interval_days)


def load_cached_public_holidays(year, cache_path=None):
    cache = load_holiday_cache(cache_path)
    holidays = cache.get("years", {}).get(str(year), {})
    if not isinstance(holidays, dict):
        return {}

    result = {}
    for date_str, names in holidays.items():
        if isinstance(names, str):
            result[date_str] = [names]
        elif isinstance(names, list):
            result[date_str] = [str(name) for name in names if str(name).strip()]

    return result


def get_korean_holidays(year, cache_path=None):
    holidays = load_cached_public_holidays(year, cache_path)
    return {
        date_str: names
        for date_str, names in sorted(holidays.items())
        if date_str.startswith(f"{year}-")
    }


def fetch_public_holidays(year, service_key, timeout=REQUEST_TIMEOUT_SECONDS):
    encoded_key = service_key if "%" in service_key else urllib.parse.quote(service_key, safe="")
    query = urllib.parse.urlencode(
        {
            "pageNo": "1",
            "numOfRows": "100",
            "solYear": str(year),
            "_type": "json",
        }
    )
    url = f"{BASE_URL}?ServiceKey={encoded_key}&{query}"

    with urllib.request.urlopen(url, timeout=timeout) as response:
        payload = response.read()

    return parse_public_holiday_response(payload)


def parse_public_holiday_response(payload):
    if isinstance(payload, bytes):
        text = payload.decode("utf-8-sig")
    else:
        text = str(payload)

    stripped = text.lstrip()
    if stripped.startswith("{"):
        return _parse_json_holiday_response(stripped)

    return _parse_xml_holiday_response(stripped)


def update_holiday_cache(
    years,
    service_key=None,
    now=None,
    force=False,
    cache_path=None,
    fetcher=None,
    update_interval_days=UPDATE_INTERVAL_DAYS,
):
    years = sorted({int(year) for year in years})
    now = now or datetime.now()
    cache = load_holiday_cache(cache_path)

    if (
        not force
        and is_cache_fresh(cache, now, update_interval_days)
        and _cache_has_years(cache, years)
    ):
        return HolidayUpdateResult(False, "fresh_cache", years)

    service_key = service_key or get_api_key()
    if not service_key:
        return HolidayUpdateResult(False, "missing_api_key", years)

    fetcher = fetcher or (lambda year: fetch_public_holidays(year, service_key))
    cache.setdefault("years", {})

    updated_years = []
    errors = []
    for year in years:
        try:
            cache["years"][str(year)] = fetcher(year)
            updated_years.append(year)
        except Exception as err:
            errors.append(f"{year}: {err}")

    if updated_years:
        cache["updated_at"] = now.isoformat(timespec="seconds")
        cache["source"] = "data.go.kr SpcdeInfoService getRestDeInfo"
        save_holiday_cache(cache, cache_path)
        return HolidayUpdateResult(True, "updated", updated_years, "; ".join(errors))

    return HolidayUpdateResult(False, "fetch_failed", years, "; ".join(errors))


def _cache_has_years(cache, years):
    cached_years = cache.get("years", {})
    return all(str(year) in cached_years for year in years)


def _add_result_holiday(result, date_str, name):
    result.setdefault(date_str, [])
    if name not in result[date_str]:
        result[date_str].append(name)


def _parse_json_holiday_response(text):
    data = json.loads(text)
    response = data.get("response", {})
    header = response.get("header", {})
    result_code = str(header.get("resultCode", "00"))
    result_message = header.get("resultMsg", "")

    if result_code != "00":
        raise RuntimeError(f"{result_code} {result_message}".strip())

    body = response.get("body", {})
    items = body.get("items") or {}
    raw_items = items.get("item", [])
    if isinstance(raw_items, dict):
        raw_items = [raw_items]

    result = {}
    for item in raw_items:
        if str(item.get("isHoliday", "")).upper() != "Y":
            continue

        locdate = str(item.get("locdate", "")).strip()
        if len(locdate) != 8:
            continue

        date_str = f"{locdate[:4]}-{locdate[4:6]}-{locdate[6:]}"
        name = str(item.get("dateName", "")).strip()
        if name:
            _add_result_holiday(result, date_str, name)

    return result


def _parse_xml_holiday_response(text):
    root = ElementTree.fromstring(text)
    result_code = root.findtext(".//resultCode", default="00")
    result_message = root.findtext(".//resultMsg", default="")

    if result_code != "00":
        raise RuntimeError(f"{result_code} {result_message}".strip())

    result = {}
    for item in root.findall(".//item"):
        if item.findtext("isHoliday", default="").upper() != "Y":
            continue

        locdate = item.findtext("locdate", default="").strip()
        if len(locdate) != 8:
            continue

        date_str = f"{locdate[:4]}-{locdate[4:6]}-{locdate[6:]}"
        name = item.findtext("dateName", default="").strip()
        if name:
            _add_result_holiday(result, date_str, name)

    return result
