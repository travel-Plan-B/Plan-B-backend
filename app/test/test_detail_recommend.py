import asyncio

from app.core.database import SessionLocal
from app.services.place_repository import get_detail_recommendations


async def main():
    db = SessionLocal()

    candidates = await get_detail_recommendations(
        db,
        place_id="8199114",  # 경포해수욕장
        source="kakao",
        prev_location={
            "lat": 37.8034055083125,
            "lng": 128.910210247605,
        },  # 경포해수욕장 자체 좌표(=출발지 근처)
        next_location=None,
        priority="MINIMIZE_TRAVEL",
    )

    for c in candidates:
        print(
            f"{c['name']:15} | {c['category_tag']} | 이전→여기 {c['travel_time_from_prev_minutes']}분 | 체류 {c['estimated_duration_minutes']}분"
        )

    db.close()


if __name__ == "__main__":
    asyncio.run(main())
