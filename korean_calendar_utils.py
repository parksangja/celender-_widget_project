from datetime import date, datetime, timedelta

from korean_lunar_calendar import KoreanLunarCalendar


def lunar_to_solar(year, month, day, leap_month=False):
    calendar = KoreanLunarCalendar()
    is_valid = calendar.setLunarDate(year, month, day, leap_month)

    if not is_valid:
        raise ValueError("Invalid lunar date")

    return datetime.strptime(calendar.SolarIsoFormat(), "%Y-%m-%d").date()


def _add_holiday(holidays, holiday_date, name):
    holidays.setdefault(holiday_date, [])
    if name not in holidays[holiday_date]:
        holidays[holiday_date].append(name)


def _next_substitute_date(holidays, after_date):
    candidate = after_date + timedelta(days=1)

    while candidate.weekday() >= 5 or candidate in holidays:
        candidate += timedelta(days=1)

    return candidate


def _add_substitute_holidays(holidays, base_holidays):
    seen_counts = {}
    for holiday_date, _name, _rule in base_holidays:
        seen_counts[holiday_date] = seen_counts.get(holiday_date, 0) + 1

    for holiday_date, name, rule in base_holidays:
        has_overlap = seen_counts[holiday_date] > 1
        needs_substitute = False

        if rule == "weekend_or_overlap":
            needs_substitute = holiday_date.weekday() >= 5 or has_overlap
        elif rule == "sunday_or_overlap":
            needs_substitute = holiday_date.weekday() == 6 or has_overlap

        if not needs_substitute:
            continue

        substitute_date = _next_substitute_date(holidays, holiday_date)
        _add_holiday(holidays, substitute_date, f"{name} 대체공휴일")


def get_korean_holidays(year):
    base_holidays = []

    def add_base(holiday_date, name, rule="none"):
        if holiday_date.year == year:
            base_holidays.append((holiday_date, name, rule))

    fixed_holidays = [
        (date(year, 1, 1), "신정", "none"),
        (date(year, 3, 1), "삼일절", "weekend_or_overlap"),
        (date(year, 5, 1), "근로자의 날", "none"),
        (date(year, 5, 5), "어린이날", "weekend_or_overlap"),
        (date(year, 6, 6), "현충일", "none"),
        (date(year, 7, 17), "제헌절", "weekend_or_overlap"),
        (date(year, 8, 15), "광복절", "weekend_or_overlap"),
        (date(year, 10, 3), "개천절", "weekend_or_overlap"),
        (date(year, 10, 9), "한글날", "weekend_or_overlap"),
        (date(year, 12, 25), "기독탄신일", "weekend_or_overlap"),
    ]

    for holiday_date, name, rule in fixed_holidays:
        add_base(holiday_date, name, rule)

    seollal = lunar_to_solar(year, 1, 1)
    for offset, name in [(-1, "설날 전날"), (0, "설날"), (1, "설날 다음날")]:
        add_base(seollal + timedelta(days=offset), name, "sunday_or_overlap")

    buddha_birthday = lunar_to_solar(year, 4, 8)
    add_base(buddha_birthday, "부처님오신날", "weekend_or_overlap")

    chuseok = lunar_to_solar(year, 8, 15)
    for offset, name in [(-1, "추석 전날"), (0, "추석"), (1, "추석 다음날")]:
        add_base(chuseok + timedelta(days=offset), name, "sunday_or_overlap")

    holidays = {}
    for holiday_date, name, _rule in base_holidays:
        _add_holiday(holidays, holiday_date, name)

    _add_substitute_holidays(holidays, base_holidays)

    return {
        holiday_date.strftime("%Y-%m-%d"): names
        for holiday_date, names in sorted(holidays.items())
        if holiday_date.year == year
    }
