import asyncio

from app.services.weather_service import get_current_weather, latlng_to_grid


async def main():
    nx, ny = latlng_to_grid(36.4480400518613, 126.799426057302)
    print(f"격자좌표: nx={nx}, ny={ny}")

    weather = await get_current_weather(nx, ny)
    print(weather)


if __name__ == "__main__":
    asyncio.run(main())
