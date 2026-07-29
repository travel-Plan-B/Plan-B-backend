import asyncio

from app.core.database import SessionLocal
from app.services.place_repository import get_or_ingest_places
from app.services.simple_service import filter_by_category_whitelist


async def main():
    db = SessionLocal()
    places = await get_or_ingest_places(db, lat=36.4480400518613, lng=126.799426057302)

    print(f"필터링 전: {len(places)}개")
    for p in places:
        print(f"  {p.name} | {p.category_tag} | is_indoor={p.is_indoor}")

    filtered = filter_by_category_whitelist(
        places, problem_reason="WEATHER", situational_answer="OUTDOOR_ONLY"
    )
    print(f"\n필터링 후 (날씨, 실내만): {len(filtered)}개")
    for p in filtered:
        print(f"  {p.name} | {p.category_tag} | is_indoor={p.is_indoor}")

    db.close()


if __name__ == "__main__":
    asyncio.run(main())
