import asyncio
from app.core.database import SessionLocal
from app.services.place_repository import get_or_ingest_places


async def main():
    db = SessionLocal()

    print("=== 1차 호출 (청양) ===")
    places = await get_or_ingest_places(db, lat=36.4480400518613, lng=126.799426057302)
    print(f"결과: {len(places)}개\n")

    print("=== 2차 호출 (같은 좌표, 바로 다시) ===")
    places2 = await get_or_ingest_places(db, lat=36.4480400518613, lng=126.799426057302)
    print(f"결과: {len(places2)}개")

    db.close()


if __name__ == "__main__":
    asyncio.run(main())