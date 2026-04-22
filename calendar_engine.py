from datetime import datetime, timedelta
import json
import os


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
        return max(e["id"] for e in self.events) + 1  #리스트가 빈 리스트가 아니라면, 이벤트 리스트의 id 중 최댓값에 1을 더해 반환한다.(json파일에서 가져오는듯?)

    def _parse_datetime(self, date_str, time_str):                           #날짜와 시간을 가져오는 함수
        return datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M") #이 함수를 호출하면, 받은 이벤트의 날짜와 시간을 출력한다.

    def _to_dict(self, event):     #이벤트에 대한 상세정보를 불러오는 함수이며 이벤트의 id, 제목, 날짜 및 시간, 기간, 태그, 우선순위를 불러온다.
        return {                   #이벤트는 딕셔너리 형태로 저장함.
            "id": event["id"],
            "title": event["title"],
            "date": event["start"].strftime("%Y-%m-%d"),
            "time": event["start"].strftime("%H:%M"),
            "duration": event["duration"],
            "tag": event.get("tag"),
            "priority": event.get("priority")
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
                start = self._parse_datetime(d["date"], d["time"]) #start = _parse_datetime()함수를 실행해 가져온 날과 시간
                self.events.append({                               #프로그램 실행 시 가져온 events 라는 리스트에 추가함. (start, end 제외하면 json파일이랑 거의 비슷하게 추가함.)
                    "id": d["id"],
                    "title": d["title"],
                    "start": start,                                  #start는 위에 있는 지역 변수 가져옴
                    "end": start + timedelta(minutes=d["duration"]), #끝은 시작에 timedelta 함수를 써서, 지속시간을 더한다.
                    "duration": d["duration"],
                    "tag": d.get("tag"),
                    "priority": d.get("priority")
                })

    # ------------------------
    # 핵심 기능
    # ------------------------

    def add_event(self, title, date, time, duration=60, tag=None, priority=None):
        start = self._parse_datetime(date, time)
        end = start + timedelta(minutes=duration)

        # 🔥 충돌 검사
        for e in self.events:
            if not (end <= e["start"] or start >= e["end"]):
                raise ValueError(f"Event conflict with id={e['id']}")

        event = {
            "id": self._generate_id(),
            "title": title,
            "start": start,
            "end": end,
            "duration": duration,
            "tag": tag,
            "priority": priority
        }

        self.events.append(event)
        self.events.sort(key=lambda x: x["start"])
        self._save()

        return self._to_dict(event)

    def list_events(self, date=None):
        if date:
            target_date = datetime.strptime(date, "%Y-%m-%d").date()
            result = [
                self._to_dict(e)
                for e in self.events
                if e["start"].date() == target_date
            ]
        else:
            result = [self._to_dict(e) for e in self.events]

        return result

    def delete_event(self, event_id):
        before = len(self.events)
        self.events = [e for e in self.events if e["id"] != event_id]

        if len(self.events) == before:
            raise ValueError("Event not found")

        self._save()
        return True

    def update_event(self, event_id, **kwargs):
        for e in self.events:
            if e["id"] == event_id:
                title = kwargs.get("title", e["title"])
                date = kwargs.get("date", e["start"].strftime("%Y-%m-%d"))
                time = kwargs.get("time", e["start"].strftime("%H:%M"))
                duration = kwargs.get("duration", e["duration"])
                tag = kwargs.get("tag", e.get("tag"))
                priority = kwargs.get("priority", e.get("priority"))

                # 기존 제거 후 재검사
                self.events.remove(e)

                try:
                    updated = self.add_event(
                        title, date, time, duration, tag, priority
                    )
                except Exception as err:
                    # 실패 시 복구
                    self.events.append(e)
                    raise err

                return updated

        raise ValueError("Event not found")