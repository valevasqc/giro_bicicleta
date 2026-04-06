import math
from datetime import datetime, timezone

TIMESTAMP_FORMAT = "%Y-%m-%dT%H:%M:%SZ"

# Easy-to-change pricing values
RATE_PER_HOUR = 5.00
MIN_CHARGE = 1.00
UNLOCK_FEE = 0.00

# Choose one:
# "per_minute" = smooth prorated pricing
# "per_10_min_block" = round up in 10-minute chunks
BILLING_MODE = "per_minute"
BLOCK_MINUTES = 10


def parse_utc(timestamp_str: str) -> datetime:
    return datetime.strptime(timestamp_str, TIMESTAMP_FORMAT).replace(tzinfo=timezone.utc)


def calculate_duration_minutes(start_time: str, end_time: str) -> float:
    start_dt = parse_utc(start_time)
    end_dt = parse_utc(end_time)
    seconds = max((end_dt - start_dt).total_seconds(), 0)
    return round(seconds / 60, 2)


def calculate_simulated_cost(duration_minutes: float) -> float:
    if duration_minutes <= 0:
        return 0.0

    if BILLING_MODE == "per_minute":
        ride_cost = (duration_minutes / 60) * RATE_PER_HOUR
    elif BILLING_MODE == "per_10_min_block":
        blocks = math.ceil(duration_minutes / BLOCK_MINUTES)
        ride_cost = blocks * ((BLOCK_MINUTES / 60) * RATE_PER_HOUR)
    else:
        raise ValueError(f"Unknown BILLING_MODE: {BILLING_MODE}")

    total = UNLOCK_FEE + ride_cost
    return round(max(total, MIN_CHARGE), 2)