from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.ingest_places import upsert_place
from app.services.kakao_service import search_kakao_place
from app.services.normalize_service import normalize_kakao_place
from app.services.place_repository import get_or_ingest_places
from app.services.tourapi_service import (
    fetch_tourapi_places_by_category,
)

router = APIRouter(prefix="/places", tags=["places"])


# @router.get("/debug")
# async def debug_places(
#     lat: float = Query(..., description="위도"),
#     lng: float = Query(..., description="경도"),
#     db: Session = Depends(get_db),
# ):
#     """[확인용] DB 캐싱+적재 로직이 잘 도는지 눈으로 보기 위한 임시 엔드포인트.
#     최종 추천 API가 아님 - 필터링/정렬/AI 선택 전 원본 데이터를 그대로 보여줌."""
#     places = await get_or_ingest_places(db, lat=lat, lng=lng)

#     return {
#         "count": len(places),
#         "places": [
#             {
#                 "name": p.name,
#                 "category_tag": p.category_tag,
#                 "is_indoor": p.is_indoor,
#                 "rating": float(p.rating) if p.rating is not None else None,
#                 "user_rating_count": p.user_rating_count,
#                 "address": p.address,
#                 "lat": p.lat,
#                 "lng": p.lng,
#             }
#             for p in places
#         ],
#     }


# @router.get("/debug-by-category")
# async def debug_places_by_category(
#     lat: float = Query(..., description="위도"),
#     lng: float = Query(..., description="경도"),
#     content_type_id: str = Query(
#         ..., description="TourAPI 대분류 코드 (예: 14=문화시설, 39=음식점)"
#     ),
# ):
#     """[확인용] 디테일탭 - 카테고리 지정 검색이 잘 도는지 확인하는 임시 엔드포인트."""
#     places, used_radius = await fetch_tourapi_places_by_category(
#         lat=lat, lng=lng, content_type_id=content_type_id
#     )

#     return {
#         "used_radius": used_radius,
#         "count": len(places),
#         "places": [
#             {"name": p.get("title"), "cat3": p.get("cat3"), "contenttypeid": p.get("contenttypeid")}
#             for p in places
#         ],
#     }


@router.get("/search")
async def search_places(
    query: str = Query(..., description="장소명 또는 주소"),
    db: Session = Depends(get_db),
):
    """디테일탭 - 담아둘 장소 검색. 검색 결과를 Place 테이블에도 저장해서
    나중에 '이 장소와 비슷한 곳' 검색 시 기준으로 쓸 수 있게 함."""
    raw_results = await search_kakao_place(query)

    saved_places = []
    for item in raw_results:
        normalized = normalize_kakao_place(item)
        if normalized is None:
            continue
        upsert_place(db, normalized)
        saved_places.append(normalized)

    db.commit()

    return {
        "count": len(saved_places),
        "places": saved_places,
    }
