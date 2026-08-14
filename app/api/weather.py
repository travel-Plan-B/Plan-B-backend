from fastapi import APIRouter, Query

from app.services.weather_service import get_current_weather, latlng_to_grid

router = APIRouter(prefix="/weather", tags=["weather"])


@router.get("")
async def get_weather(
    lat: float = Query(..., description="위도"),
    lng: float = Query(..., description="경도"),
):
    nx, ny = latlng_to_grid(lat, lng)
    weather = await get_current_weather(nx, ny)

    if weather is None:
        return {
            "success": False,
            "error": {"code": "WEATHER_UNAVAILABLE", "message": "날씨 정보를 가져올 수 없습니다."},
        }

    return {"success": True, "data": weather}
