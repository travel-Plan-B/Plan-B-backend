import asyncio
from app.services.google_places_service import enrich_with_google_rating


async def main():
    result1 = await enrich_with_google_rating(
        name="옥정호수공원", lat=37.8221988195, lng=127.0950336394
    )
    print("옥정호수공원:", result1)

    result2 = await enrich_with_google_rating(
        name="황금어장", lat=37.5215384311, lng=129.1161457818
    )
    print("황금어장:", result2)


if __name__ == "__main__":
    asyncio.run(main())