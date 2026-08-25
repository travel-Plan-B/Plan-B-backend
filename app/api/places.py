import asyncio

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.ingest_places import upsert_place
from app.models.place import Place
from app.services.google_places_service import (
    enrich_with_google_rating,
    get_place_details_from_google,
)
from app.services.kakao_service import search_kakao_place
from app.services.normalize_service import normalize_kakao_place

router = APIRouter(prefix="/places", tags=["places"])


@router.get("/search")
async def search_places(
    query: str = Query(..., description="장소명 또는 주소"),
    db: Session = Depends(get_db),
):
    """디테일탭 - 담아둘 장소 검색. 검색 결과를 Place 테이블에도 저장해서
    나중에 '이 장소와 비슷한 곳' 검색 시 기준으로 쓸 수 있게 함."""
    raw_results = await search_kakao_place(query)

    normalized_list = []
    for item in raw_results:
        normalized = normalize_kakao_place(item)
        if normalized is None:
            continue
        normalized_list.append(normalized)

    async def attach_image(place: dict) -> dict:
        google_data = await enrich_with_google_rating(
            name=place["name"], lat=place["lat"], lng=place["lng"]
        )
        place["image_url"] = google_data["image_url"] if google_data else None
        place["rating"] = google_data["rating"] if google_data else None
        place["user_rating_count"] = google_data["user_rating_count"] if google_data else None
        return place

    enriched_places = await asyncio.gather(*[attach_image(p) for p in normalized_list])

    for place in enriched_places:
        upsert_place(db, place)

    db.commit()

    return {
        "count": len(enriched_places),
        "places": enriched_places,
    }


@router.get("/{place_id}")
async def get_place_detail(
    place_id: str,
    source: str = Query(..., description="tourapi 또는 kakao"),
    db: Session = Depends(get_db),
):
    """추천 목록에서 장소 클릭 시 상세페이지에 필요한 정보 조회."""
    place = db.query(Place).filter_by(source=source, source_id=place_id).first()
    if place is None:
        return {"success": False, "error": "PLACE_NOT_FOUND"}

    google_detail = await get_place_details_from_google(
        name=str(place.name), lat=float(place.lat), lng=float(place.lng)
    )

    return {
        "success": True,
        "data": {
            "place_id": place.source_id,
            "name": place.name,
            "category_tag": place.category_tag,
            "address": place.address,
            "description": place.description,
            "lat": place.lat,
            "lng": place.lng,
            "rating": float(place.rating) if place.rating is not None else None,
            "user_rating_count": place.user_rating_count,
            "operating_hours": place.operating_hours,
            "parking_available": place.parking_available,
            "parking_status": place.parking_status,
            "image_urls": (
                google_detail["image_urls"]
                if google_detail
                else ([place.image_url] if place.image_url else [])
            ),
            "business_status": google_detail["business_status"] if google_detail else None,
            "business_hours": google_detail["business_hours"] if google_detail else None,
            "phone": google_detail["phone"] if google_detail else None,
            "homepage_url": google_detail["homepage_url"] if google_detail else None,
            "place_url": google_detail["place_url"] if google_detail else None,
        },
    }
