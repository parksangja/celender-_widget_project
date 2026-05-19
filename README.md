# celender-_widget_project

PC 바탕화면에서 사용할 수 있는 미니 캘린더 위젯 프로젝트입니다.
PyQt6로 간단한 캘린더 UI를 만들고, 일정 데이터는 `events.json`에 저장합니다.

## 프로젝트 목적

Outlook이나 기본 캘린더 앱보다 가볍게 사용할 수 있는 PC용 캘린더 위젯을 만드는 것이 목표입니다.
현재 버전은 캘린더 UI, 일정 저장 엔진, 한국어 자연어 파서, 직접 일정 추가 기능을 포함한 중간 결과물입니다.

## 현재 구현된 기능

- PyQt6 기반 3분할 위젯 UI
- 왼쪽 AI 입력 영역
- 가운데 캘린더 영역
- 오른쪽 오늘/선택 날짜 일정 목록
- 한국어 자연어 일정 추가/조회/삭제 명령 파싱
- 일정 직접 추가 버튼
- JSON 파일 기반 일정 저장
- 일정 시간 충돌 검사
- 음력 날짜를 양력 날짜로 변환
- 대한민국 공휴일 달력 표시
- 선거일/임시공휴일 같은 수시 지정 휴일 표시
- 공공데이터포털 특일 정보 기반 2일 주기 휴일 자동 업데이트
- 시작일만 있는 무기한 기간 일정
- 파서/실행기 테스트

## 파일 구조

```text
celender-_widget_project/
|
|-- main.py                    # PyQt6 UI 실행 파일
|-- calendar_engine.py          # 일정 저장/조회/삭제/수정 엔진
|-- ai_parser_gpt.py            # 한국어 자연어 명령 파서
|-- korean_datetime_parser.py   # 한국어 날짜/시간 해석
|-- korean_calendar_utils.py    # 음력 변환과 대한민국 공휴일 계산
|-- holiday_updater.py          # 공식 휴일 API 자동 업데이트와 캐시 관리
|-- executor.py                 # 파서 명령을 캘린더 엔진에 실행
|
|-- test_parser.py              # 자연어 파서 테스트
|-- test_executor.py            # 실행기 테스트
|-- test_calendar_features.py   # 음력/공휴일/기간 일정 테스트
|-- test_holiday_updater.py     # 휴일 자동 업데이트 테스트
|
|-- requirements.txt            # 필요한 Python 패키지 목록
|-- special_holidays.json       # 선거일/임시공휴일 같은 수시 지정 휴일
|-- holiday_api_key.txt.example # 공공데이터포털 API 키 입력 예시
|-- setup_env.bat               # Windows 환경 준비용 실행 파일
|-- run_calendar.bat            # Windows 앱 실행 파일
|-- make_submission.bat         # 제출용 폴더 생성 파일
|-- README.md                   # 프로젝트 설명과 실행 방법
|-- SUBMISSION.md               # 제출 전 확인용 문서
|-- 프로젝트 개요.md             # 개발 동기와 초기 기획
```

## 제출 시 제외할 파일

아래 파일과 폴더는 자동 생성되거나 개인 실행 데이터이므로 제출물에 포함하지 않습니다.

```text
.venv/
__pycache__/
events.json
holiday_api_key.txt
holiday_cache.json
*.pyc
.git/
```

제출용 폴더를 자동으로 만들고 싶다면 아래 파일을 실행합니다.

```powershell
make_submission.bat
```

실행 후 만들어지는 `calendar_widget_submission` 폴더만 제출하면 됩니다.

## 실행 환경

- Python 3.12 이상
- PyQt6 필요

## 수시 지정 휴일 추가

선거일이나 임시공휴일처럼 매번 지정되는 휴일은 `special_holidays.json`에 추가합니다.

```json
[
  {
    "date": "2026-06-03",
    "name": "제9회 전국동시지방선거일"
  }
]
```

앱을 다시 실행하면 달력과 오른쪽 일정 목록에 반영됩니다.

## 휴일 자동 업데이트

공식 휴일 데이터는 공공데이터포털의 한국천문연구원 특일 정보 API에서 가져옵니다.
API 키가 있으면 앱을 켤 때 자동으로 확인하고, 마지막 업데이트 후 2일이 지나지 않았다면 `holiday_cache.json`에 저장된 캐시를 그대로 사용합니다.

API 키 설정 방법은 둘 중 하나를 사용하면 됩니다.

```powershell
$env:KOREA_HOLIDAY_API_KEY="공공데이터포털에서 받은 인증키"
```

또는 `holiday_api_key.txt.example` 파일을 복사해서 `holiday_api_key.txt`로 이름을 바꾼 뒤, 파일 안에 인증키를 넣으면 됩니다.
`holiday_api_key.txt`와 `holiday_cache.json`은 개인 설정/자동 생성 파일이므로 Git과 제출물에서 제외합니다.

PowerShell에서 `python --version`을 입력했을 때 버전이 나오지 않으면 Python이 설치되어 있지 않거나, PATH 설정이 되어 있지 않은 상태입니다.
그 경우 Python 공식 설치 파일을 사용하고, 설치할 때 **Add python.exe to PATH** 옵션을 켜야 합니다.

## 처음 실행 준비

프로젝트 폴더로 이동합니다.

```powershell
cd C:\Users\User\Desktop\project\celender-_widget_project
```

가상환경을 만듭니다.

```powershell
python -m venv .venv
```

필요한 패키지를 설치합니다.

```powershell
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

또는 `setup_env.bat` 파일을 실행해도 됩니다.

## 실행 방법

```powershell
.\.venv\Scripts\python.exe main.py
```

또는 `run_calendar.bat` 파일을 실행해도 됩니다.

## 선택: 가상환경 활성화해서 사용하기

아래 방식은 명령어를 짧게 쓸 수 있지만, PowerShell 실행 정책에 따라 막힐 수 있습니다.

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
```

만약 `Activate.ps1` 실행이 막히면, 이 README의 기본 방식처럼 `.\.venv\Scripts\python.exe`를 직접 사용하면 됩니다.

## Git 메모

`__pycache__`, `.venv`, `events.json` 같은 자동 생성 파일이나 개인 실행 데이터는 Git에 올리지 않도록 `.gitignore`에 등록되어 있습니다.

## 테스트 실행

```powershell
.\.venv\Scripts\python.exe -m unittest test_parser.py test_executor.py test_calendar_features.py test_holiday_updater.py
```
