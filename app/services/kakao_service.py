import httpx

from app.core.config import settings

KAKAO_KEYWORD_URL = "https://dapi.kakao.com/v2/local/search/keyword.json"


async def search_kakao_place(query: str) -> list[dict]:
    """카카오 Local API 키워드 장소 검색."""
    headers = {"Authorization": f"KakaoAK {settings.KAKAO_REST_API_KEY}"}
    params = {"query": query}

    async with httpx.AsyncClient(timeout=10.0) as client:
        res = await client.get(KAKAO_KEYWORD_URL, headers=headers, params=params)
        res.raise_for_status()
        data = res.json()

    return data.get("documents", [])
