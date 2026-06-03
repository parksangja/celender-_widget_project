# 중간 제출 안내

## 제출 목적

이 프로젝트는 PC 바탕화면에서 사용할 수 있는 캘린더 위젯 중간 결과물입니다.
현재는 PyQt6 UI, 일정 엔진, OpenAI API 입력 해석, 로컬 한국어 자연어 파서, 명령 실행기, 직접 일정 추가 기능까지 구현되어 있습니다.

## 제출에 포함할 파일

```text
main.py
calendar_engine.py
ai_parser_gpt.py
openai_calendar_client.py
korean_datetime_parser.py
holiday_updater.py
data_safety.py
executor.py
test_parser.py
test_executor.py
test_calendar_features.py
test_holiday_updater.py
test_openai_calendar_client.py
test_data_safety.py
requirements.txt
.env.example
setup_env.bat
run_calendar.bat
make_submission.bat
README.md
SUBMISSION.md
프로젝트 개요.md
```

## 제출에서 제외할 파일

```text
.git/
.venv/
__pycache__/
events.json
.env
holiday_cache.json
*.json.bak
*.json.tmp
*.json.corrupt-*
*.pyc
```

## 파일별 역할

- `main.py`: PyQt6 기반 UI 실행 파일입니다. 3분할 화면, AI 입력창, 캘린더, 일정 목록, 직접 추가 창을 담당합니다.
- `calendar_engine.py`: 일정 추가, 조회, 삭제, 수정, 저장, 충돌 검사, 색상 저장, 반복 일정을 담당합니다.
- `ai_parser_gpt.py`: OpenAI API 키가 없거나 API 호출이 실패했을 때 사용하는 로컬 한국어 자연어 파서입니다.
- `openai_calendar_client.py`: OpenAI API 응답을 일정 명령으로 변환하고, 실패 시 로컬 파서로 대체합니다.
- `korean_datetime_parser.py`: `오늘`, `내일`, `5월 3일`, `오후 세 시`, `음력 1월 1일` 같은 날짜/시간 표현을 해석합니다.
- `holiday_updater.py`: 공공데이터포털 공식 휴일 API를 2일 주기로 확인하고 `holiday_cache.json`에 저장/조회합니다.
- `data_safety.py`: `events.json`, `holiday_cache.json`을 안전하게 저장하고, 백업/복구를 처리합니다.
- `executor.py`: 파서가 만든 명령을 실제 캘린더 엔진에 실행합니다.
- `test_parser.py`: 자연어 파서가 의도대로 동작하는지 확인합니다.
- `test_executor.py`: 파서 명령과 캘린더 엔진 연결이 의도대로 동작하는지 확인합니다.
- `test_calendar_features.py`: 음력 변환, 공휴일 계산, 무기한 기간 일정 기능을 확인합니다.
- `test_holiday_updater.py`: 공식 휴일 응답 파싱, 2일 캐시, API 캐시 조회 기능을 확인합니다.
- `test_openai_calendar_client.py`: OpenAI 응답 추출, 명령 정규화, API 요청 형식을 확인합니다.
- `test_data_safety.py`: 일정 파일과 휴일 캐시 파일의 백업/복구 동작을 확인합니다.
- `requirements.txt`: 실행에 필요한 Python 패키지를 기록합니다.
- `.env.example`: 공공데이터포털 API 키와 OpenAI API 키를 `.env`에 넣는 형식을 보여주는 예시 파일입니다.
- `setup_env.bat`: Windows에서 가상환경과 패키지 설치를 쉽게 실행하기 위한 파일입니다.
- `run_calendar.bat`: Windows에서 앱을 쉽게 실행하기 위한 파일입니다.

## 실행 방법

처음 한 번만 환경을 준비합니다.

```powershell
setup_env.bat
```

앱을 실행합니다.

```powershell
run_calendar.bat
```

또는 PowerShell에서 직접 실행할 수 있습니다.

```powershell
.\.venv\Scripts\python.exe main.py
```

## 제출용 폴더 만들기

아래 파일을 실행하면 제출에 필요한 파일만 `calendar_widget_submission` 폴더에 복사됩니다.

```powershell
make_submission.bat
```

그 후 `calendar_widget_submission` 폴더만 제출하면 됩니다.

## 테스트 방법

```powershell
.\.venv\Scripts\python.exe -m unittest test_parser.py test_executor.py test_calendar_features.py test_holiday_updater.py test_openai_calendar_client.py test_data_safety.py
```

## 현재 구현 범위

- 캘린더 UI 표시
- 현재 달 이외 날짜 흐림 표시
- AI 입력 영역 접기/펼치기
- 날짜 클릭 시 오른쪽 일정 목록 갱신
- OpenAI API 기반 AI 입력으로 일정 추가/조회/삭제
- OpenAI API 키가 없거나 호출 실패 시 로컬 파서로 자동 대체
- AI가 해석한 일정 추가/기간 추가/삭제 명령은 실행 전 확인
- AI 입력창과 달력 사이 정보 아이콘으로 OpenAI/휴일 API 연결 상태 표시
- 정보 아이콘 클릭으로 API 키와 모델명을 수정하는 설정 화면
- 오른쪽 `+` 버튼으로 일반 일정과 기간 일정 직접 추가
- 오른쪽 일정 목록 클릭으로 일정 수정/삭제
- 매주/매달/매년 반복 일정
- 반복 일정의 특정 회차 건너뛰기
- 반복 일정의 특정 회차만 수정
- 반복 일정 종료일 수정
- 음력 날짜를 양력으로 변환
- 대한민국 공휴일 달력 표시
- 공휴일/기간/일반 일정을 달력 색상 막대로 표시
- 일정별 사용자 색상 지정
- 공공데이터포털 특일 정보 기반 2일 주기 휴일 자동 업데이트
- API가 제공하는 선거일/임시공휴일 표시
- 시작일만 있는 무기한 기간 일정
- `events.json`과 `holiday_cache.json` 안전 저장/백업/손상 복구
- 일정 충돌 검사
- JSON 파일 저장

## 이후 개선할 부분

- UI 디자인 세부 조정
