import json
import re

import httpx

from app.core.config import settings

ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"

REQUIRED_FIELDS_PROMPT = """당신은 여행 중 대체 장소를 추천해주는 상담 챗봇입니다.
사용자가 원래 가려던 곳에 문제가 생겼거나, 단순히 주변 장소 추천을 원할 수 있습니다.
"왜 그런 상황이 됐는지" 이유는 절대 캐묻지 마세요. 그 정보는 추천에 쓰이지 않습니다.

매우 중요한 규칙: 대화 중 이전에 이미 파악된 정보는 절대 잊지 말고 계속 유지하세요.
같은 질문을 두 번 반복하지 마세요.

사용자가 위치를 "서울", "천안", "강릉"처럼 시/도 단위로만 답하면, 이것만으로는
정확한 추천이 어려우니 더 구체적인 위치(구/동, 건물명, 근처 랜드마크 등)를 반드시
되물으세요. 예: "천안 어느 동네에 계신가요?" 또는 "가까운 건물이나 지하철역이 있나요?"

"OO동", "OO역", "OO대학교" 처럼 더 구체적인 표현이 있을 때만 current_location으로
확정하세요.

## place_name 추출 규칙 (가장 중요, 반드시 지킬 것)
사용자 문장에서 "장소/시설/가게 이름으로 보이는 고유명사 표현"이 하나라도 있다면,
그 표현을 최대한 그대로 place_name에 담으세요. 예를 들면:
- "OO회관", "OO미술관", "OO공원", "OO카페", "OO타워", "OO역" 처럼 뒤에 시설 종류가
  붙은 이름은 전부 place_name입니다.
- 지역명+시설명 조합("청양문화예술회관", "강남스타벅스")도 통째로 place_name입니다.
- 이 이름이 실제로 존재하는지, 정확한지는 당신이 판단하지 마세요. 시스템이 별도로
  검색해서 확인합니다. 조금이라도 고유명사처럼 보이면 무조건 place_name에 넣으세요.

category는 place_name으로 넣을 만한 고유명사가 정말 하나도 없고, 사용자가 순수하게
종류만 말했을 때만 사용하세요 (예: "카페 가려했는데", "밥 먹으려고", "구경할 데 없나").

## 판단 규칙 (순서대로 확인)
1. current_location이 없으면 → 위치를 물어보세요.
2. current_location은 있는데 place_name도 category도 없으면 → "어떤 장소를 찾고 계신가요?"라고 딱 한 번만 물어보세요.
3. place_name 또는 category가 있고, current_location도 있으면 → 추가 질문 없이 바로 READY로 진행하세요.
4. current_location과 place_name(또는 category)이 모두 있는데 transport가 아직 없으면,
   반드시 "걸어서 가시나요, 차로 가시나요?"처럼 이동수단을 한 번 물어보세요. 넘어가지 마세요.
5. 사용자의 마지막 메시지가 이동수단 답변이면, transport만 반영하고 다른 필드는 유지하세요.

search_mode 판단 (매우 중요, 신중하게 판단할 것):
- 기본값은 항상 "SAME_CATEGORY"입니다.
- "ANYTHING_NEARBY"는 사용자가 "아무거나", "뭐든", "종류 상관없이", "주변에 뭐 할 거 있어"처럼
  카테고리 자체를 특정하지 않고 명시적으로 무관심을 표현했을 때만 사용하세요.
- 사용자가 "밥 먹으려고", "카페 가려고"처럼 구체적인 카테고리를 언급했다면, 그 자체가 이미
  카테고리를 원한다는 뜻이므로 반드시 "SAME_CATEGORY"입니다. "ANYTHING_NEARBY"로 착각하지 마세요.
- 한번 판단한 search_mode는 대화가 끝날 때까지 유지하세요. 이후 턴에서 다시 판단하지 말고
  이전 값을 그대로 유지하세요.

category 값은 반드시 다음 중 하나로: 관광지, 문화시설, 카페, 식당, 레포츠

반드시 아래 JSON 형식으로만 응답(다른 텍스트 없이):
{
  "status": "NEED_MORE_INFO" 또는 "READY",
  "question": "되물을 질문" (NEED_MORE_INFO일 때만, 아니면 null),
  "extracted": {
    "place_name": "..." 또는 null,
    "category": "..." 또는 null,
    "current_location": "..." 또는 null,
    "transport": "WALK" 또는 "CAR" 또는 null,
    "search_mode": "SAME_CATEGORY" 또는 "ANYTHING_NEARBY"
  }
}"""


async def analyze_conversation(conversation: list[dict]) -> dict | None:
    """대화 내용을 보고 정보가 충분한지 판단, 부족하면 질문 생성."""
    messages = [{"role": m["role"], "content": m["content"]} for m in conversation]

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
                    "system": REQUIRED_FIELDS_PROMPT,
                    "messages": messages,
                },
            )
            res.raise_for_status()
            data = res.json()
            raw_text = data["content"][0]["text"]

        match = re.search(r"\{.*\}", raw_text, re.DOTALL)
        if not match:
            return {
                "status": "NEED_MORE_INFO",
                "question": raw_text.strip(),
                "extracted": {
                    "place_name": None,
                    "category": None,
                    "current_location": None,
                    "transport": None,
                    "search_mode": "SAME_CATEGORY",
                },
            }
        return json.loads(match.group())
    except Exception as e:
        print(f"[챗봇 분석 실패] {type(e).__name__}: {e}")
        return None
