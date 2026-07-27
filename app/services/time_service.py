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
