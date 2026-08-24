from fastapi import APIRouter
from pydantic import BaseModel

from app.services.kakao_mobility_service import get_travel_time
from app.services.time_service import validate_time_conflict
from app.services.kakao_mobility_service import get_travel_time

router = APIRouter(prefix="/schedule", tags=["schedule"])


class Location(BaseModel):
    lat: float
    lng: float


class NextFixedItem(BaseModel):
    start_time: str
    location: Location


class ValidateRequest(BaseModel):
    item_id: str
    new_start_time: str
    new_duration_minutes: int
    location: Location
    next_fixed_item: NextFixedItem
    transport: str = "CAR"


class TravelTimeRequest(BaseModel):
    origin: Location
    destination: Location
    transport: str = "CAR"


@router.post("/validate")
async def validate_schedule(request: ValidateRequest):
    travel_result = await get_travel_time(
        request.location.lat,
        request.location.lng,
        request.next_fixed_item.location.lat,
        request.next_fixed_item.location.lng,
        transport=request.transport,
    )
    travel_minutes = travel_result["travel_minutes"] if travel_result else 0

    result = validate_time_conflict(
        new_start_time=request.new_start_time,
        new_duration_minutes=request.new_duration_minutes,
        travel_time_to_next_minutes=travel_minutes,
        next_fixed_start_time=request.next_fixed_item.start_time,
    )

    return {"success": True, "data": result}


@router.post("/travel-time")
async def calculate_travel_time(request: TravelTimeRequest):
    result = await get_travel_time(
        request.origin.lat,
        request.origin.lng,
        request.destination.lat,
        request.destination.lng,
        transport=request.transport,
    )

    if result is None:
        return {
            "success": False,
            "error": {"code": "ROUTE_NOT_FOUND", "message": "경로를 찾을 수 없습니다."},
        }

    return {
        "success": True,
        "data": {
            "travel_minutes": result["travel_minutes"],
            "distance": result["distance"],
            "distance_km": result["distance_km"],
            "estimated": result["estimated"],
        },
    }
