import asyncio

from app.core.redis_client import redis_client


async def main():
    await redis_client.set("test_key", "hello", ex=60)
    value = await redis_client.get("test_key")
    print(f"저장한 값 확인: {value}")


if __name__ == "__main__":
    asyncio.run(main())
