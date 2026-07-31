import json

import httpx

from app.core.config import settings

ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"


async def get_ai_final_pick(candidates: list[dict], situation: dict) -> list[dict] | None:
    candidate_summary = [
        {
            "place_id": c["place_id"],
            "name": c["name"],
            "category_tag": c["category_tag"],
            "travel_time_minutes": c["travel_time_minutes"],
            "rating": c["rating"],
        }
        for c in candidates
    ]

    prompt = f"""상황: {situation['situation_description']}
            남은 이용가능시간: {situation['available_minutes']}분

            후보 장소 목록(반드시 이 중에서만 선택):
            {json.dumps(candidate_summary, ensure_ascii=False)}

            이 중 가장 적합한 3곳을 선택하고, 각각 이유를 한 문장으로 설명해줘.
            반드시 아래 JSON 배열 형식으로만 응답(다른 텍스트 없이):
            [{{"place_id": "...", "reason": "..."}}, {{"place_id": "...", "reason": "..."}}, {{"place_id": "...", "reason": "..."}}]"""

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            res = await client.post(
                ANTHROPIC_URL,
                headers={
                    "x-api-key": settings.CLAUDE_API_KEY,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": "claude-haiku-4-5-20251001",
                    "max_tokens": 500,
                    "messages": [{"role": "user", "content": prompt}],
                },
            )
            res.raise_for_status()
            data = res.json()
            raw_text = data["content"][0]["text"]

        cleaned = raw_text.strip().removeprefix("```json").removesuffix("```").strip()
        return json.loads(cleaned)
    except httpx.HTTPStatusError as e:
        print(f"[AI 호출 실패] 상태코드={e.response.status_code}")
        print(f"[AI 응답 본문] {e.response.text}")
        return None
    except Exception as e:
        print(f"[AI 호출 실패] {type(e).__name__}: {e}")
        return None