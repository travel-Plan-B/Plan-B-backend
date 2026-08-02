import json

import httpx

import re

from app.core.config import settings

ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"


async def get_ai_final_pick(candidates: list[dict], situation: dict) -> list[dict] | None:
    candidate_summary = []
    for c in candidates:
        travel_info = c.get("travel_time_minutes")
        if travel_info is None:
            # 디테일탭 형태(양방향) 대응
            prev = c.get("travel_time_from_prev_minutes")
            next_ = c.get("travel_time_to_next_minutes")
            travel_info = (
                f"이전 장소에서 {prev}분, 다음 장소까지 {next_}분"
                if (prev is not None or next_ is not None)
                else None
            )

        candidate_summary.append(
            {
                "place_id": c["place_id"],
                "name": c["name"],
                "category_tag": c.get("category_tag"),
                "travel_time": travel_info,
                "rating": c.get("rating"),
            }
        )

    prompt = f"""상황: {situation['situation_description']}
후보 장소 목록(반드시 이 중에서만 선택):
{json.dumps(candidate_summary, ensure_ascii=False)}

이 중 가장 적합한 3곳을 선택하고, 각각 이유를 한 문장으로 작성해줘.

이유를 쓸 때 지켜야 할 것:
- 평점이나 이동시간 숫자를 그대로 나열하지 말 것 (예: "평점 4.5, 이동시간 9분이라 좋아요" 금지)
- 대신 사용자가 원래 가려던 곳을 못 가서 아쉬운 마음을 공감하면서, 이 장소가 어떤 매력이 있는지 자연스럽게 설명할 것
- 마치 친구가 대안을 추천해주듯 따뜻하고 친근한 톤으로 작성할 것
- 좋은 예시: "아쉽게도 원래 계획하신 곳은 어려울 것 같아요. 대신 가까운 거리에 아름다운 전통차 체험도 함께 즐길 수 있는 이곳은 어떠세요?"
- 나쁜 예시: "평점 4.8이고 이동시간 7분으로 접근성이 좋습니다."

반드시 아래 JSON 배열 형식으로만 응답(다른 텍스트 없이):
[{{"place_id": "...", "reason": "..."}}, {{"place_id": "...", "reason": "..."}}, {{"place_id": "...", "reason": "..."}}]"""
    ...

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

            match = re.search(r"\[.*\]", raw_text, re.DOTALL)
            if not match:
                print(f"[AI 응답에서 JSON 배열을 못 찾음] {raw_text!r}")
                return None

            return json.loads(match.group())

        cleaned = raw_text.strip().removeprefix("```json").removesuffix("```").strip()
        return json.loads(cleaned)
    except httpx.HTTPStatusError as e:
        print(f"[AI 호출 실패] 상태코드={e.response.status_code}")
        print(f"[AI 응답 본문] {e.response.text}")
        return None
    except Exception as e:
        print(f"[AI 호출 실패] {type(e).__name__}: {e}")
        return None
