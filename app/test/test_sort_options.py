import asyncio

from app.core.database import SessionLocal
from app.services.place_repository import get_or_ingest_places
from app.services.simple_service import enrich_with_travel_time, sort_places


async def main():
    db = SessionLocal()
    places = await get_or_ingest_places(db, lat=36.4480400518613, lng=126.799426057302)

    # 이동시간 계산 (임의로 현재 위치 = 같은 좌표 근처)
    places = await enrich_with_travel_time(places, current_lat=36.4480400518613, current_lng=126.799426057302)

    print("=== 가까운순 ===")
    for p in sort_places(places, "NEAREST")[:5]:
        print(f"{p.name:20} | {p.travel_minutes}분")

    print("\n=== 체류시간순 ===")
    for p in sort_places(places, "LONGEST_STAY")[:5]:
        print(f"{p.name:20} | {p.category_tag}")

    db.close()


if __name__ == "__main__":
    asyncio.run(main())