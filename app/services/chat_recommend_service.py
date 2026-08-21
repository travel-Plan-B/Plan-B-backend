import asyncio

from app.core.category_duration import get_default_duration
from app.ingest_places import upsert_place
from app.services.ai_recommend_service import get_ai_final_pick
from app.services.category_map import (
    CATEGORY_TAG_TO_CAT3,
    CATEGORY_TAG_TO_CONTENTTYPE,
    TOURAPI_CAT3_CATEGORY_MAP,
    TOURAPI_CONTENTTYPE_MAP,
    infer_indoor,
)
from app.services.google_places_service import enrich_with_google_rating
from app.services.kakao_mobility_service import get_travel_time
from app.services.kakao_service import search_kakao_place
from app.services.normalize_service import normalize_kakao_place
from app.services.place_repository import (
    get_detail_recommendations,
    get_or_ingest_places,
)  # noqa: F401
from app.services.simple_service import enrich_with_travel_time, place_to_dict, sort_places
from app.services.tourapi_service import fetch_tourapi_places_by_category


async def recommend_from_chat(
    db,
    place_name: str | None,
    category: str | None,
    current_location: str,
    transport: str,
    search_mode: str = "SAME_CATEGORY",
) -> dict:
    """챗봇에서 추출한 정보로 대체 장소 추천 실행."""

    location_results = await search_kakao_place(current_location)
    if not location_results:
        return {"success": False, "reason": "LOCATION_NOT_FOUND"}

    current_lat = float(location_results[0]["y"])
    current_lng = float(location_results[0]["x"])

    # 케이스 1: 구체적 장소명이 있는 경우 - 그 장소 기준으로 대체 검색
    if place_name:
        place_results = await search_kakao_place(place_name)
        if not place_results:
            return {"success": False, "reason": "PLACE_NOT_FOUND"}

        place_item = place_results[0]
        normalized = normalize_kakao_place(place_item)
        if normalized is None:
            return {"success": False, "reason": "CATEGORY_NOT_SUPPORTED"}

        upsert_place(db, normalized)
        db.commit()

        if search_mode == "ANYTHING_NEARBY":
            data = await _recommend_anything_nearby(db, current_lat, current_lng, transport)
        else:
            result = await get_detail_recommendations(
                db,
                place_id=normalized["source_id"],
                source=normalized["source"],
                prev_location={"lat": current_lat, "lng": current_lng},
                next_location=None,
                priority="MINIMIZE_TRAVEL",
                transport=transport,
                problem_reason="PLACE_UNAVAILABLE",
                situational_answer="YES",
            )
            data = result

        return {"success": True, "data": data}

    # 케이스 2: 구체적 장소명 없이 카테고리만 있는 경우
    if category:
        data = await _recommend_by_category(db, category, current_lat, current_lng, transport)
        if data is None:
            return {"success": False, "reason": "CATEGORY_NOT_SUPPORTED"}
        return {"success": True, "data": data}

    return {"success": False, "reason": "PLACE_NOT_FOUND"}


async def _recommend_anything_nearby(db, lat: float, lng: float, transport: str) -> dict:
    """카테고리 무관, 주변 아무 곳이나 추천 (심플탭 로직 재사용)."""
    places = await get_or_ingest_places(db, lat=lat, lng=lng)
    places = await enrich_with_travel_time(places, lat, lng, transport=transport)
    places = [p for p in places if getattr(p, "distance_km", None) is None or p.distance_km <= 10]
    places = sort_places(places, "RECOMMENDED")[:10]

    return await _ai_pick_and_format(
        places,
        "사용자가 특정 장소 대신 주변에 갈 만한 곳을 찾고 있습니다. 카테고리는 상관없습니다.",
        transport,
    )


async def _recommend_by_category(
    db, category: str, lat: float, lng: float, transport: str
) -> dict | None:
    """구체적 장소 없이, 카테고리만으로 주변 검색."""

    # 카페처럼 대분류가 아니라 cat3로만 구분되는 카테고리는 39(음식점)로 넓게 검색 후 재필터링
    if category in CATEGORY_TAG_TO_CAT3:
        content_type_id = "39"
        target_cat3 = CATEGORY_TAG_TO_CAT3[category]
    else:
        content_type_id = CATEGORY_TAG_TO_CONTENTTYPE.get(category)
        target_cat3 = None

    if content_type_id is None:
        return None

    raw_places, _ = await fetch_tourapi_places_by_category(
        lat=lat, lng=lng, content_type_id=content_type_id, target_count=30
    )

    if target_cat3:
        raw_places = [p for p in raw_places if p.get("cat3") == target_cat3]

    if not raw_places:
        return {"ai_recommended": [], "more_places": []}

    async def enrich(item: dict) -> dict:
        item_lat, item_lng = float(item["mapy"]), float(item["mapx"])
        result = await get_travel_time(lat, lng, item_lat, item_lng, transport=transport)
        travel_minutes = result["travel_minutes"] if result else None
        distance = result["distance"] if result else None
        distance_km = result["distance_km"] if result else None

        google_data = await enrich_with_google_rating(
            name=item.get("title"), lat=item_lat, lng=item_lng
        )
        rating = google_data["rating"] if google_data else None
        user_rating_count = google_data["user_rating_count"] if google_data else None
        parking_status = google_data["parking_status"] if google_data else None
        operating_hours = google_data["operating_hours"] if google_data else None

        cat3 = item.get("cat3")
        category_tag = TOURAPI_CAT3_CATEGORY_MAP.get(cat3) or TOURAPI_CONTENTTYPE_MAP.get(
            item.get("contenttypeid")
        )
        is_indoor = infer_indoor("tourapi", cat3, cat1=item.get("cat1"), name=item.get("title"))

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
            "travel_time_minutes": travel_minutes,
            "distance": distance,
            "distance_km": distance_km,
            "estimated_duration_minutes": (
                get_default_duration(category_tag) if category_tag else 30
            ),
        }

    enriched = await asyncio.gather(*[enrich(p) for p in raw_places])
    enriched = [p for p in enriched if p.get("distance_km") is None or p["distance_km"] <= 10]
    enriched.sort(
        key=lambda p: (
            p.get("travel_time_minutes") if p.get("travel_time_minutes") is not None else 9999
        )
    )
    enriched = enriched[:10]

    return await _ai_pick_and_format(
        enriched,
        f"사용자가 '{category}' 카테고리의 장소를 찾고 있습니다.",
        transport,
        already_dict=True,
    )


async def _ai_pick_and_format(
    places, situation_description: str, transport: str, already_dict: bool = False
) -> dict:
    """AI 최종 선택 후 ai_recommended/more_places 형태로 조립. 공통 로직 분리."""
    if already_dict:
        candidates = places
    else:
        candidates = [place_to_dict(p) for p in places]

    situation = {"situation_description": situation_description, "available_minutes": None}
    ai_result = await get_ai_final_pick(candidates, situation, transport=transport)

    if ai_result:
        # AI가 3개보다 많이 돌려줄 수도 있으니, 안전하게 상위 3개만 사용
        ai_result = ai_result[:3]
        reason_map = {r["place_id"]: r["reason"] for r in ai_result}
        ai_recommended = [d for d in candidates if d["place_id"] in reason_map]
        for d in ai_recommended:
            d["recommend_reason"] = reason_map[d["place_id"]]
        more_places = [d for d in candidates if d["place_id"] not in reason_map]
    else:
        for d in candidates:
            d["recommend_reason"] = None
        ai_recommended = candidates[:3]
        more_places = candidates[3:]

    return {
        "ai_recommended": ai_recommended,
        "more_places": more_places,
        "travel_time_disclaimer": "입력하신 위치 기준으로 계산된 예상 이동시간이며, 실제와 다를 수 있습니다.",
    }
