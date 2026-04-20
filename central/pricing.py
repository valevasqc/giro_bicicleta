from datetime import datetime, timezone

TIMESTAMP_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


def parse_utc(timestamp_str: str) -> datetime:
    return datetime.strptime(timestamp_str, TIMESTAMP_FORMAT).replace(tzinfo=timezone.utc)


def calculate_duration_minutes(start_time: str, end_time: str) -> float:
    start_dt = parse_utc(start_time)
    end_dt = parse_utc(end_time)
    seconds = max((end_dt - start_dt).total_seconds(), 0)
    return round(seconds / 60, 2)


def calculate_cost(duration_minutes: float, rate_per_minute: float, minimum_charge: float) -> float:
    """Return ride cost in GTQ at a per-minute rate, floored to minimum_charge."""
    if duration_minutes <= 0:
        return minimum_charge
    cost = duration_minutes * rate_per_minute
    return round(max(cost, minimum_charge), 2)
