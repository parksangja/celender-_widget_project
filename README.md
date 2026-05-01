# celender-_widget_project

PC 바탕화면에서 사용할 수 있는 미니 캘린더 위젯 프로젝트입니다.
PyQt6로 간단한 캘린더 UI를 만들고, 일정 데이터는 `events.json`에 저장합니다.

## 실행 환경

- Python 3.12 이상
- PyQt6 필요

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
