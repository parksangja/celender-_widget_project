from datetime import datetime, timedelta
import json
import os


class CalendarEngine:
    def __init__(self, storage_path="events.json"):
        self.events = [] #입력 받은 이벤트를 담을 리스트
        self.storage_path = storage_path #
        self._load()

    # ------------------------
    # 내부 유틸
    # ------------------------
    def _generate_id(self):
        if not self.events:
            return 1
        return max(e["id"] for e in self.events) + 1

    def _parse_datetime(self, date_str, time_str):
        return datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")

    def _to_dict(self, event):
        return {
            "id": event["id"],
            "title": event["title"],
            "date": event["start"].strftime("%Y-%m-%d"),
            "time": event["start"].strftime("%H:%M"),
            "duration": event["duration"],
            "tag": event.get("tag"),
            "priority": event.get("priority")
        }

    def _save(self):
        data = [self._to_dict(e) for e in self.events]
        with open(self.storage_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _load(self):
        if not os.path.exists(self.storage_path):
            return
        with open(self.storage_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            for d in data:
                start = self._parse_datetime(d["date"], d["time"])
                self.events.append({
                    "id": d["id"],
                    "title": d["title"],
                    "start": start,
                    "end": start + timedelta(minutes=d["duration"]),
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