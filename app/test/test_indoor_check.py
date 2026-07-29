import asyncio

from app.core.database import SessionLocal
from app.services.place_repository import get_or_ingest_places


async def main():
    db = SessionLocal()
    places = await get_or_ingest_places(db, lat=36.4480400518613, lng=126.799426057302)

    print("=== 관광지로 분류된 것들의 원본 카테고리 코드 ===")
    for p in places:
        if p.category_tag == "관광지":
            print(f"{p.name:20} | raw_category_source={p.raw_category_source}")

    db.close()


if __name__ == "__main__":
    asyncio.run(main())
