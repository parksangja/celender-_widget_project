from datetime import datetime, time, timedelta
import json
import os

DEFAULT_EVENT_COLOR = "#2F6FED"


class CalendarEngine:                               #self를 사용하는 이유: 클래스 정의 시 첫번째 매개변수로 반드시 사용되어야 함. 물론 딴거 써도 됨.
    def __init__(self, storage_path="events.json"): #class 실행시 자동으로 불러오는 메소드
        self.events = []                            #입력 받은 이벤트를 담을 리스트
        self.storage_path = storage_path            #저장 경로를 events.json으로 정함
        self._load()                                #실행시, _load() 함수를 실행함

    # ------------------------
    # 내부 유틸
    # ------------------------
    def _generate_id(self):                           #ㅅㅂ 이 함수가 왜 있는거임? 이놈이 이벤트 아이디 생성해서 self값을 정하는건가? -> 이벤트의 id를 정하는 함수인듯?
        if not self.events:                           #리스트가 빈 리스트일때, 함수는 1을 반환한다. 즉 첫번째 이벤트의 id를 1로 정해 반환한다.
            return 1
        return max(e["id"] for e in self.events) + 1  #리스트가 빈 리스트가 아니라면, 이벤트 리스트의 id 중 최댓값에 1을 더해 반환한다.(json파일에서 가져오는듯?) -> 최초 이벤트가 아니라면 기존 이벤트의 id에 1을 더해 id를 정한다

    def _parse_datetime(self, date_str, time_str):                           #날짜와 시간을 가져오는 함수
        return datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M") #이 함수를 호출하면, 받은 이벤트의 날짜와 시간을 출력한다.

    def _parse_date(self, date_str):
        return datetime.strptime(date_str, "%Y-%m-%d").date()

    def _sort_key(self, event):
        if event.get("type") == "period":
            return datetime.combine(event["start_date"], time.min)

        return event["start"]

    def _period_active_on(self, event, target_date):
        start_date = event["start_date"]
        end_date = event.get("end_date")

        if end_date is None:
            return target_date >= start_date

        return start_date <= target_date <= end_date

    def _check_timed_conflict(self, start, end, ignore_id=None):
        for e in self.events:
            if e.get("type") == "period":
                continue
            if ignore_id is not None and e["id"] == ignore_id:
                continue

            if not (end <= e["start"] or start >= e["end"]):
                raise ValueError(f"Event conflict with id={e['id']}")

    def _to_dict(self, event):     #이벤트에 대한 상세정보를 불러오는 함수이며 JSON형식으로 저장된 이벤트의 id, 제목, 날짜 및 시간, 기간, 태그, 우선순위를 불러온다.
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
            }

        return {                   #이벤트는 딕셔너리 형태로 반환함.
            "id": event["id"],
            "type": "timed",
            "title": event["title"],
            "date": event["start"].strftime("%Y-%m-%d"),
            "time": event["start"].strftime("%H:%M"),
            "duration": event["duration"],
            "tag": event.get("tag"),
            "priority": event.get("priority"),
            "color": event.get("color", DEFAULT_EVENT_COLOR),
        }

    def _save(self):                                              #self값을 받아와 그 값에 해당하는 이벤트를 저장하는 함수
        data = [self._to_dict(e) for e in self.events]            #data = 이벤트 파일 안에 있는 이벤트를 가져와 함수 _to_dict에 넣고 반환된 값 
        with open(self.storage_path, "w", encoding="utf-8") as f: #이벤트를 주어진 경로를 따라 한글로 열어 아래 명령이 끝나면 닫음 (tq w가 왜있는거임?)
            json.dump(data, f, ensure_ascii=False, indent=2)      #저장 파일이 json형식이기에. json모듈 명령어인 dump를 사용해 data를 파일로 저장함. 

    def _load(self):
        if not os.path.exists(self.storage_path):                  #만약 실행 시 컴퓨터에 저장 경로가 존재하지 않다면, 아무것도 반환하지 않는다.
            return
        with open(self.storage_path, "r", encoding="utf-8") as f:  #저장 경로가 존재하면, 저장 경로를 한글로 받아와 열고 아래 명령을 실행 후 닫는다.
            data = json.load(f)                                    #data = 저장한 json파일 (f는 아마 _save()함수에 있는 f아닐까?)
            for d in data:                                         #data 파일 속 요소에 대해 반복
                if d.get("type") == "period":
                    self.events.append({
                        "id": d["id"],
                        "type": "period",
                        "title": d["title"],
                        "start_date": self._parse_date(d.get("start_date", d["date"])),
                        "end_date": self._parse_date(d["end_date"]) if d.get("end_date") else None,
                        "tag": d.get("tag"),
                        "priority": d.get("priority"),
                        "color": d.get("color", DEFAULT_EVENT_COLOR),
                    })
                    continue

                start = self._parse_datetime(d["date"], d["time"]) #start = _parse_datetime()함수를 실행해 가져온 날과 시간
                self.events.append({                               #프로그램 실행 시 가져온 events 라는 리스트에 추가함. (start, end 제외하면 json파일이랑 거의 비슷하게 추가함.)
                    "id": d["id"],
                    "type": "timed",
                    "title": d["title"],
                    "start": start,                                  #start는 위에 있는 지역 변수 가져옴
                    "end": start + timedelta(minutes=d["duration"]), #끝은 시작에 timedelta 함수를 써서, 지속시간을 더한다.
                    "duration": d["duration"],
                    "tag": d.get("tag"),
                    "priority": d.get("priority"),
                    "color": d.get("color", DEFAULT_EVENT_COLOR),
                })

    # ------------------------
    # 핵심 기능
    # ------------------------

    def add_event(self, title, date, time, duration=60, tag=None, priority=None, color=None): #이벤트 저장 함수
        start = self._parse_datetime(date, time)                                  #시작 시간은 받아온 날짜와 시간을 _parse_datetime에 맞추어 정함
        end = start + timedelta(minutes=duration)                                 #끝나는 시간은 duration을 시작시간에 timedelta를 이용해 더해서 정함

        self._check_timed_conflict(start, end)
            
        event = {                                                      #충돌검사 통과시, 저장 형식에 맞추어 저장
            "id": self._generate_id(), 
            "type": "timed",
            "title": title,
            "start": start,
            "end": end,
            "duration": duration,
            "tag": tag,
            "priority": priority,
            "color": color or DEFAULT_EVENT_COLOR,
        }

        self.events.append(event)
        self.events.sort(key=self._sort_key)       #시작시간 순서로 이벤트 정렬
        self._save()                               #정렬 후 저장

        return self._to_dict(event)

    def add_period_event(self, title, start_date, end_date=None, tag=None, priority=None, color=None):
        start = self._parse_date(start_date)
        end = self._parse_date(end_date) if end_date else None

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

    def list_events(self, date=None):                                #이벤트 리스트 반환 함수
        if date:
            target_date = self._parse_date(date)                    #만약 찾는 날이 있다면,
            result = [                                               #그 날에 있는 이벤트들을 반환
                self._to_dict(e)                                     #이벤트들을 _to_dict 함수를 거쳐 딕셔너리 형태로 만듬
                for e in self.events
                if (
                    e.get("type") == "period" and self._period_active_on(e, target_date)
                ) or (
                    e.get("type") != "period" and e["start"].date() == target_date
                )
            ]
        else:
            result = [self._to_dict(e) for e in self.events]         #찾는 날이 없다면 전체 일정 반환

        return result

    def delete_event(self, event_id):                                 #이벤트 삭제 함수
        before = len(self.events)
        self.events = [e for e in self.events if e["id"] != event_id] #삭제할 이벤트의 id와 다른 이벤트는 남김, 같다면 남기지 않음

        if len(self.events) == before:                                #이벤트 삭제 검사
            raise ValueError("Event not found")                       #만약 삭제 전 이벤트와 개수가 같다면 오류 알리기

        self._save()
        return True

    def get_event(self, event_id):
        for e in self.events:
            if e["id"] == event_id:
                return self._to_dict(e)

        raise ValueError("Event not found")

    def update_event(self, event_id, **kwargs):                             #이벤트 수정 함수
        for e in self.events:
            if e["id"] == event_id:                                         #수정할 이벤트의 id와 같은 이벤트 발견 시, **kwargs로 받아와 수정할 값만 수정
                if e.get("type") == "period":
                    title = kwargs.get("title", e["title"])
                    start_date = kwargs.get("start_date", kwargs.get("date", e["start_date"].strftime("%Y-%m-%d")))
                    end_date = kwargs.get("end_date", e["end_date"].strftime("%Y-%m-%d") if e.get("end_date") else None)
                    start = self._parse_date(start_date)
                    end = self._parse_date(end_date) if end_date else None

                    if end is not None and end < start:
                        raise ValueError("Period end date must be after start date")

                    e["title"] = title
                    e["start_date"] = start
                    e["end_date"] = end
                    e["tag"] = kwargs.get("tag", e.get("tag"))
                    e["priority"] = kwargs.get("priority", e.get("priority"))
                    e["color"] = kwargs.get("color", e.get("color", DEFAULT_EVENT_COLOR))
                    self.events.sort(key=self._sort_key)
                    self._save()
                    return self._to_dict(e)

                title = kwargs.get("title", e["title"])
                date = kwargs.get("date", e["start"].strftime("%Y-%m-%d"))
                time = kwargs.get("time", e["start"].strftime("%H:%M"))
                duration = kwargs.get("duration", e["duration"])
                tag = kwargs.get("tag", e.get("tag"))
                priority = kwargs.get("priority", e.get("priority"))
                color = kwargs.get("color", e.get("color", DEFAULT_EVENT_COLOR))
                start = self._parse_datetime(date, time)
                end = start + timedelta(minutes=duration)

                self._check_timed_conflict(start, end, ignore_id=event_id)

                e["title"] = title
                e["start"] = start
                e["end"] = end
                e["duration"] = duration
                e["tag"] = tag
                e["priority"] = priority
                e["color"] = color
                self.events.sort(key=self._sort_key)
                self._save()
                return self._to_dict(e)

        raise ValueError("Event not found")                                  #찾는 이벤트의 id가 없다면 오류 알림
