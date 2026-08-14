import json
import re

import httpx

from app.core.config import settings

ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"


async def get_ai_final_pick(
    candidates: list[dict], situation: dict, transport: str = "CAR"
) -> list[dict] | None:
    transport_label = "걸어서" if transport == "WALK" else "차로"

    candidate_summary = []
    for c in candidates:
        travel_info = c.get("travel_time_minutes")
        if travel_info is None:
            prev = c.get("travel_time_from_prev_minutes")
            next_ = c.get("travel_time_to_next_minutes")
            if prev is not None and next_ is not None:
                travel_info = (
                    f"{transport_label} 이전 장소에서 약 {prev}분, 다음 장소까지 약 {next_}분"
                )
            elif prev is not None:
                travel_info = f"{transport_label} 약 {prev}분"
            else:
                travel_info = None

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

이 중 가장 적합한 3곳을 선택하고, 각각 이유를 2~3개의 짧은 문장으로 작성해줘.

이유를 쓸 때 지켜야 할 것:
- 이유는 배열 형태로, 문장 2~3개로 나눠서 작성할 것 (한 문장에 다 몰아넣지 말 것)
- 공감이나 위로하는 표현("아쉬우시겠지만", "안타깝지만" 등)은 쓰지 말 것
- 이동시간을 언급할 때는 반드시 후보 목록에 있는 travel_time 값을 그대로 인용할 것, 숫자를 임의로 바꾸지 말 것
- 애매한 표현("좋은 평점") 대신, 실제 평점 수치를 근거로 들 것 (예: "평점 4.7점")
- 부자연스럽거나 어색한 단어 선택 주의 (예: "충동적으로" 같은 부정적 뉘앙스 단어는 부적절)
- 담백하고 명확한 존댓말로, 각 문장은 짧고 간결하게 작성할 것

반드시 아래 JSON 형식으로만 응답(다른 텍스트 없이):
[
  {{"place_id": "...", "reason": ["이유 문장1", "이유 문장2", "이유 문장3"]}},
  {{"place_id": "...", "reason": ["이유 문장1", "이유 문장2"]}},
  {{"place_id": "...", "reason": ["이유 문장1", "이유 문장2", "이유 문장3"]}}
]"""
    ...  # 나머지 로직(API 호출, 파싱)은 기존과 동일

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
