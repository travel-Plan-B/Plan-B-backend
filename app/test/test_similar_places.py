import asyncio

from app.core.database import SessionLocal
from app.services.place_repository import get_similar_places


async def main():
    db = SessionLocal()

    places, used_radius = await get_similar_places(db, place_id="2832200", source="tourapi")
    print(f"반경 {used_radius}m 에서 {len(places)}개 후보\n")
    for p in places:
        print(f"{p.get('title'):20} | cat3={p.get('cat3')}")

    db.close()


if __name__ == "__main__":
    asyncio.run(main())
