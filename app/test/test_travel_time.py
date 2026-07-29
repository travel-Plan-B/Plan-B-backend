# app/test/test_travel_time.py
import asyncio

from app.services.kakao_mobility_service import get_travel_time


async def main():
    result = await get_travel_time(
        origin_lat=37.8227690565604,
        origin_lng=127.095012085337,
        dest_lat=37.8171697397632,
        dest_lng=126.9935,  # 임의 좌표
    )
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
