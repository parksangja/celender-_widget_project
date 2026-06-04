import json
import os
import shutil
from datetime import datetime
#validator은 유효성 검사를 위해 가져오는 매소드, 만약 검사한 데이터가 validator의 조건에 맞지 않으면 ValueError 예외 발생
#copy2는 파일 내용과 메타데이터까지 복사
#엔진 파일 라인 229, 235에서 사용

def backup_path(path): #백업 경로 설정 함수
    return f"{path}.bak" #경로에 .bak 붙여서 반환


def temp_path(path):   #임시 파일 경로 설정 함수
    return f"{path}.tmp" #경로에 .tmp 붙여서 반환


def corrupt_path(path): #시발 이건 뭐야 -> 손상된 파일 경로 설정 함수
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S") #함수 불러올 때 시간 저장
    return f"{path}.corrupt-{timestamp}" #경로에 .corrupt-시간 붙여서 반환


def load_json_safely(path, default, validator=None):#`안전하게 JSON 파일을 불러오는 함수
    if not os.path.exists(path): #경로가 존재하지 않으면 기본값 반환
        return default

    try:
        data = read_json(path)   #JSON 파일 읽기
        validate_json_data(data, validator) #data 유효성 검사
        return data #통과시 data 반환
    except (OSError, json.JSONDecodeError, TypeError, ValueError): #에러 발생 시 아래 명령 실행
        backup_data = load_backup_json(path, validator)            #백업 파일에서 JSON 데이터 불러오기
        if backup_data is not None:     #백업 데이터가 있다면 아래 명령 실행
            preserve_corrupt_file(path) #손상 파일 보존
            restore_backup(path)        #백업 파일 복원
            return backup_data

        preserve_corrupt_file(path) #백업 데이터도 유효성검사를 통과 못하면, 기본값 반환
        return default


def save_json_safely(path, data): #안전하게 JSON 파일을 저장하는 함수
    directory = os.path.dirname(path) #path와 동일한 디렉토리 경로 저장
    if directory: #경로가 있다면 해당 디렉토리 생성, 이미 있다면 에러 없이 넘어감
        os.makedirs(directory, exist_ok=True)

    create_backup(path) #백업 파일 생성

    target_temp_path = temp_path(path)
    with open(target_temp_path, "w", encoding="utf-8") as f: #임시 파일을 열음
        json.dump(data, f, ensure_ascii=False, indent=2)     #임시 파일에 data를 그대로 저장
        f.write("\n")

    os.replace(target_temp_path, path) #원래 파일의 내용을 임시 파일 내용으로 교체


def read_json(path): #JSON 파일 읽는 함수
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def validate_json_data(data, validator): #data 유효성 검사 함수
    if validator is not None and not validator(data): #validator가 있고, validator(data)가 False라면 아래 명령 실행
        raise ValueError("Invalid JSON structure")


def create_backup(path): #백업 파일 생성 함수
    if not os.path.exists(path): #없으면 아무것도 안함
        return

    try:
        shutil.copy2(path, backup_path(path)) #path를 백업 파일 경로로 복사
    except OSError:
        pass


def load_backup_json(path, validator=None): #백업 파일 불러오는 함수
    target_backup_path = backup_path(path)  #해당 경로와 일치하는 백업 파일 경로 가져옴
    if not os.path.exists(target_backup_path): #만약 존재하지 않으면 None 반환
        return None

    try:
        data = read_json(target_backup_path) #백업 파일 읽어서 data에 저장
        validate_json_data(data, validator)  #유효성 검사
        return data
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return None


def preserve_corrupt_file(path): #손상 파일 보존 함수
    if not os.path.exists(path):
        return

    try:
        shutil.move(path, corrupt_path(path)) #원래 파일을 손상 파일 경로에 이동
    except OSError:
        pass


def restore_backup(path): #백업 파일 복원 함수
    target_backup_path = backup_path(path)
    if not os.path.exists(target_backup_path):
        return

    try:
        shutil.copy2(target_backup_path, path) #백업 파일을 원래 파일에 복사
    except OSError:
        pass
