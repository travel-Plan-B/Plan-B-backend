import asyncio
import math
import re
from difflib import SequenceMatcher

from app.core.category_duration import get_default_duration
from app.services.kakao_mobility_service import get_travel_time


def _normalize_name(name: str | None) -> str:
    """이름 비교용 정규화: 공백 제거 + 소문자화."""
    if not name:
        return ""
    return re.sub(r"\s+", "", name).lower()


def _haversine_km(lat1, lng1, lat2, lng2) -> float:
    """두 좌표 간 직선거리(km). 라우팅 API의 실제 도로 경로 거리와 달리
    출발지=도착지가 같은 지점이어도 왜곡되지 않아, 동일 장소 판별에 사용."""
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng / 2) ** 2
    )
    return 2 * R * math.asin(math.sqrt(a))


def is_same_place(
    candidate_name: str | None,
    candidate_lat: float,
    candidate_lng: float,
    exclude_name: str | None,
    ref_lat: float,
    ref_lng: float,
    distance_threshold_km: float = 0.3,
    similarity_threshold: float = 0.6,
) -> bool:
    """직선거리가 충분히 가깝고(distance_threshold_km 이내) 이름도 유사하면(similarity_threshold 이상)
    같은 실제 장소(크로스 소스 중복)로 판단. 둘 중 하나만으로는 오탐 위험이 크므로 AND로 검증."""
    distance_km = _haversine_km(candidate_lat, candidate_lng, ref_lat, ref_lng)
    if distance_km > distance_threshold_km:
        return False

    n1, n2 = _normalize_name(candidate_name), _normalize_name(exclude_name)
    if not n1 or not n2:
        return False

    similarity = SequenceMatcher(None, n1, n2).ratio()
    return similarity >= similarity_threshold


def exclude_same_place(
    places: list,
    exclude_name: str | None,
    ref_lat: float,
    ref_lng: float,
) -> list:
    """exclude_name/좌표가 주어지면, 그와 같은 실제 장소로 판단되는 후보를 제거."""
    if not exclude_name:
        return places
    return [
        p for p in places if not is_same_place(p.name, p.lat, p.lng, exclude_name, ref_lat, ref_lng)
    ]


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


async def enrich_with_travel_time(places, current_lat, current_lng, transport="CAR"):
    async def attach(p):
        result = await get_travel_time(current_lat, current_lng, p.lat, p.lng, transport=transport)
        p.travel_minutes = result["travel_minutes"] if result else None
        p.distance = result["distance"] if result else None
        p.distance_km = result["distance_km"] if result else None
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
        "distance": getattr(p, "distance", None),
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
