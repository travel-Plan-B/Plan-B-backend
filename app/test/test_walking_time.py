from app.services.kakao_mobility_service import estimate_walking_distance_and_time


def main():
    distance_km, minutes = estimate_walking_distance_and_time(
        37.8034055083125, 128.910210247605, 37.7977913781, 128.9095224784
    )
    print(f"도보 예상 거리: {distance_km}km, 예상 시간: {minutes}분")


if __name__ == "__main__":
    main()
