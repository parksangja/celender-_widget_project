#명령 실행 파일
#파서가 만든 명령을 엔진에 연결하기 위해 존재함. 이벤트 추가, 삭제, 목록 확인 명령을 실행
from datetime import datetime

def _require_fields(command, fields): #명령에 field가 없으면 예외 처리
    missing = [field for field in fields if field not in command] #단점은 key는 있지만, 그 값이 None인 경우는 거르지 못함.
    if missing:
        raise ValueError(f"Missing command fields: {', '.join(missing)}")


def _clean_condition(condition): #조건에 None이 들어오면 에러가 나지 않게 무시하는 함수
    cleaned = {}
    for key, value in dict(condition or {}).items():
        if value is None: #None이면 cleaned에 넣지 않기
            continue
        if isinstance(value, str):
            value = value.strip()
            if not value: #공백을 벗기면 공백일때 cleaned에 넣지 않기
                continue
        cleaned[key] = value
    return cleaned


def _matches_condition(event, condition): #실제 이벤트와 입력 받은 조건이 일치하는지 검사
    condition = _clean_condition(condition)

    if "date" in condition:
        if event.get("type") == "period": #기간 이벤트면 우선 시간 충돌 검사
            target_date = datetime.strptime(condition["date"], "%Y-%m-%d").date()
            start_date = datetime.strptime(event["start_date"], "%Y-%m-%d").date()
            end_date = datetime.strptime(event["end_date"], "%Y-%m-%d").date() if event.get("end_date") else None

            if target_date < start_date:
                return False
            if end_date is not None and target_date > end_date:
                return False
        elif event["date"] != condition["date"]:
            return False

    if "time" in condition and event["time"] != condition["time"]:
        return False

    if "title" in condition and condition["title"] not in event["title"]:
        return False

    return True


def _find_first_event(engine, condition): #조건에 맞는 이벤트들 뽑아 그 이벤트 중 첫번째 이벤트를 반환하는 함수
    condition = _clean_condition(condition)
    events = engine.list_events(condition.get("date"))
    targets = [event for event in events if _matches_condition(event, condition)]
    if not targets:
        raise ValueError("Matching event not found")

    return targets[0]


def execute(command, engine): #실행 함수
    action = command.get("action")

    if action == "add":                                     #명령 행동이 add면 _require_fields() 함수에 따라 검사 후 명령 실행
        _require_fields(command, ["title", "date", "time"])
        return engine.add_event(                            #engine에는 calendar_engine.py에 있는 CalendarEngine클래스가 들어감(main.py 참조)
            command["title"],
            command["date"],
            command["time"],
            command.get("duration", 60),
            command.get("tag"),
            command.get("priority"),
            command.get("color"),
            command.get("recurrence", "none"),
            command.get("recurrence_end"),
        )

    if action == "add_period":
        _require_fields(command, ["title", "start_date"])
        return engine.add_period_event(
            command["title"],
            command["start_date"],
            command.get("end_date"),
            command.get("tag"),
            command.get("priority"),
            command.get("color"),
        )

    if action == "list":                                    #명령 행동이 list면 이벤트 리스트 반환
        return engine.list_events(command.get("date"))

    if action == "delete":                                  #명령 행동이 delete면, 우선 조건 검사(모든 이벤트 삭제를 막기 위해서임)
        condition = _clean_condition(command.get("condition", {}))
        if not condition:                                   #날짜나 시간, 제목같은 조건이 없다면 에외 처리
            raise ValueError("Delete condition is required")

        events = engine.list_events()
        targets = [e for e in events if _matches_condition(e, condition)] #_matches_condition() 함수에 따라 condition검사 및 그에 맞는 이벤트를 찾아 targets라는 리스트에 추가

        for t in targets:
            engine.delete_event(t["id"])                                  #targets 이벤트들에 있는 id에 따라 삭제

        return targets                                                    #삭제한 이벤트 반환

    if action == "skip_occurrence": #명령 행동이 반복 스킵이면 아래 명령 실행
        _require_fields(command, ["occurrence_date", "condition"]) #명령에서 스킵할 날짜와 조건을 검사함
        condition = _clean_condition(command.get("condition"))     #조건을 뽑아 딕셔너리로 만들거나, 조건이 없거나 비어있으면 빈 딕셔너리로 만듬
        condition.setdefault("date", command["occurrence_date"])   #'date'에 해당하는 값을 찾고, 없다면 'date'키를 만들고 값으로 command["occurrence_date"]를 넣음
        target = _find_first_event(engine, condition)              #조건에 맞는 첫번째 날짜 찾음
        return engine.skip_occurrence(target["id"], target.get("occurrence_date") or command["occurrence_date"])

    if action == "update_occurrence": #명령이 반복 업데이트면 아래 수행
        _require_fields(command, ["occurrence_date", "condition", "updates"]) #명령에서 업데이트 할 날짜, 조건, 업데이트 내용을 검사함
        condition = _clean_condition(command.get("condition"))
        condition.setdefault("date", command["occurrence_date"])
        target = _find_first_event(engine, condition)
        return engine.update_occurrence( #업데이트 할 이벤트의 id와 날짜, 내용을 엔진에 넣어 정보 처리
            target["id"],
            target.get("occurrence_date") or command["occurrence_date"],
            **command.get("updates", {}),
        )

    if action == "update_recurrence_end": #명령이 반복 종료일 업데이트면 아래 명령 실행
        _require_fields(command, ["condition", "recurrence_end"]) #명령에서 조건과 반복 종료일 검사
        condition = _clean_condition(command.get("condition")) #조건은 명령에서 가져온 조건이거나 조건이 None이면 빈 딕셔너리로 함
        if not condition:
            raise ValueError("Update condition is required")
        target = _find_first_event(engine, condition)
        return engine.update_recurrence_end(target["id"], command.get("recurrence_end"))

    raise ValueError(f"Unknown action: {action}")
