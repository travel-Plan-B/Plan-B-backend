from datetime import datetime


def calculate_available_minutes(
    deadline_time: str, current_time: str, travel_minutes: int, buffer_minutes: int = 10
) -> int:
    """이용 가능 시간 = 마감시간 - 현재시간 - 이동시간 - 여유시간(기본 10분)"""
    fmt = "%H:%M"
    deadline = datetime.strptime(deadline_time, fmt)
    current = datetime.strptime(current_time, fmt)

    remaining = (deadline - current).total_seconds() / 60
    return int(remaining - travel_minutes - buffer_minutes)


def validate_time_conflict(
    new_start_time: str,
    new_duration_minutes: int,
    travel_time_to_next_minutes: int,
    next_fixed_start_time: str,
    buffer_minutes: int = 10,
) -> dict:
    """수정한 시간이 다음 고정 일정과 충돌하는지 검증."""
    fmt = "%H:%M"
    start = datetime.strptime(new_start_time, fmt)
    next_fixed = datetime.strptime(next_fixed_start_time, fmt)

    end_time = start.timestamp() + new_duration_minutes * 60
    arrival_at_next = end_time + travel_time_to_next_minutes * 60 + buffer_minutes * 60

    remaining_seconds = next_fixed.timestamp() - arrival_at_next
    remaining_minutes = int(remaining_seconds / 60)

    if remaining_minutes >= 0:
        return {
            "valid": True,
            "buffer_minutes_remaining": remaining_minutes,
            "reason": None,
            "shortfall_minutes": None,
        }
    else:
        return {
            "valid": False,
            "buffer_minutes_remaining": None,
            "reason": f"다음 고정 일정({next_fixed_start_time}) 도착까지 시간이 부족합니다.",
            "shortfall_minutes": abs(remaining_minutes),
        }
