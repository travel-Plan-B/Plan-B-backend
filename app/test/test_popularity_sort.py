import asyncio

from app.core.database import SessionLocal
from app.services.place_repository import get_or_ingest_places
from app.services.simple_service import sort_by_popularity


async def main():
    db = SessionLocal()
    places = await get_or_ingest_places(db, lat=36.4480400518613, lng=126.799426057302)

    sorted_places = sort_by_popularity(places)

    print("=== 리뷰수 기준 정렬 결과 ===")
    for p in sorted_places:
        print(f"{p.name:20} | 리뷰수={p.user_rating_count}")

    db.close()


if __name__ == "__main__":
    asyncio.run(main())