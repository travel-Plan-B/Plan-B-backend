from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.core.database import get_db
from app.services.place_repository import get_detail_recommendations

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


class Location(BaseModel):
    lat: float
    lng: float


class DetailRecommendRequest(BaseModel):
    item_id: str
    place_id: str
    source: str
    prev_item_location: Location | None = None
    next_item_location: Location | None = None
    priority: str = "MINIMIZE_TRAVEL"


@router.post("/detail")
async def recommend_detail(request: DetailRecommendRequest, db: Session = Depends(get_db)):
    prev = request.prev_item_location.dict() if request.prev_item_location else None
    next_loc = request.next_item_location.dict() if request.next_item_location else None

    candidates = await get_detail_recommendations(
        db,
        place_id=request.place_id,
        source=request.source,
        prev_location=prev,
        next_location=next_loc,
        priority=request.priority,
    )

    return {
        "item_id": request.item_id,
        "candidates": candidates,
    }