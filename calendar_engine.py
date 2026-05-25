import json
import os
from datetime import date as date_type          #date: 연도, 월, 일 단위의 날짜를 다루는 표준 라이브러리 클래스
from datetime import datetime, time, timedelta


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

    def _period_active_on(self, event, target_date):
        start_date = event["start_date"]
        end_date = event.get("end_date")
        if end_date is None:
            return target_date >= start_date
        return start_date <= target_date <= end_date

    def _timed_occurs_on(self, event, target_date):
        start_date = event["start"].date()
        recurrence = event.get("recurrence", RECURRENCE_NONE)
        recurrence_end = event.get("recurrence_end")

        if target_date < start_date:
            return False
        if recurrence_end is not None and target_date > recurrence_end:
            return False
        if recurrence == RECURRENCE_NONE:
            return target_date == start_date
        if recurrence == RECURRENCE_WEEKLY:
            return (target_date - start_date).days % 7 == 0
        if recurrence == RECURRENCE_MONTHLY:
            return target_date.day == start_date.day
        if recurrence == RECURRENCE_YEARLY:
            return target_date.month == start_date.month and target_date.day == start_date.day
        return False

    def _timed_bounds_on(self, event, target_date):
        start = datetime.combine(target_date, event["start"].time())
        end = start + timedelta(minutes=event["duration"])
        return start, end

    def _iter_candidate_dates(self, start_date, recurrence, recurrence_end=None, max_days=730):
        if recurrence == RECURRENCE_NONE:
            yield start_date
            return

        last_date = recurrence_end or (start_date + timedelta(days=max_days))
        current = start_date
        while current <= last_date:
            fake_event = {
                "start": datetime.combine(start_date, time.min),
                "recurrence": recurrence,
                "recurrence_end": recurrence_end,
            }
            if self._timed_occurs_on(fake_event, current):
                yield current
            current += timedelta(days=1)

    def _time_overlaps(self, start_a, end_a, start_b, end_b):
        return not (end_a <= start_b or start_a >= end_b)

    def _check_timed_conflict(
        self,
        start,
        duration,
        recurrence=RECURRENCE_NONE,
        recurrence_end=None,
        ignore_id=None,
    ):
        for target_date in self._iter_candidate_dates(start.date(), recurrence, recurrence_end):
            new_start = datetime.combine(target_date, start.time())
            new_end = new_start + timedelta(minutes=duration)

            for event in self.events:
                if event.get("type") == "period":
                    continue
                if ignore_id is not None and event["id"] == ignore_id:
                    continue
                if not self._timed_occurs_on(event, target_date):
                    continue

                existing_start, existing_end = self._timed_bounds_on(event, target_date)
                if self._time_overlaps(new_start, new_end, existing_start, existing_end):
                    raise ValueError(f"Event conflict with id={event['id']}")

    def _to_dict(self, event, target_date=None):
        if event.get("type") == "period":
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
            }

        display_date = target_date or event["start"].date()
        recurrence_end = event.get("recurrence_end")
        return {
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
            "recurrence_end": recurrence_end.strftime("%Y-%m-%d") if recurrence_end else None,
        }

    def _save(self):
        data = [self._to_dict(event) for event in self.events]
        with open(self.storage_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _load(self):
        if not os.path.exists(self.storage_path):                 #저장경로가 없으면 pass
            return

        with open(self.storage_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        for item in data:
            if item.get("type") == "period":
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
            })

        self.events.sort(key=self._sort_key)

    def add_event(
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
        start = self._parse_datetime(date, time)
        recurrence = self._normalize_recurrence(recurrence)
        recurrence_end = self._parse_optional_date(recurrence_end)
        if recurrence == RECURRENCE_NONE:
            recurrence_end = None
        if recurrence_end is not None and recurrence_end < start.date():
            raise ValueError("Recurrence end date must be after start date")

        self._check_timed_conflict(start, duration, recurrence, recurrence_end)

        event = {
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
        }

        self.events.append(event)
        self.events.sort(key=self._sort_key)
        self._save()
        return self._to_dict(event)

    def add_period_event(self, title, start_date, end_date=None, tag=None, priority=None, color=None):
        start = self._parse_date(start_date)
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
            return [self._to_dict(event) for event in self.events]

        target_date = self._parse_date(date)
        result = []
        for event in self.events:
            if event.get("type") == "period":
                if self._period_active_on(event, target_date):
                    result.append(self._to_dict(event))
                continue

            if self._timed_occurs_on(event, target_date):
                result.append(self._to_dict(event, target_date))

        result.sort(key=lambda item: (item.get("time") or "00:00", item["title"]))
        return result

    def get_event(self, event_id):
        for event in self.events:
            if event["id"] == event_id:
                return self._to_dict(event)
        raise ValueError("Event not found")

    def delete_event(self, event_id):
        before = len(self.events)
        self.events = [event for event in self.events if event["id"] != event_id]
        if len(self.events) == before:
            raise ValueError("Event not found")

        self._save()
        return True

    def update_event(self, event_id, **kwargs):
        for event in self.events:
            if event["id"] != event_id:
                continue

            if event.get("type") == "period":
                title = kwargs.get("title", event["title"])
                start_date = kwargs.get("start_date", kwargs.get("date", event["start_date"].strftime("%Y-%m-%d")))
                end_date = kwargs.get("end_date", event["end_date"].strftime("%Y-%m-%d") if event.get("end_date") else None)
                start = self._parse_date(start_date)
                end = self._parse_optional_date(end_date)
                if end is not None and end < start:
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
