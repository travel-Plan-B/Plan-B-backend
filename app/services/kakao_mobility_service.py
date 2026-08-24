import math

import httpx

from app.core.config import settings

DIRECTIONS_URL = "https://apis-navi.kakaomobility.com/v1/directions"


def format_distance(distance_km: float | None) -> str | None:
    """거리를 사람이 읽기 좋은 문자열로 변환. 1km 미만은 m, 이상은 km."""
    if distance_km is None:
        return None
    if distance_km < 1:
        return f"{round(distance_km * 1000)}m"
    return f"{distance_km}km"


def estimate_walking_distance_and_time(
    lat1: float, lng1: float, lat2: float, lng2: float, walking_speed_kmh: float = 4.0
) -> tuple[float, int]:
    """직선거리 기준 도보 거리(km)와 시간(분) 추정 (실제 도로 경로 API 없이 대략치).
    직선거리에 1.3배 보정(실제 도로는 직선보다 김)을 적용."""
    R = 6371  # 지구 반지름(km)
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng / 2) ** 2
    )
    distance_km = round(R * 2 * math.asin(math.sqrt(a)) * 1.3, 1)
    minutes = round((distance_km / walking_speed_kmh) * 60)
    return distance_km, minutes


async def get_travel_time(origin_lat, origin_lng, dest_lat, dest_lng, transport="CAR"):
    if transport == "WALK":
        distance_km, minutes = estimate_walking_distance_and_time(
            origin_lat, origin_lng, dest_lat, dest_lng
        )
        return {
            "travel_minutes": minutes,
            "distance_km": distance_km,
            "distance": format_distance(distance_km),
            "estimated": True,
        }

    headers = {"Authorization": f"KakaoAK {settings.KAKAO_REST_API_KEY}"}
    params = {
        "origin": f"{origin_lng},{origin_lat}",
        "destination": f"{dest_lng},{dest_lat}",
        "priority": "RECOMMEND",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            res = await client.get(DIRECTIONS_URL, headers=headers, params=params)
            res.raise_for_status()
            data = res.json()
    except httpx.HTTPStatusError as e:
        print(f"[카카오모빌리티 실패] {e.response.status_code}: {e.response.text}")
        return None
    except Exception as e:
        print(f"[카카오모빌리티 실패] {type(e).__name__}: {e}")
        return None

    routes = data.get("routes", [])
    if not routes or routes[0].get("result_code") != 0:
        return None

    summary = routes[0]["summary"]
    distance_km = round(summary["distance"] / 1000, 1)

    return {
        "travel_minutes": round(summary["duration"] / 60),
        "distance_km": distance_km,
        "distance": format_distance(distance_km),
        "estimated": False,
    }
