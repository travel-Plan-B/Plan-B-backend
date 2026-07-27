import asyncio
from datetime import datetime
from app.core.database import SessionLocal
from app.models.place import Place
from app.services.tourapi_service import fetch_tourapi_places_expanding
from app.services.google_places_service import enrich_with_google_rating
from app.services.normalize_service import normalize_tourapi_place


def upsert_place(db, data: dict):
    existing = (
        db.query(Place)
        .filter_by(source=data["source"], source_id=data["source_id"])
        .first()
    )
    if existing:
        for key, value in data.items():
            setattr(existing, key, value)
        existing.last_synced_at = datetime.utcnow()
    else:
        db.add(Place(**data, last_synced_at=datetime.utcnow()))


async def ingest(db, lat: float, lng: float):
    """db 세션을 파라미터로 받음 - 더 이상 자체적으로 세션을 만들지 않음."""
    places, used_radius = await fetch_tourapi_places_expanding(lat, lng)
    print(f"TourAPI 반경 {used_radius}m 에서 {len(places)}개 조회됨\n")

    saved, skipped = 0, 0

    for item in places:
        normalized = normalize_tourapi_place(item)
        if normalized is None:
            skipped += 1
            continue

        google_data = await enrich_with_google_rating(
            name=normalized["name"], lat=normalized["lat"], lng=normalized["lng"]
        )
        if google_data:
            normalized["rating"] = google_data["rating"]
            normalized["user_rating_count"] = google_data["user_rating_count"]

        upsert_place(db, normalized)
        saved += 1
        print(f"저장: {normalized['name']} ({normalized['category_tag']})")

    print(f"\n완료 — 저장 {saved}건 / 제외 {skipped}건")


if __name__ == "__main__":
    async def _standalone_run():
        db = SessionLocal()
        await ingest(db, lat=37.8227690565604, lng=127.095012085337)
        db.commit()
        db.close()

    asyncio.run(_standalone_run())