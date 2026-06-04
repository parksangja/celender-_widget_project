import json
import os
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timedelta
from xml.etree import ElementTree

from data_safety import load_json_safely, save_json_safely


BASE_URL = "http://apis.data.go.kr/B090041/openapi/service/SpcdeInfoService/getRestDeInfo" #API로 가져오는 파일의 원주소
PROJECT_DIR = os.path.dirname(__file__) #프로젝트 폴더의 주소
HOLIDAY_CACHE_PATH = os.path.join(PROJECT_DIR, "holiday_cache.json") #프로젝트 폴더에 holiday_cache.json을 추가함
ENV_FILE = os.path.join(PROJECT_DIR, ".env") #프로젝트 폴더에 환경변수를 관리할 .evn파일을 추가함
API_KEY_ENV = "KOREA_HOLIDAY_API_KEY" #API키는 환경변수에 있는 휴일정보 API키
UPDATE_INTERVAL_DAYS = 2 #업데이트 주기
REQUEST_TIMEOUT_SECONDS = 8 #요청 제한 시간


@dataclass
class HolidayUpdateResult:
    updated: bool
    reason: str
    years: list[int]
    error: str = ""


def get_api_key(env_path=None): #환경변수에서 API키를 가져오는 함수
    env_key = os.environ.get(API_KEY_ENV, "").strip() #환경변수에서 휴일정보 API키를 가져옴.
    if env_key: #만약 키를 못찾으면 아래로 내려감.
        return env_key

    dotenv_key = load_env_value(API_KEY_ENV, env_path or ENV_FILE) #환경변수 경로나 파일을 열어 휴일정보 API키를 찾음.
    if dotenv_key:
        return dotenv_key

    return None #위 조건문을 모두 실패한다면 None 반환


def load_env_value(name, env_path=None): #환경변수 파일을 만드는 함수
    env_path = env_path or ENV_FILE      #env_path는 받아온 경로나 경로가 없으면 파일로 한다.
    if not os.path.exists(env_path):     #모종의 이유로 환경변수 경로나 파일이 없다면 None을 반환한다.
        return None

    with open(env_path, "r", encoding="utf-8") as f: #환경변수 경로를 찾았다면 해당 파일을 열어 읽음.
        lines = f.readlines()                        #파일의 내용을 한줄씩 읽어 리스트로 저장

    prefix = f"{name}="
    for raw_line in lines:  #개별 요소마다 검사 -> 여러 API에서 휴일정보 API키 찾기
        line = raw_line.strip() #공백 삭제
        if not line or line.startswith("#") or "=" not in line: #만약 요소가 빈 문자열이거나 "#"으로 시작하거나 ""="이 포함되어 있지 않다면, 패스
            continue

        if not line.startswith(prefix):                         #만약 요소가 휴일정보 API키의 이름이 아니라면 패스
            continue

        value = line.split("=", 1)[1].strip()                   #휴일정보 API를 찾았다면 첫번째 "=" 기준으로 뒤에 있는 문자열을 가져와 공백 제거
        if (value.startswith('"') and value.endswith('"')) or ( #문자열이 "["~"]"이거나 "['~']" 이면 안에 있는 "" 과 '' 제거
            value.startswith("'") and value.endswith("'")
        ):
            value = value[1:-1]

        return value.strip() or None #순수한 API키를 반환함. API키를 못찾았다면 None반환

    return None


def load_holiday_cache(cache_path=None): #전에 불러온 휴일정보 캐시를 불러오는 함수
    cache_path = cache_path or HOLIDAY_CACHE_PATH   #load_env_value처럼 초기 설정
    data = load_json_safely(
        cache_path,
        {"updated_at": None, "years": {}},
        validator=lambda value: isinstance(value, dict),
    )

    data.setdefault("updated_at", None) #위 조건문을 통과하면 딕셔너리에 "updated_at" key를 찾고 없으면 해당 키에 None 값을 가지게 딕셔너리에 저장
    data.setdefault("years", {})        #updated_at과 마찬가지
    if not isinstance(data["years"], dict):
        data["years"] = {}
    return data                         #data 딕셔너리 반환


def save_holiday_cache(cache, cache_path=None): #휴일정보 캐시를 저장하는 함수
    cache_path = cache_path or HOLIDAY_CACHE_PATH
    save_json_safely(cache_path, cache)


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
