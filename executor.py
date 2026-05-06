def _require_fields(command, fields):
    missing = [field for field in fields if field not in command]
    if missing:
        raise ValueError(f"Missing command fields: {', '.join(missing)}")


def _matches_condition(event, condition):
    if "date" in condition and event["date"] != condition["date"]:
        return False

    if "time" in condition and event["time"] != condition["time"]:
        return False

    if "title" in condition and condition["title"] not in event["title"]:
        return False

    return True


def execute(command, engine):
    action = command.get("action")

    if action == "add":
        _require_fields(command, ["title", "date", "time"])
        return engine.add_event(
            command["title"],
            command["date"],
            command["time"],
            command.get("duration", 60),
            command.get("tag"),
            command.get("priority"),
        )

    if action == "list":
        return engine.list_events(command.get("date"))

    if action == "delete":
        condition = command.get("condition", {})
        if not condition:
            raise ValueError("Delete condition is required")

        events = engine.list_events()
        targets = [e for e in events if _matches_condition(e, condition)]

        for t in targets:
            engine.delete_event(t["id"])

        return targets

    raise ValueError(f"Unknown action: {action}")
