def execute(command, engine):
    action = command.get("action")

    if action == "delete":
        condition = command.get("condition", {})
        events = engine.list_events()

        # 조건 필터링
        targets = []

        for e in events:
            match = True

            if "date" in condition and e["date"] != condition["date"]:
                match = False

            if "title" in condition and condition["title"] not in e["title"]:
                match = False

            if match:
                targets.append(e)

        # 삭제 실행
        for t in targets:
            engine.delete_event(t["id"])

        return targets