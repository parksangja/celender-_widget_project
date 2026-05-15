# 중간 제출 안내

## 제출 목적

이 프로젝트는 PC 바탕화면에서 사용할 수 있는 캘린더 위젯 중간 결과물입니다.
현재는 PyQt6 UI, 일정 엔진, 한국어 자연어 파서, 명령 실행기, 직접 일정 추가 기능까지 구현되어 있습니다.

## 제출에 포함할 파일

```text
main.py
calendar_engine.py
ai_parser_gpt.py
korean_datetime_parser.py
korean_calendar_utils.py
executor.py
test_parser.py
test_executor.py
test_calendar_features.py
requirements.txt
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
*.pyc
```

## 파일별 역할

- `main.py`: PyQt6 기반 UI 실행 파일입니다. 3분할 화면, AI 입력창, 캘린더, 일정 목록, 직접 추가 창을 담당합니다.
- `calendar_engine.py`: 일정 추가, 조회, 삭제, 수정, 저장, 충돌 검사를 담당합니다.
- `ai_parser_gpt.py`: 사용자의 한국어 자연어 입력을 `add`, `list`, `delete` 명령으로 변환합니다.
- `korean_datetime_parser.py`: `오늘`, `내일`, `5월 3일`, `오후 세 시`, `1시간 반` 같은 날짜/시간 표현을 해석합니다.
- `korean_calendar_utils.py`: 음력 날짜를 양력 날짜로 변환하고 대한민국 공휴일을 계산합니다.
- `executor.py`: 파서가 만든 명령을 실제 캘린더 엔진에 실행합니다.
- `test_parser.py`: 자연어 파서가 의도대로 동작하는지 확인합니다.
- `test_executor.py`: 파서 명령과 캘린더 엔진 연결이 의도대로 동작하는지 확인합니다.
- `test_calendar_features.py`: 음력 변환, 공휴일 계산, 무기한 기간 일정 기능을 확인합니다.
- `requirements.txt`: 실행에 필요한 Python 패키지를 기록합니다.
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
.\.venv\Scripts\python.exe -m unittest test_parser.py test_executor.py test_calendar_features.py
```

## 현재 구현 범위

- 캘린더 UI 표시
- 날짜 클릭 시 오른쪽 일정 목록 갱신
- 자연어 입력으로 일정 추가/조회/삭제
- 오른쪽 `+` 버튼으로 일정 직접 추가
- 음력 날짜를 양력으로 변환
- 대한민국 공휴일 달력 표시
- 시작일만 있는 무기한 기간 일정
- 일정 충돌 검사
- JSON 파일 저장

## 아직 개선할 부분

- 일정 수정 UI
- 일정 삭제 UI 버튼
- 더 세부적인 반복 일정 처리
- 실제 OpenAI API 연결
- UI 디자인 세부 조정
