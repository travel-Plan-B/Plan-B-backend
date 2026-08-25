from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.ai_recommend_service import get_ai_final_pick
from app.services.kakao_mobility_service import get_travel_time
from app.services.place_repository import get_or_ingest_places
from app.services.simple_service import (
    enrich_with_travel_time,
    exclude_same_place,
    filter_by_category_whitelist,
    filter_by_duration_simple,
    place_to_dict,
    sort_places,
)
from app.services.time_service import calculate_available_minutes
from app.services.weather_service import get_current_weather, latlng_to_grid

router = APIRouter(prefix="/simple", tags=["simple"])


class Location(BaseModel):
    lat: float
    lng: float


class SimpleRecommendRequest(BaseModel):
    place_id: str | None = None
    source: str | None = None
    current_location: Location
    next_place: Location | None = None
    deadline_time: str
    current_time: str
    transport: str = "CAR"
    problem_reason: str
    situational_answer: str | None = None
    sort: str = "RECOMMENDED"
    exclude_place_name: str | None = None


@router.post("/recommendations")
async def recommend_simple(request: SimpleRecommendRequest, db: Session = Depends(get_db)):
    # 1. 장소 이용불가 + "아니요"면 추천 없이 종료
    if request.problem_reason == "PLACE_UNAVAILABLE" and request.situational_answer == "NO":
        return {
            "success": True,
            "data": {
                "ai_recommended": [],
                "more_places": [],
                "no_candidates_reason": "USER_DECLINED",
            },
        }

    # 2. 다음 일정까지 이동시간 계산 (있으면)
    travel_to_next = 0
    if request.next_place:
        result = await get_travel_time(
            request.current_location.lat,
            request.current_location.lng,
            request.next_place.lat,
            request.next_place.lng,
            transport=request.transport,
        )
        travel_to_next = result["travel_minutes"] if result else 0

    # 3. 이용가능시간 계산
    available_minutes = calculate_available_minutes(
        request.deadline_time, request.current_time, travel_to_next
    )

    places = await get_or_ingest_places(
        db, lat=request.current_location.lat, lng=request.current_location.lng
    )

    if request.place_id and request.source:
        places = [
            p
            for p in places
            if not (p.source == request.source and p.source_id == request.place_id)
        ]

    places = exclude_same_place(
        places,
        request.exclude_place_name,
        request.current_location.lat,
        request.current_location.lng,
    )

    # 날씨를 명시적으로 선택 안 한 경우, 실제 날씨를 참고해서 자동 판단
    weather_info = None
    if request.problem_reason != "WEATHER":
        nx, ny = latlng_to_grid(request.current_location.lat, request.current_location.lng)
        weather_info = await get_current_weather(nx, ny)

    is_bad_weather = False
    if weather_info:
        is_bad_weather = weather_info["sky_condition"] in ("RAIN", "RAIN_SNOW", "SNOW", "SHOWER")

    places = filter_by_category_whitelist(
        places, request.problem_reason, request.situational_answer, force_indoor=is_bad_weather
    )

    places = filter_by_duration_simple(places, available_minutes)

    if not places:
        reason = "NOT_ENOUGH_TIME" if available_minutes <= 0 else "NO_SUITABLE_PLACE"
        return {
            "success": True,
            "data": {
                "available_minutes": available_minutes,
                "ai_recommended": [],
                "more_places": [],
                "no_candidates_reason": reason,
            },
        }

    places = await enrich_with_travel_time(
        places,
        request.current_location.lat,
        request.current_location.lng,
        transport=request.transport,
    )

    MAX_DISTANCE_KM = 10
    places = [
        p
        for p in places
        if getattr(p, "distance_km", None) is None or p.distance_km <= MAX_DISTANCE_KM
    ]

    places = sort_places(places, request.sort)
    top10 = places[:10]
    top10_dicts = [place_to_dict(p) for p in top10]

    situation_text = f"사용자가 '{request.problem_reason}' 문제를 겪고 있습니다."
    if request.problem_reason == "WEATHER":
        if request.situational_answer == "OUTDOOR_ONLY":
            situation_text += " 비/악천후로 야외 활동을 피하고 싶어해서, 이미 실내 확인된 장소들만 후보로 걸러졌습니다."
        elif request.situational_answer == "WALKING_ONLY":
            situation_text += " 오래 걷는 활동을 피하고 싶어합니다."
        elif request.situational_answer == "BOTH":
            situation_text += " 야외 활동과 오래 걷는 활동을 모두 피하고 싶어하며, 이미 실내 확인된 장소들만 후보로 걸러졌습니다."
    elif request.problem_reason == "TIME_CHANGED":
        situation_text += f" 남은 이용가능시간은 {available_minutes}분입니다."
    if weather_info and is_bad_weather:
        situation_text += f" 마침 이 시간대에는 날씨 예보가 좋지 않아({weather_info['sky_condition']}), 실내 장소 위주로 안내해드립니다."

    situation = {
        "situation_description": situation_text,
        "available_minutes": available_minutes,
    }

    ai_result = await get_ai_final_pick(top10_dicts, situation, transport=request.transport)

    if ai_result:
        reason_map = {r["place_id"]: r["reason"] for r in ai_result}
        ai_recommended = [d for d in top10_dicts if d["place_id"] in reason_map]
        for d in ai_recommended:
            d["recommend_reason"] = reason_map[d["place_id"]]
        more_places = [d for d in top10_dicts if d["place_id"] not in reason_map]
    else:
        # AI 실패 시 fallback: 그냥 정렬된 순서 그대로 상위 3개
        ai_recommended = top10_dicts[:3]
        more_places = top10_dicts[3:]

    return {
        "success": True,
        "data": {
            "available_minutes": available_minutes,
            "ai_recommended": ai_recommended,
            "more_places": more_places,
        },
    }
