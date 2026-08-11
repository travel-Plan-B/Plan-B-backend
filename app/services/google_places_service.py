import httpx

from app.core.config import settings

TEXT_SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"


async def enrich_with_google_rating(name: str, lat: float, lng: float, max_distance_km: float = 1.0) -> dict | None:
    """장소명+좌표 기반으로 Google Places에서 평점/리뷰수/주차정보를 찾아 보완.
    매칭 실패 시 None 반환."""
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": settings.GOOGLE_PLACES_API_KEY,
        "X-Goog-FieldMask": "places.displayName,places.rating,places.userRatingCount,places.location,places.parkingOptions",
    }
    body = {
        "textQuery": name,
        "locationBias": {
            "circle": {
                "center": {"latitude": lat, "longitude": lng},
                "radius": 500.0
            }
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
    has_free_parking = any([
        parking.get("freeParkingLot"),
        parking.get("freeStreetParking"),
        parking.get("freeGarageParking"),
    ])
    has_paid_parking = any([
        parking.get("paidParkingLot"),
        parking.get("paidStreetParking"),
        parking.get("paidGarageParking"),
    ])

    if has_free_parking:
        parking_status = "FREE"
    elif has_paid_parking:
        parking_status = "PAID"
    else:
        parking_status = None

    return {
        "rating": top.get("rating"),
        "user_rating_count": top.get("userRatingCount"),
        "parking_status": parking_status,
    }