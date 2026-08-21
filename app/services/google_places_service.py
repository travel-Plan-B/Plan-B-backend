from datetime import datetime

import httpx

from app.core.config import settings

TEXT_SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"


def _format_operating_hours(opening_hours: dict | None) -> tuple[str | None, bool | None]:
    """오늘 요일 기준 운영시간을 'HH:MM-HH:MM' 형식으로 요약. (운영시간 문자열, 지금 영업중 여부) 반환."""
    if not opening_hours:
        return None, None

    open_now = opening_hours.get("openNow")
    periods = opening_hours.get("periods", [])

    today_weekday = (datetime.now().weekday() + 1) % 7  # 파이썬(월=0) -> 구글(일=0) 변환

    for period in periods:
        open_info = period.get("open", {})
        close_info = period.get("close", {})
        if open_info.get("day") == today_weekday:
            open_str = f"{open_info.get('hour', 0):02d}:{open_info.get('minute', 0):02d}"
            close_str = f"{close_info.get('hour', 0):02d}:{close_info.get('minute', 0):02d}"
            return f"{open_str}-{close_str}", open_now

    return None, open_now  # 오늘 운영시간 정보 자체가 없으면(=휴무일 가능성)


def build_photo_url(photo_name: str | None, max_width: int = 400) -> str | None:
    """Google Places photo reference를 실제 이미지 URL로 변환."""
    if not photo_name:
        return None
    return f"https://places.googleapis.com/v1/{photo_name}/media?maxWidthPx={max_width}&key={settings.GOOGLE_PLACES_API_KEY}"


async def enrich_with_google_rating(
    name: str, lat: float, lng: float, max_distance_km: float = 1.0
) -> dict | None:
    """장소명+좌표 기반으로 Google Places에서 평점/리뷰수/주차정보/운영시간을 찾아 보완.
    매칭 실패 시 None 반환."""
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": settings.GOOGLE_PLACES_API_KEY,
        "X-Goog-FieldMask": "places.displayName,"
        "places.rating,"
        "places.userRatingCount,"
        "places.location,"
        "places.parkingOptions,"
        "places.regularOpeningHours,"
        "places.photos",
    }
    body = {
        "textQuery": name,
        "locationBias": {
            "circle": {"center": {"latitude": lat, "longitude": lng}, "radius": 500.0}
        },
        "languageCode": "ko",
        "maxResultCount": 1,
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        res = await client.post(TEXT_SEARCH_URL, headers=headers, json=body)
        res.raise_for_status()
        data = res.json()

    places = data.get("places", [])
    if not places:
        return None

    top = places[0]
    google_lat = top.get("location", {}).get("latitude")
    google_lng = top.get("location", {}).get("longitude")

    if google_lat is None or google_lng is None:
        return None

    distance = ((lat - google_lat) ** 2 + (lng - google_lng) ** 2) ** 0.5 * 111

    if distance > max_distance_km:
        return None

    parking = top.get("parkingOptions", {})
    has_free_parking = any(
        [
            parking.get("freeParkingLot"),
            parking.get("freeStreetParking"),
            parking.get("freeGarageParking"),
        ]
    )
    has_paid_parking = any(
        [
            parking.get("paidParkingLot"),
            parking.get("paidStreetParking"),
            parking.get("paidGarageParking"),
        ]
    )

    if has_free_parking:
        parking_status = "FREE"
    elif has_paid_parking:
        parking_status = "PAID"
    else:
        parking_status = None

    operating_hours, open_now = _format_operating_hours(top.get("regularOpeningHours"))

    photos = top.get("photos", [])
    photo_name = photos[0].get("name") if photos else None
    image_url = build_photo_url(photo_name)

    return {
        "rating": top.get("rating"),
        "user_rating_count": top.get("userRatingCount"),
        "parking_status": parking_status,
        "operating_hours": operating_hours,
        "open_now": open_now,
        "image_url": image_url,
    }
