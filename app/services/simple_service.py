import asyncio

from app.core.category_duration import get_default_duration
from app.services.kakao_mobility_service import get_travel_time


def filter_by_category_whitelist(
    places, problem_reason: str, situational_answer: str | None = None, force_indoor: bool = False
):
    """문제 사유에 맞는 카테고리만 필터링.
    WEATHER 사유는 사용자 응답을 그대로 따르고,
    그 외 사유는 실제 기상청 데이터(force_indoor)로 자동 판단."""
    if problem_reason == "WEATHER":
        if situational_answer in ("OUTDOOR_ONLY", "BOTH"):
            places = [p for p in places if p.is_indoor is True]
        if situational_answer in ("WALKING_ONLY", "BOTH"):
            places = [p for p in places if p.category_tag != "레포츠"]
    elif force_indoor:
        places = [p for p in places if p.is_indoor is True]

    return places


def sort_by_popularity(places):
    """후보 내 상대 기준으로 리뷰수 정렬. user_rating_count 없으면 맨 뒤로 밀림."""
    return sorted(places, key=lambda p: p.user_rating_count or 0, reverse=True)


async def enrich_with_travel_time(places, current_lat: float, current_lng: float, transport: str = "CAR"):
    """각 장소에 현재 위치로부터의 이동시간(분)을 계산해서 붙임. 실패 시 None."""

    async def attach(p):
        result = await get_travel_time(current_lat, current_lng, p.lat, p.lng, transport=transport)
        p.travel_minutes = result["travel_minutes"] if result else None
        return p

    return await asyncio.gather(*[attach(p) for p in places])


def sort_places(places, sort_option: str = "RECOMMENDED"):
    """정렬 옵션 적용: RECOMMENDED(인기순) / NEAREST(가까운순) / LONGEST_STAY(체류시간순)"""
    if sort_option == "NEAREST":
        return sorted(
            places, key=lambda p: p.travel_minutes if p.travel_minutes is not None else 9999
        )
    if sort_option == "LONGEST_STAY":
        from app.core.category_duration import get_default_duration

        return sorted(places, key=lambda p: get_default_duration(p.category_tag), reverse=True)
    return sort_by_popularity(places)  # 기본값: RECOMMENDED


def place_to_dict(p, recommend_reason: str | None = None) -> dict:
    return {
        "place_id": p.source_id,
        "name": p.name,
        "category_tag": p.category_tag,
        "is_indoor": p.is_indoor,
        "image_url": p.image_url,
        "rating": float(p.rating) if p.rating is not None else None,
        "user_rating_count": p.user_rating_count,
        "description": p.description,
        "address": p.address,
        "travel_time_minutes": getattr(p, "travel_minutes", None),
        "operating_hours": p.operating_hours,
        "parking_available": p.parking_available,
        "parking_status": p.parking_status,
        "estimated_duration_minutes": get_default_duration(p.category_tag),
        "recommend_reason": recommend_reason,
    }


def filter_by_duration_simple(places, available_minutes: int) -> list:
    """카테고리 기본 체류시간이 이용가능시간 안에 들어오는 곳만 필터링. (Place DB 객체용)"""
    if available_minutes <= 0:
        return []
    return [p for p in places if get_default_duration(p.category_tag) <= available_minutes]
