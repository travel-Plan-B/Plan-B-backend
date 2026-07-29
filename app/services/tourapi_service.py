import httpx
from typing import Any

from app.core.config import settings

TOURAPI_BASE_URL = "https://apis.data.go.kr/B551011/KorService2/locationBasedList2"


# ===== 공용 =====
async def fetch_tourapi_places(
    lat: float, lng: float, radius: int = 1000, content_type_id: str | None = None
) -> list[dict]:
    params: dict[str, Any] = {
        "serviceKey": settings.TOUR_API_KEY,
        "MobileOS": "ETC",
        "MobileApp": "PlanB",
        "mapX": lng,
        "mapY": lat,
        "radius": radius,
        "numOfRows": 50,
        "pageNo": 1,
        "_type": "json",
    }

    if content_type_id is not None:
        params["contentTypeId"] = content_type_id

    async with httpx.AsyncClient(timeout=10.0) as client:
        res = await client.get(TOURAPI_BASE_URL, params=params)
        res.raise_for_status()
        data = res.json()

    items = data.get("response", {}).get("body", {}).get("items", {})
    if items == "" or not items:
        return []
    return items.get("item", [])


# ===== 심플탭 전용 =====
async def fetch_tourapi_places_expanding(
    lat: float, lng: float, target_count: int = 30, max_process: int = 30
) -> tuple[list[dict], int]:
    """target_count(기본 30개) 이상 모일 때까지 3km→5km→10km로 반경을 넓혀가며 검색.
    max_process개까지만(가까운 순) 이후 단계로 넘김."""
    radius_steps = [3000, 5000, 10000]
    collected = []
    seen_ids = set()
    used_radius = radius_steps[0]

    for radius in radius_steps:
        places = await fetch_tourapi_places(lat=lat, lng=lng, radius=radius)

        for p in places:
            content_id = p.get("contentid")
            if content_id not in seen_ids:
                collected.append(p)
                seen_ids.add(content_id)

        used_radius = radius
        if len(collected) >= target_count:
            break

    collected.sort(key=lambda p: float(p.get("dist", 0)))
    return collected[:max_process], used_radius


# ===== 디테일탭 전용 =====
async def fetch_tourapi_places_by_category(
    lat: float, lng: float, content_type_id: str, target_count: int = 10
) -> tuple[list[dict], int]:
    """특정 contenttypeid로 좁혀서 검색. 디테일탭 카테고리 교체용."""
    radius_steps = [3000, 5000, 10000]
    collected = []
    seen_ids = set()
    used_radius = radius_steps[0]

    for radius in radius_steps:
        places = await fetch_tourapi_places(
            lat=lat, lng=lng, radius=radius, content_type_id=content_type_id
        )
        for p in places:
            content_id = p.get("contentid")
            if content_id not in seen_ids:
                collected.append(p)
                seen_ids.add(content_id)

        used_radius = radius
        if len(collected) >= target_count:
            break

    collected.sort(key=lambda p: float(p.get("dist", 0)))
    return collected[:target_count], used_radius
