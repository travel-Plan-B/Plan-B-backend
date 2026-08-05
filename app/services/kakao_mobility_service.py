import math

import httpx

from app.core.config import settings

DIRECTIONS_URL = "https://apis-navi.kakaomobility.com/v1/directions"


async def get_travel_time(origin_lat: float, origin_lng: float, dest_lat: float, dest_lng: float, transport: str = "CAR") -> dict | None:
    """두 좌표 간 이동시간(분)과 거리(km) 계산.
    자동차: 카카오모빌리티 실제 경로 API. 도보: 직선거리 기준 추정치(실제 도로 API 미승인 상태)."""
    if transport == "WALK":
        minutes = estimate_walking_minutes(origin_lat, origin_lng, dest_lat, dest_lng)
        return {"travel_minutes": minutes, "distance_km": None, "estimated": True}

    headers = {"Authorization": f"KakaoAK {settings.KAKAO_REST_API_KEY}"}
    params = {
        "origin": f"{origin_lng},{origin_lat}",
        "destination": f"{dest_lng},{dest_lat}",
        "priority": "RECOMMEND",
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        res = await client.get(DIRECTIONS_URL, headers=headers, params=params)
        res.raise_for_status()
        data = res.json()

    routes = data.get("routes", [])
    if not routes or routes[0].get("result_code") != 0:
        return None

    summary = routes[0]["summary"]
    return {
        "travel_minutes": round(summary["duration"] / 60),
        "distance_km": round(summary["distance"] / 1000, 1),
        "estimated": False,
    }

def estimate_walking_minutes(lat1: float, lng1: float, lat2: float, lng2: float, walking_speed_kmh: float = 4.0) -> int:
    """직선거리 기준 도보 시간 추정 (실제 도로 경로 API 없이 대략치).
    직선거리에 1.3배 보정(실제 도로는 직선보다 김)을 적용."""
    R = 6371  # 지구 반지름(km)
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng / 2) ** 2
    distance_km = R * 2 * math.asin(math.sqrt(a)) * 1.3

    return round((distance_km / walking_speed_kmh) * 60)
