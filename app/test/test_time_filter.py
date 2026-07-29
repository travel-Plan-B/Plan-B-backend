from app.core.category_duration import get_default_duration
from app.services.place_repository import filter_by_duration
from app.services.time_service import calculate_available_minutes


def main():
    # 1. 이용가능시간 계산 테스트
    available = calculate_available_minutes(
        deadline_time="18:00", current_time="16:30", travel_minutes=15
    )
    print(f"이용가능시간: {available}분")

    # 2. 카테고리별 기본 체류시간 확인
    print(f"카페 기본 체류시간: {get_default_duration('카페')}분")
    print(f"매핑 없는 카테고리: {get_default_duration('레저')}분 (기본값 확인)")

    # 3. 시간 필터링 테스트 (임의 데이터로)
    fake_places = [
        {"cat3": "A05020900", "contenttypeid": "39", "title": "카페A"},  # 카페, 40분
        {"cat3": None, "contenttypeid": "14", "title": "박물관A"},  # 문화시설, 60분
    ]
    filtered = filter_by_duration(fake_places, available_minutes=available)
    print(f"\n필터링 결과 ({available}분 안에 가능한 곳):")
    for p in filtered:
        print(f"- {p['title']}")


if __name__ == "__main__":
    main()
