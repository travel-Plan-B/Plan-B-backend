import httpx

from app.core.config import settings

DIRECTIONS_URL = "https://apis-navi.kakaomobility.com/v1/directions"


async def get_travel_time(
    origin_lat: float, origin_lng: float, dest_lat: float, dest_lng: float
) -> dict | None:
    """두 좌표 간 자동차 이동시간(분)과 거리(km) 계산. 실패 시 None."""
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
    }
