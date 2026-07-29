import asyncio
import math
from datetime import datetime, timedelta

from app.core.category_duration import get_default_duration
from app.ingest_places import ingest
from app.models.place import Place
from app.services.category_map import (
    CATEGORY_TAG_TO_CAT3,
    CATEGORY_TAG_TO_CONTENTTYPE,
    TOURAPI_CAT3_CATEGORY_MAP,
    TOURAPI_CAT3_EXCLUDE,
    TOURAPI_CONTENTTYPE_MAP,
)
from app.services.kakao_mobility_service import get_travel_time
from app.services.tourapi_service import fetch_tourapi_places_by_category

STALE_DAYS = 30


def _bounding_box(lat: float, lng: float, radius_km: float):
    """좌표+반경을 대략적인 사각형(최소/최대 위경도)으로 변환."""
    lat_delta = radius_km / 111.0
    lng_delta = radius_km / (111.0 * max(0.1, abs(math.cos(math.radians(lat)))))
    return lat - lat_delta, lat + lat_delta, lng - lng_delta, lng + lng_delta


async def get_or_ingest_places(db, lat: float, lng: float, radius_km: float = 10) -> list[Place]:
    lat_min, lat_max, lng_min, lng_max = _bounding_box(lat, lng, radius_km)
    stale_cutoff = datetime.utcnow() - timedelta(days=STALE_DAYS)

    existing = (
        db.query(Place)
        .filter(
            Place.lat.between(lat_min, lat_max),
            Place.lng.between(lng_min, lng_max),
            Place.last_synced_at >= stale_cutoff,
        )
        .all()
    )

    if existing:
        print(f"[CACHE HIT] DB에서 {len(existing)}개 재사용 (외부 API 호출 없음)")
        return existing

    print("[CACHE MISS] 데이터 없거나 오래됨 → 새로 수집")
    await ingest(db, lat, lng)
    db.commit()

    return (
        db.query(Place)
        .filter(
            Place.lat.between(lat_min, lat_max),
            Place.lng.between(lng_min, lng_max),
        )
        .all()
    )


async def get_similar_places(db, place_id: str, source: str) -> tuple[list[dict], int]:
    original = db.query(Place).filter_by(source=source, source_id=place_id).first()
    if original is None:
        return [], 0

    category_tag = original.category_tag

    if category_tag in CATEGORY_TAG_TO_CAT3:
        content_type_id = "39"
    else:
        content_type_id = CATEGORY_TAG_TO_CONTENTTYPE.get(category_tag)

    if content_type_id is None:
        return [], 0

    places, used_radius = await fetch_tourapi_places_by_category(
        lat=original.lat, lng=original.lng, content_type_id=content_type_id
    )

    if category_tag in CATEGORY_TAG_TO_CAT3:
        target_cat3 = CATEGORY_TAG_TO_CAT3[category_tag]
        places = [p for p in places if p.get("cat3") == target_cat3]

    # 블랙리스트에 걸리는 세부 카테고리 제외 (종교시설, 복지시설 등)
    places = [p for p in places if p.get("cat3") not in TOURAPI_CAT3_EXCLUDE]

    # 원본 장소 자기 자신은 후보에서 제외
    places = [p for p in places if p.get("contentid") != place_id]

    return places, used_radius


def filter_by_duration(places: list[dict], available_minutes: int) -> list[dict]:
    """카테고리 기본 체류시간이 이용가능시간 안에 들어오는 곳만 필터링."""
    if available_minutes <= 0:
        return []

    filtered = []
    for p in places:
        category_tag = TOURAPI_CAT3_CATEGORY_MAP.get(p.get("cat3")) or TOURAPI_CONTENTTYPE_MAP.get(
            p.get("contenttypeid")
        )
        duration = get_default_duration(category_tag) if category_tag else 30
        if duration <= available_minutes:
            filtered.append(p)
    return filtered


async def get_detail_recommendations(
    db,
    place_id: str,
    source: str,
    prev_location: dict | None,
    next_location: dict | None,
    priority: str = "MINIMIZE_TRAVEL",
    max_candidates: int = 10,
) -> list[dict]:
    """디테일탭 - 카테고리 필터링 + 양방향 이동시간 + 기본 체류시간까지 붙여서 최종 후보 반환."""
    raw_places, _ = await get_similar_places(db, place_id, source)

    # 이동시간 계산 비용을 줄이기 위해, 거리순 상위 일부만 처리
    raw_places = raw_places[:max_candidates]

    async def enrich(item: dict) -> dict:
        lat, lng = float(item["mapy"]), float(item["mapx"])

        travel_from_prev = None
        travel_to_next = None

        if prev_location:
            result = await get_travel_time(prev_location["lat"], prev_location["lng"], lat, lng)
            travel_from_prev = result["travel_minutes"] if result else None

        if next_location:
            result = await get_travel_time(lat, lng, next_location["lat"], next_location["lng"])
            travel_to_next = result["travel_minutes"] if result else None

        cat3 = item.get("cat3")
        category_tag = TOURAPI_CAT3_CATEGORY_MAP.get(cat3) or TOURAPI_CONTENTTYPE_MAP.get(
            item.get("contenttypeid")
        )

        return {
            "place_id": item.get("contentid"),
            "name": item.get("title"),
            "address": item.get("addr1"),
            "category_tag": category_tag,
            "lat": lat,
            "lng": lng,
            "travel_time_from_prev_minutes": travel_from_prev,
            "travel_time_to_next_minutes": travel_to_next,
            "estimated_duration_minutes": (
                get_default_duration(category_tag) if category_tag else 30
            ),
        }

    # 여러 후보의 이동시간을 동시에 계산 (순차 호출 방지)
    enriched = await asyncio.gather(*[enrich(p) for p in raw_places])

    if priority == "MINIMIZE_TRAVEL":

        def total_travel(p):
            a = p["travel_time_from_prev_minutes"] or 0
            b = p["travel_time_to_next_minutes"] or 0
            return a + b

        enriched.sort(key=total_travel)
    # SIMILAR_TO_ORIGINAL, EXPLORE_NEW은 일단 원래 순서(거리순) 유지 - 추후 다듬을 부분

    return enriched
