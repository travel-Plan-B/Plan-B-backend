import asyncio
import math
from datetime import datetime, timedelta

from app.core.category_duration import get_default_duration
from app.ingest_places import ingest
from app.models.place import Place
from app.services.ai_recommend_service import get_ai_final_pick
from app.services.category_map import (
    CATEGORY_TAG_TO_CAT3,
    CATEGORY_TAG_TO_CONTENTTYPE,
    TOURAPI_CAT3_CATEGORY_MAP,
    TOURAPI_CAT3_EXCLUDE,
    TOURAPI_CONTENTTYPE_MAP,
    infer_indoor,
)
from app.services.google_places_service import enrich_with_google_rating
from app.services.kakao_mobility_service import get_travel_time
from app.services.tourapi_service import (
    fetch_tourapi_places_by_category,
    fetch_tourapi_places_expanding,
)
from app.services.weather_service import get_current_weather, latlng_to_grid

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

    MIN_CACHE_COUNT = 10

    if existing and len(existing) >= MIN_CACHE_COUNT:
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


def _normalize_name(name: str | None) -> str:
    """이름 비교용 정규화: 공백 제거."""
    return (name or "").replace(" ", "")


def _is_same_place(
    candidate_name,
    candidate_lat,
    candidate_lng,
    original_name,
    original_lat,
    original_lng,
    max_distance_m=50,
) -> bool:
    """이름이 같거나, 좌표가 아주 가까우면(기본 50m 이내) 같은 장소로 판단."""
    if _normalize_name(candidate_name) == _normalize_name(original_name):
        return True

    distance_km = (
        (candidate_lat - original_lat) ** 2 + (candidate_lng - original_lng) ** 2
    ) ** 0.5 * 111
    distance_m = distance_km * 1000
    return distance_m <= max_distance_m


async def get_similar_places(
    db, place_id: str, source: str, priority: str = "SIMILAR_TO_ORIGINAL"
) -> tuple[list[dict], int]:
    original = db.query(Place).filter_by(source=source, source_id=place_id).first()
    if original is None:
        return [], 0

    category_tag = original.category_tag

    if priority == "EXPLORE_NEW":
        # 카테고리 무관하게 넓게 검색 (심플탭 로직 재사용)
        raw_places, used_radius = await fetch_tourapi_places_expanding(
            original.lat, original.lng, target_count=30
        )
        places = raw_places

        places = [
            p
            for p in places
            if (
                TOURAPI_CAT3_CATEGORY_MAP.get(p.get("cat3"))
                or TOURAPI_CONTENTTYPE_MAP.get(p.get("contenttypeid"))
            )
            is not None
        ]

        # 같은 카테고리는 오히려 제외해서 "새로운 느낌"을 강조
        places = [
            p
            for p in places
            if (
                TOURAPI_CAT3_CATEGORY_MAP.get(p.get("cat3"))
                or TOURAPI_CONTENTTYPE_MAP.get(p.get("contenttypeid"))
            )
            != category_tag
        ]
    else:
        if category_tag in CATEGORY_TAG_TO_CAT3:
            content_type_id = "39"
        else:
            content_type_id = CATEGORY_TAG_TO_CONTENTTYPE.get(category_tag)

        if content_type_id is None:
            return [], 0

        places, used_radius = await fetch_tourapi_places_by_category(
            lat=original.lat, lng=original.lng, content_type_id=content_type_id, target_count=30
        )

        if category_tag in CATEGORY_TAG_TO_CAT3:
            target_cat3 = CATEGORY_TAG_TO_CAT3[category_tag]
            places = [p for p in places if p.get("cat3") == target_cat3]

    places = [p for p in places if p.get("cat3") not in TOURAPI_CAT3_EXCLUDE]
    places = [
        p
        for p in places
        if not _is_same_place(
            p.get("title"),
            float(p.get("mapy", 0)),
            float(p.get("mapx", 0)),
            original.name,
            original.lat,
            original.lng,
        )
    ]

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
    place_id,
    source,
    prev_location,
    next_location,
    priority="MINIMIZE_TRAVEL",
    max_candidates=10,
    transport="CAR",
    problem_reason="PLACE_UNAVAILABLE",
    situational_answer=None,
    current_time=None,
    next_item_start_time=None,
):
    original = db.query(Place).filter_by(source=source, source_id=place_id).first()

    weather_info = None
    if problem_reason != "WEATHER" and original:
        nx, ny = latlng_to_grid(original.lat, original.lng)
        weather_info = await get_current_weather(nx, ny)

    is_bad_weather = False
    if weather_info:
        is_bad_weather = weather_info["sky_condition"] in ("RAIN", "RAIN_SNOW", "SNOW", "SHOWER")

    raw_places, _ = await get_similar_places(db, place_id, source, priority=priority)
    # 여기서 자르지 않고, 최대한 많이(30개) 가져와서 아래 필터링을 거친 후에 자름

    async def enrich(item: dict) -> dict:
        lat, lng = float(item["mapy"]), float(item["mapx"])
        travel_from_prev = None
        travel_to_next = None

        distance_from_prev = None
        distance_from_prev_km = None
        distance_to_next = None

        if prev_location:
            result = await get_travel_time(
                prev_location["lat"], prev_location["lng"], lat, lng, transport=transport
            )
            travel_from_prev = result["travel_minutes"] if result else None
            distance_from_prev = result["distance"] if result else None
            distance_from_prev_km = result["distance_km"] if result else None

        if next_location:
            result = await get_travel_time(
                lat, lng, next_location["lat"], next_location["lng"], transport=transport
            )
            travel_to_next = result["travel_minutes"] if result else None
            distance_to_next = result["distance"] if result else None

        google_data = await enrich_with_google_rating(name=item.get("title"), lat=lat, lng=lng)
        rating = google_data["rating"] if google_data else None
        user_rating_count = google_data["user_rating_count"] if google_data else None
        parking_status = google_data["parking_status"] if google_data else None
        operating_hours = google_data["operating_hours"] if google_data else None

        cat3 = item.get("cat3")
        category_tag = TOURAPI_CAT3_CATEGORY_MAP.get(cat3) or TOURAPI_CONTENTTYPE_MAP.get(
            item.get("contenttypeid")
        )
        is_indoor = infer_indoor("tourapi", cat3, cat1=item.get("cat1"), name=item.get("title"))

        schedule_buffer_minutes = None
        if current_time and next_item_start_time and travel_from_prev is not None:

            duration = get_default_duration(category_tag) if category_tag else 30
            total_before_next_travel = travel_from_prev + duration
            # current_time에서 total_before_next_travel만큼 지난 시각과 next_item_start_time의 차이
            from datetime import datetime, timedelta

            fmt = "%H:%M"
            start = datetime.strptime(current_time, fmt) + timedelta(
                minutes=total_before_next_travel
            )
            next_fixed = datetime.strptime(next_item_start_time, fmt)
            travel_next = travel_to_next or 0
            remaining = (next_fixed - start).total_seconds() / 60 - travel_next
            schedule_buffer_minutes = int(remaining)

        return {
            "place_id": item.get("contentid"),
            "name": item.get("title"),
            "address": item.get("addr1"),
            "category_tag": category_tag,
            "is_indoor": is_indoor,
            "image_url": item.get("firstimage") or None,
            "rating": rating,
            "user_rating_count": user_rating_count,
            "parking_status": parking_status,
            "operating_hours": operating_hours,
            "lat": lat,
            "lng": lng,
            "travel_time_from_prev_minutes": travel_from_prev,
            "travel_time_to_next_minutes": travel_to_next,
            "distance_from_prev": distance_from_prev,
            "distance_from_prev_km": distance_from_prev_km,
            "distance_to_next": distance_to_next,
            "estimated_duration_minutes": (
                get_default_duration(category_tag) if category_tag else 30
            ),
            "schedule_buffer_minutes": schedule_buffer_minutes,
        }

    enriched = await asyncio.gather(*[enrich(p) for p in raw_places])

    MAX_DISTANCE_KM = 10
    enriched = [
        p
        for p in enriched
        if p.get("distance_from_prev_km") is None or p["distance_from_prev_km"] <= MAX_DISTANCE_KM
    ]

    if problem_reason == "WEATHER" and situational_answer in ("OUTDOOR_ONLY", "BOTH"):
        enriched = [p for p in enriched if p.get("is_indoor") is not False]
    elif is_bad_weather:
        enriched.sort(key=lambda p: p.get("is_indoor") is not True)

    if priority == "MINIMIZE_TRAVEL":

        def total_travel(p):
            return (p["travel_time_from_prev_minutes"] or 0) + (
                p["travel_time_to_next_minutes"] or 0
            )

        enriched.sort(key=total_travel)
    elif priority == "SIMILAR_TO_ORIGINAL":
        original_category = original.category_tag if original else None
        enriched.sort(key=lambda p: p["category_tag"] != original_category)

    enriched = enriched[:max_candidates]

    priority_text = {
        "MINIMIZE_TRAVEL": "이동 시간이 가장 짧은 곳을 우선으로 선택해주세요.",
        "SIMILAR_TO_ORIGINAL": "원래 장소와 성격이 비슷한 곳을 우선으로 선택해주세요.",
        "EXPLORE_NEW": "평소와는 다른 새로운 느낌의 장소를 우선으로 선택해주세요.",
    }.get(priority, "이동 시간이 가장 짧은 곳을 우선으로 선택해주세요.")

    situation_description = f"일정 속 장소를 대체할 곳을 찾고 있습니다. {priority_text}"
    if weather_info and is_bad_weather:
        situation_description += f" 지금 이 시간대에는 날씨 예보가 좋지 않아({weather_info['sky_condition']}), 실내 장소를 우선 고려해주세요."

    situation = {"situation_description": situation_description, "available_minutes": None}
    ai_result = await get_ai_final_pick(enriched, situation, transport=transport)

    if ai_result:
        reason_map = {r["place_id"]: r["reason"] for r in ai_result}
        ai_recommended = [d for d in enriched if d["place_id"] in reason_map]
        for d in ai_recommended:
            d["recommend_reason"] = reason_map[d["place_id"]]
        more_places = [d for d in enriched if d["place_id"] not in reason_map]
    else:
        for d in enriched:
            d["recommend_reason"] = None
        ai_recommended = enriched[:3]
        more_places = enriched[3:]

    return {"ai_recommended": ai_recommended, "more_places": more_places}
