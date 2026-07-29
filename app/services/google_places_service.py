import httpx

from app.core.config import settings

TEXT_SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"


async def enrich_with_google_rating(
    name: str, lat: float, lng: float, max_distance_km: float = 1.0
) -> dict | None:
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": settings.GOOGLE_PLACES_API_KEY,
        "X-Goog-FieldMask": "places.displayName,places.rating,places.userRatingCount,places.location",
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
        print(f"[DEBUG] '{name}' - Google 검색 결과 자체가 0건")
        return None

    top = places[0]
    google_lat = top.get("location", {}).get("latitude")
    google_lng = top.get("location", {}).get("longitude")
    found_name = top.get("displayName", {}).get("text")

    if google_lat is None or google_lng is None:
        return None

    distance = ((lat - google_lat) ** 2 + (lng - google_lng) ** 2) ** 0.5 * 111

    if distance > max_distance_km:
        print(
            f"[DEBUG] '{name}' - Google이 찾은 곳: '{found_name}' (거리 {distance:.1f}km, 매칭 실패로 처리)"
        )
        return None

    return {
        "rating": top.get("rating"),
        "user_rating_count": top.get("userRatingCount"),
    }
