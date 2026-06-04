##엔진은 그저 데이터 처리를 위해 존재함/
#
import calendar
import os
from datetime import date as date_type          #date: 연도, 월, 일 단위의 날짜를 다루는 표준 라이브러리 클래스
from datetime import datetime, time, timedelta

from data_safety import load_json_safely, save_json_safely #파일 께짐을 방지하기 위해 가져옴


DEFAULT_EVENT_COLOR = "#2F6FED" #기본적인 일정 색상, 달력에 막대기로 표시할 때 이 색상 사용
RECURRENCE_NONE = "none"          #반복 없는 설정
RECURRENCE_WEEKLY = "weekly"      #매주 반복 설정
RECURRENCE_MONTHLY = "monthly"    #매달 반복 설정
RECURRENCE_YEARLY = "yearly"      #매년 반복 설정
VALID_RECURRENCES = {             #유효 반복 설정 목록
    RECURRENCE_NONE,
    RECURRENCE_WEEKLY,
    RECURRENCE_MONTHLY,
    RECURRENCE_YEARLY,
}


class CalendarEngine:                               #엔진 클래스 정의
    def __init__(self, storage_path="events.json"): #클래스 불러올 때 자동 실행, 저장경로는 events.json으로 설정(파일이 없으면 새로 생성)
        self.events = []
        self.storage_path = storage_path
        self._load()

    def _generate_id(self): #이벤트 id 생성 함수
        if not self.events: #첫 이벤트는 id를 1로 지정
            return 1
        return max(event["id"] for event in self.events) + 1 #기존 이벤트의 id에 1씩 더해서 id지정

    def _parse_datetime(self, date_str, time_str):  #받은 날짜와 시간을 datetime 객체로 변환해 반환
        return datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")

    def _parse_date(self, date_str): #받은 날짜와 시간 중 날짜만 datetime 객체로 변환해 .date()로 날짜 반환(시간까지 받는지는 모르겠음)
        return datetime.strptime(date_str, "%Y-%m-%d").date()

    def _parse_optional_date(self, date_str):
        if not date_str:                   #받은 날짜가 문자열이 아니라면 None 반환
            return None
        if isinstance(date_str, datetime): #받은 날짜가 datetime 객체라면 .date()로 날짜 반환
            return date_str.date()
        if isinstance(date_str, date_type):#받은 날짜가 date 객체라면 그대로 반환(위에 as date_type로 date 클래스 불러왔음)
            return date_str
        return self._parse_date(date_str)  #모든 조건문에 걸리지 않으면 _parse_date() 함수로 날짜 반환

    def _normalize_recurrence(self, recurrence):                  #반복 설정 함수
        recurrence = recurrence or RECURRENCE_NONE                #반복 설정을 받아온 반복 설정이나 반복하지 않음으로 설정(or은 왼쪽 값이 '비어있음'으로 판단하면 오른쪽 값 사용)
        if recurrence not in VALID_RECURRENCES:
            raise ValueError(f"Invalid recurrence: {recurrence}") #반복 설정이 유효 반복 설정 목록에 없으면 예외 처리
        return recurrence

    def _sort_key(self, event):
        if event.get("type") == "period": #이벤트의 타입이 기간이면 시작 날짜와 최소 시간을 합쳐 datetime 객체로 반환
            return datetime.combine(event["start_date"], time.min)
        return event["start"]              #이벤트의 타입이 기간이 아니면 시작 datetime 객체 반환

    def _period_active_on(self, event, target_date): #기간 이벤트가 특정 날에 활성화 되어있는지 확인하는 함수
        start_date = event["start_date"]
        end_date = event.get("end_date")
        if end_date is None:                         #무기한 기간 일정 확인
            return target_date >= start_date
        return start_date <= target_date <= end_date #기간 일정 확인

    def _timed_occurs_on(self, event, target_date):           #목표 날짜가 이벤트 기간에 포함되는지 판단하는 함수
        start_date = event["start"].date()
        recurrence = event.get("recurrence", RECURRENCE_NONE) #반복 있으면 가져오고 없으면 NONE으로 가져옴(get이용해서 오류 방지)
        recurrence_end = event.get("recurrence_end")
        target_date_str = target_date.strftime("%Y-%m-%d")

        if target_date < start_date:
            return False
        if recurrence_end is not None and target_date > recurrence_end:
            return False
        if target_date_str in event.get("recurrence_skips", set()): #반복 스킵
            return False
        if target_date_str in event.get("recurrence_overrides", {}): #반복 일정 중 수정한 날짜
            return False
        if recurrence == RECURRENCE_NONE:
            return target_date == start_date
        if recurrence == RECURRENCE_WEEKLY:
            return (target_date - start_date).days % 7 == 0
        if recurrence == RECURRENCE_MONTHLY:
            return self._monthly_occurs_on(start_date, target_date)
        if recurrence == RECURRENCE_YEARLY:
            return target_date.month == start_date.month and target_date.day == start_date.day
        return False

    def _monthly_occurs_on(self, start_date, target_date): #매월 반복하는 일정에 해당 날짜가 포함되는지 확인하는 함수
        if target_date.day == start_date.day: #날짜가 같으면 True
            return True
        
        #날짜가 다른 경우 아래 조건문의 결과 반환
        return self._is_last_day_of_month(start_date) and self._is_last_day_of_month(target_date)

    def _is_last_day_of_month(self, date_obj): #어떤 날이 달의 마지막 날짜인지 확인하는 함수
        return date_obj.day == calendar.monthrange(date_obj.year, date_obj.month)[1]

    def _timed_bounds_on(self, event, target_date):                  #이벤트의 시작과 끝을 계산하여 반환하는 함수
        start = datetime.combine(target_date, event["start"].time())
        end = start + timedelta(minutes=event["duration"])           #하루만 진행하는 이벤트의 지속시간을 받아 끝 계산
        return start, end

    def _override_bounds(self, override):  #반복 일정 중 수정한 날짜의 시작과 끝을 계산하여 반환하는 함수
        start = self._parse_datetime(override["date"], override["time"])
        end = start + timedelta(minutes=override["duration"])
        return start, end

    def _timed_occurrences_on(self, event, target_date): #어떤 이벤트가 특정 날짜에 발생하는 모든 경우를 반복 스킵과 수정을 고려해서 생성하는 함수
        target_date_str = target_date.strftime("%Y-%m-%d")

        for occurrence_date, override in event.get("recurrence_overrides", {}).items():
            if override["date"] != target_date_str:
                continue

            start, end = self._override_bounds(override) #만약 반복 일정 중 수정한 날짜에 대해서 시작시, 끝시간을 구함
            yield {
                "occurrence_date": occurrence_date,
                "start": start,
                "end": end,
                "override": override,
            }                                            #수정 날짜에 대해 딕셔너리 생산 후 반환

        if self._timed_occurs_on(event, target_date):
            start, end = self._timed_bounds_on(event, target_date)
            yield {
                "occurrence_date": target_date_str,
                "start": start,
                "end": end,
                "override": None,
            }

    def _iter_candidate_dates(self, start_date, recurrence, recurrence_end=None, max_days=730):
        if recurrence == RECURRENCE_NONE:   #반복 없으면 시작 날짜 생산해 반환
            yield start_date
            return

        last_date = recurrence_end or (start_date + timedelta(days=max_days))
        current = start_date
        while current <= last_date:                             #현재 날짜가 마지막 날짜보다 작거나 같을 때까지 반복
            fake_event = {
                "start": datetime.combine(start_date, time.min),
                "recurrence": recurrence,
                "recurrence_end": recurrence_end,
            }
            if self._timed_occurs_on(fake_event, current):      #현재 날짜에 이벤트가 발생하는지 확인해서 맞으면 현재 날짜 생산해 반환
                yield current
            current += timedelta(days=1)                        #아니면 현재 날짜에 하루 더해서 다음 날짜로 넘어감

    def _time_overlaps(self, start_a, end_a, start_b, end_b):   #시작시간, 끝 시간이 겹치거나 오버되는지 확인하는 함수
        return not (end_a <= start_b or start_a >= end_b)

    def _check_timed_conflict(         #시간 충돌 감지 함수
        self,
        start,
        duration,
        recurrence=RECURRENCE_NONE,
        recurrence_end=None,
        ignore_id=None,
    ):
        for target_date in self._iter_candidate_dates(start.date(), recurrence, recurrence_end): #반복 설정에 따라 발생할 수 있는 날짜들을 순회하면서 충돌 검사
            new_start = datetime.combine(target_date, start.time())
            new_end = new_start + timedelta(minutes=duration)

            for event in self.events:
                if event.get("type") == "period":   #지속 이벤트가 아닌 기간 이벤트면 패스
                    continue
                if ignore_id is not None and event["id"] == ignore_id:  #업데이트 시 자기 자신과의 충돌은 무시하도록 설정되어 있으면 패스
                    continue
                for occurrence in self._timed_occurrences_on(event, target_date):
                    existing_start = occurrence["start"]
                    existing_end = occurrence["end"]
                    if self._time_overlaps(new_start, new_end, existing_start, existing_end):   #만약 시작시간과 끝시간이 겹치면 예외처리
                        raise ValueError(f"Event conflict with id={event['id']}")

    def _to_dict(self, event, target_date=None, occurrence_date=None, override=None):            #이벤트를 딕셔너리로 반환하는 함수
        if event.get("type") == "period":                   #기간 이벤트라면 아래 형태로 반환
            end_date = event.get("end_date")
            return {
                "id": event["id"],
                "type": "period",
                "title": event["title"],
                "date": event["start_date"].strftime("%Y-%m-%d"),
                "start_date": event["start_date"].strftime("%Y-%m-%d"),
                "end_date": end_date.strftime("%Y-%m-%d") if end_date else None,
                "time": None,
                "duration": None,
                "tag": event.get("tag"),
                "priority": event.get("priority"),
                "color": event.get("color", DEFAULT_EVENT_COLOR),
                "recurrence": RECURRENCE_NONE,
                "recurrence_end": None,
                "occurrence_date": None,
                "is_override": False,
            }

        if override is not None:                    #반복 일정 중 수정한 날짜라면 아래 형태로 반환
            recurrence_end = event.get("recurrence_end")
            return {
                "id": event["id"],
                "type": "timed",
                "title": override.get("title", event["title"]),
                "date": override["date"],
                "time": override["time"],
                "duration": override["duration"],
                "tag": override.get("tag", event.get("tag")),
                "priority": override.get("priority", event.get("priority")),
                "color": override.get("color", event.get("color", DEFAULT_EVENT_COLOR)),
                "recurrence": event.get("recurrence", RECURRENCE_NONE),
                "recurrence_end": recurrence_end.strftime("%Y-%m-%d") if recurrence_end else None,
                "occurrence_date": occurrence_date,
                "is_override": True,
            }

        display_date = target_date or event["start"].date() #목표 날짜가 있으면 목표 날짜로, 없으면 이벤트의 시작 날짜로 표시 날짜 설정
        recurrence_end = event.get("recurrence_end")        #지속 이벤트의 반복 종료 날짜 가져오기
        return {                                            #지속 이벤트는 아래 형식으로 반환
            "id": event["id"],
            "type": "timed",
            "title": event["title"],
            "date": display_date.strftime("%Y-%m-%d"),
            "time": event["start"].strftime("%H:%M"),
            "duration": event["duration"],
            "tag": event.get("tag"),
            "priority": event.get("priority"),
            "color": event.get("color", DEFAULT_EVENT_COLOR),
            "recurrence": event.get("recurrence", RECURRENCE_NONE),
            "recurrence_end": recurrence_end.strftime("%Y-%m-%d") if recurrence_end else None, #지속이벤트의 끝을 받았다면 그걸로, 아니면 무기한으로 설정
            "occurrence_date": display_date.strftime("%Y-%m-%d"),
            "is_override": False,
            "recurrence_skips": sorted(event.get("recurrence_skips", set())),  #여러 날짜에 대해 스킵을 처리, 동일한 날짜에 여러번 스킵 명령을 넣어도 set으로 중복 제거
            "recurrence_overrides": event.get("recurrence_overrides", {}),
        }

    def _save(self):                                                #이벤트 저장 함수
        data = [self._to_dict(event) for event in self.events]      #이벤트 리스트 속 이벤트를 딕셔너리 형태로 변환해서 리스트에 저장
        save_json_safely(self.storage_path, data)                   #임시 파일 저장 + 기존 파일 백업 후 안전하게 교체

    def _load(self):
        if not os.path.exists(self.storage_path):                 #저장경로가 없으면 pass
            return

        data = load_json_safely(self.storage_path, [], validator=lambda value: isinstance(value, list))

        for item in data:
            try:
                if item.get("type") == "period":                      #이벤트 타입이 기간이라면 아래 형식으로 events 리스트에 추가
                    self.events.append({
                        "id": item["id"],
                        "type": "period",
                        "title": item["title"],
                        "start_date": self._parse_date(item.get("start_date", item["date"])),
                        "end_date": self._parse_optional_date(item.get("end_date")),
                        "tag": item.get("tag"),
                        "priority": item.get("priority"),
                        "color": item.get("color", DEFAULT_EVENT_COLOR),
                    })
                    continue
                #이벤트 타입이 지속이라면 아래 형식으로 events 리스트에 추가
                start = self._parse_datetime(item["date"], item["time"])
                recurrence = self._normalize_recurrence(item.get("recurrence"))
                recurrence_end = self._parse_optional_date(item.get("recurrence_end"))
                self.events.append({
                    "id": item["id"],
                    "type": "timed",
                    "title": item["title"],
                    "start": start,
                    "end": start + timedelta(minutes=item.get("duration", 60)),
                    "duration": item.get("duration", 60),
                    "tag": item.get("tag"),
                    "priority": item.get("priority"),
                    "color": item.get("color", DEFAULT_EVENT_COLOR),
                    "recurrence": recurrence,
                    "recurrence_end": recurrence_end,
                    "recurrence_skips": set(item.get("recurrence_skips", [])),
                    "recurrence_overrides": item.get("recurrence_overrides", {}),
                })
            except (KeyError, TypeError, ValueError):
                continue

        self.events.sort(key=self._sort_key) #시작시간 기준으로 이벤트 정렬

    def add_event( #이벤트 추가 함수(하루 일정 또는 반복 일정)
        self,
        title,
        date,
        time,
        duration=60,
        tag=None,
        priority=None,
        color=None,
        recurrence=RECURRENCE_NONE,
        recurrence_end=None,
    ):
        start = self._parse_datetime(date, time)                    #받은 시간과 날짜를 datetime 객체로 변환해서 시작 시간 설정
        recurrence = self._normalize_recurrence(recurrence)         #받은 반복 설정을 일반화해 저장
        recurrence_end = self._parse_optional_date(recurrence_end)  #끝시간도 마찬가지로 함수 통해 datetime 객체로 변환해서 저장
        if recurrence == RECURRENCE_NONE:                           #반복이 없다면 반복 종료 시간을 None으로 설정
            recurrence_end = None
        if recurrence_end is not None and recurrence_end < start.date(): #반복 종료 날짜가 시작 날짜보다 빠르면 예외 처리
            raise ValueError("Recurrence end date must be after start date")

        self._check_timed_conflict(start, duration, recurrence, recurrence_end) #충돌 검사 실행

        event = {                                       #충돌 검사 통과 시, 이벤트 딕셔너리 생성
            "id": self._generate_id(),
            "type": "timed",
            "title": title,
            "start": start,
            "end": start + timedelta(minutes=duration),
            "duration": duration,
            "tag": tag,
            "priority": priority,
            "color": color or DEFAULT_EVENT_COLOR,
            "recurrence": recurrence,
            "recurrence_end": recurrence_end,
            "recurrence_skips": set(),
            "recurrence_overrides": {},
        }

        self.events.append(event)                       #생성한 이벤트를 events 리스트에 추가 후, 정렬 및 파일에 저장
        self.events.sort(key=self._sort_key)
        self._save()
        return self._to_dict(event)                     #생성한 이벤트를 딕셔너리 형태로 반환

    def add_period_event(self, title, start_date, end_date=None, tag=None, priority=None, color=None): #기간 이벤트 추가 함수
        start = self._parse_date(start_date)        #시작 날짜와 끝 날짜를 각각 함수로 datetime 객체로 변환해서 저장
        end = self._parse_optional_date(end_date)
        if end is not None and end < start:
            raise ValueError("Period end date must be after start date")

        event = {
            "id": self._generate_id(),
            "type": "period",
            "title": title,
            "start_date": start,
            "end_date": end,
            "tag": tag,
            "priority": priority,
            "color": color or DEFAULT_EVENT_COLOR,
        }

        self.events.append(event)
        self.events.sort(key=self._sort_key)
        self._save()
        return self._to_dict(event)

    def list_events(self, date=None):
        if date is None:
            return [self._to_dict(event) for event in self.events] #날짜가 지정되지 않으면 모든 이벤트를 딕셔너리 형태로 반환

        target_date = self._parse_date(date)                       #날짜가 지정되면 해당 날짜를 타겟으로 정해 datetime 객체로 변환해서 저장
        result = []
        for event in self.events:
            if event.get("type") == "period":                       #만약 기간 이벤트라면,
                if self._period_active_on(event, target_date):      #포남 날짜가 기간에 포함되면 result에 이벤트 추가
                    result.append(self._to_dict(event))
                continue

            for occurrence in self._timed_occurrences_on(event, target_date):
                result.append(
                    self._to_dict(
                        event,
                        occurrence["start"].date(),
                        occurrence["occurrence_date"],
                        occurrence["override"],
                    )
                )

        result.sort(key=lambda item: (item.get("time") or "00:00", item["title"])) #result를 시간과 제목 기준으로 정렬
        return result

    def get_event(self, event_id):          #이벤트 id 가지고 이벤트를 찾는 함수
        for event in self.events:
            if event["id"] == event_id:
                return self._to_dict(event)
        raise ValueError("Event not found")

    def delete_event(self, event_id):       #이벤트 id 가지고 이벤트를 삭제하는 함수
        before = len(self.events)
        self.events = [event for event in self.events if event["id"] != event_id]
        if len(self.events) == before:      #이벤트 길이로 제대로 삭제되었는지 확인
            raise ValueError("Event not found")

        self._save()
        return True

    def update_event(self, event_id, **kwargs): #이벤트 업데이트 함수(keyword arguments로 업데이트할 키워드와 값을 받음)
        for event in self.events:               #업데이트 할 이벤트의 id와 일치하는 이벤트 찾기
            if event["id"] != event_id:
                continue
                                                #위 조건문 통과 시 아래 업데이트 과정 실행
            if event.get("type") == "period":   #만약 기간 이벤트라면 받은 키워드와 값으로 딕셔너리 형태의 이벤트 업데이트
                title = kwargs.get("title", event["title"])
                start_date = kwargs.get("start_date", kwargs.get("date", event["start_date"].strftime("%Y-%m-%d")))
                end_date = kwargs.get("end_date", event["end_date"].strftime("%Y-%m-%d") if event.get("end_date") else None)
                start = self._parse_date(start_date)
                end = self._parse_optional_date(end_date)
                if end is not None and end < start: #충돌 검사
                    raise ValueError("Period end date must be after start date")

                event["title"] = title
                event["start_date"] = start
                event["end_date"] = end
                event["tag"] = kwargs.get("tag", event.get("tag"))
                event["priority"] = kwargs.get("priority", event.get("priority"))
                event["color"] = kwargs.get("color", event.get("color", DEFAULT_EVENT_COLOR))
                self.events.sort(key=self._sort_key)
                self._save()
                return self._to_dict(event)
            #기간 이벤트가 아니라면 아래 형식에 따라 업데이트
            title = kwargs.get("title", event["title"])
            date = kwargs.get("date", event["start"].strftime("%Y-%m-%d"))
            time_text = kwargs.get("time", event["start"].strftime("%H:%M"))
            duration = kwargs.get("duration", event["duration"])
            tag = kwargs.get("tag", event.get("tag"))
            priority = kwargs.get("priority", event.get("priority"))
            color = kwargs.get("color", event.get("color", DEFAULT_EVENT_COLOR))
            recurrence = self._normalize_recurrence(kwargs.get("recurrence", event.get("recurrence", RECURRENCE_NONE)))
            recurrence_end = self._parse_optional_date(kwargs.get("recurrence_end", event.get("recurrence_end")))
            start = self._parse_datetime(date, time_text)
            if recurrence == RECURRENCE_NONE:
                recurrence_end = None
            if recurrence_end is not None and recurrence_end < start.date():
                raise ValueError("Recurrence end date must be after start date")

            self._check_timed_conflict(start, duration, recurrence, recurrence_end, ignore_id=event_id)

            event["title"] = title
            event["start"] = start
            event["end"] = start + timedelta(minutes=duration)
            event["duration"] = duration
            event["tag"] = tag
            event["priority"] = priority
            event["color"] = color
            event["recurrence"] = recurrence
            event["recurrence_end"] = recurrence_end
            self.events.sort(key=self._sort_key)
            self._save()
            return self._to_dict(event)

        raise ValueError("Event not found")

    def skip_occurrence(self, event_id, occurrence_date): #반복 일정 중 스킵한 날짜 처리 함수
        event = self._find_timed_event(event_id)
        occurrence_date_obj = self._parse_date(occurrence_date)
        occurrence_date_str = occurrence_date_obj.strftime("%Y-%m-%d")

        if not self._occurrence_exists(event, occurrence_date_obj): #스킵할 이벤트 날짜가 반복 일정에 존재하지 않으면 예외 처리
            raise ValueError("Occurrence not found")

        event.setdefault("recurrence_skips", set()).add(occurrence_date_str)
        event.setdefault("recurrence_overrides", {}).pop(occurrence_date_str, None)
        self._save()
        return self._to_dict(event, occurrence_date_obj)

    def update_occurrence(self, event_id, occurrence_date, **kwargs):  #반복 일정에 대해 스킵이나 수정한 날짜 업데이트 함수
        event = self._find_timed_event(event_id)
        occurrence_date_obj = self._parse_date(occurrence_date)
        occurrence_date_str = occurrence_date_obj.strftime("%Y-%m-%d")

        if not self._occurrence_exists(event, occurrence_date_obj):    #업데이트할 이벤트 날짜가 반복 일정에 존재하지 않으면 예외 처리
            raise ValueError("Occurrence not found")

        current = self._to_dict(event, occurrence_date_obj)
        date = kwargs.get("date", current["date"])
        time_text = kwargs.get("time", current["time"])
        duration = kwargs.get("duration", current["duration"])
        start = self._parse_datetime(date, time_text)

        self._check_timed_conflict( #업데이트한 날짜와 시간, 지속시간, 반복 설정에 따라 충돌 검사
            start,
            duration,
            RECURRENCE_NONE,
            None,
            ignore_id=event_id,
        )

        override = {                #충돌검사 통과 시, 수정된 날짜에 대해 딕셔너리 형태로 override 생성
            "title": kwargs.get("title", current["title"]),
            "date": date,
            "time": time_text,
            "duration": duration,
            "tag": kwargs.get("tag", current.get("tag")),
            "priority": kwargs.get("priority", current.get("priority")),
            "color": kwargs.get("color", current.get("color", DEFAULT_EVENT_COLOR)),
        }

        event.setdefault("recurrence_skips", set()).discard(occurrence_date_str)    #업데이트한 날짜가 스킵된 날짜 목록에 있으면 제거
        event.setdefault("recurrence_overrides", {})[occurrence_date_str] = override
        self._save()
        return self._to_dict(event, self._parse_date(date), occurrence_date_str, override)

    def update_recurrence_end(self, event_id, recurrence_end):  #반복 일정의 종료 날짜 업데이트 함수
        event = self._find_timed_event(event_id)
        recurrence_end = self._parse_optional_date(recurrence_end)

        if event.get("recurrence", RECURRENCE_NONE) == RECURRENCE_NONE:
            raise ValueError("Event is not recurring")
        if recurrence_end is not None and recurrence_end < event["start"].date():
            raise ValueError("Recurrence end date must be after start date")

        event["recurrence_end"] = recurrence_end
        self._save()
        return self._to_dict(event)

    def _find_timed_event(self, event_id): #기간이나 반복 이벤트가 아닌 이벤트를 찾는 함수
        for event in self.events:
            if event["id"] == event_id and event.get("type") != "period":
                return event
        raise ValueError("Event not found")

    def _occurrence_exists(self, event, occurrence_date): #어떤 이벤트가 반복 날짜에 속하는지 판단하는 함수
        occurrence_date_str = occurrence_date.strftime("%Y-%m-%d")
        if occurrence_date_str in event.get("recurrence_overrides", {}):
            return True
        if occurrence_date_str in event.get("recurrence_skips", set()):
            return True
        #만약 위 조건문을 다 통과했다면 테스트 이벤트를 만들어 반복 날짜에 발생하는지 확인해서 결과 반환
        fake_event = dict(event)
        fake_event["recurrence_skips"] = set()
        fake_event["recurrence_overrides"] = {}
        return self._timed_occurs_on(fake_event, occurrence_date)
