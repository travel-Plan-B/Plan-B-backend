import asyncio

from app.services.tourapi_service import fetch_tourapi_places_expanding


async def main():
    places, used_radius = await fetch_tourapi_places_expanding(
        lat=37.4256131888095, lng=126.700683721051
    )
    print(f"반경 {used_radius}m 에서 총 {len(places)}개 결과\n")

    for p in places:
        if p.get("contenttypeid") == "15":
            print(p)
            print("---")


if __name__ == "__main__":
    asyncio.run(main())
