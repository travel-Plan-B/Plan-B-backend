from app.services.time_service import validate_time_conflict


def main():
    # 케이스 1: 충분한 경우
    result1 = validate_time_conflict(
        new_start_time="15:00",
        new_duration_minutes=60,
        travel_time_to_next_minutes=15,
        next_fixed_start_time="18:00",
    )
    print("케이스1 (충분):", result1)

    # 케이스 2: 부족한 경우
    result2 = validate_time_conflict(
        new_start_time="17:00",
        new_duration_minutes=90,
        travel_time_to_next_minutes=20,
        next_fixed_start_time="18:00",
    )
    print("케이스2 (부족):", result2)


if __name__ == "__main__":
    main()
