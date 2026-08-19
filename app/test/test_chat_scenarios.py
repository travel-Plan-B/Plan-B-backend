import asyncio

from app.services.chat_analysis_service import analyze_conversation

SCENARIOS = [
    {
        "name": "케이스1: 문제상황 없이 순수 추천 요청",
        "turns": [
            "배고파서 밥먹을려 하는데 주변 맛집 없어?",
            "청양에 있어",
        ],
    },
    {
        "name": "케이스2: 장소명 + 문제상황 있는 경우",
        "turns": [
            "청양 문화예술회관 갈려는데 휴일이라 못가",
            "청양읍에 있어",
            "걸어서 갈거야",
        ],
    },
    {
        "name": "케이스3: 카테고리만 언급, 같은 카테고리 원함",
        "turns": [
            "카페 가려 했는데 비와서 못가. 다른 카페 있어?",
            "천안 신부동이야",
        ],
    },
    {
        "name": "케이스4: 카테고리 무관, 아무거나 원함",
        "turns": [
            "야외활동 하려 했는데 비와서 못해. 주변에 뭐 할 거 있어?",
            "청양읍이야",
            "차 타고 갈거야",
        ],
    },
    {
        "name": "케이스5: 애매한 표현(야외카페처럼 실제 없는 이름)",
        "turns": [
            "야외카페 가려했는데 비와서 못가",
            "청양이야",
        ],
    },
    {
        "name": "케이스6: 위치를 시/도 단위로만 답함 (구체화 필요)",
        "turns": [
            "배고파서 밥먹을려 하는데 주변 맛집 없어?",
            "천안에 있어",
            "천안 신부동이야",
        ],
    },
]


async def run_scenario(scenario: dict):
    print(f"\n{'=' * 50}")
    print(f"[{scenario['name']}]")
    print(f"{'=' * 50}")

    conversation = []
    merged_extracted = {}

    for turn in scenario["turns"]:
        conversation.append({"role": "user", "content": turn})
        print(f"\n사용자: {turn}")

        result = await analyze_conversation(conversation)
        if result is None:
            print("  → 분석 실패")
            break

        # 실제 chat.py와 동일한 병합 로직
        for key, value in result["extracted"].items():
            if value is not None:
                merged_extracted[key] = value

        has_target = merged_extracted.get("place_name") or merged_extracted.get("category")
        has_location = merged_extracted.get("current_location")
        is_anything_nearby = merged_extracted.get("search_mode") == "ANYTHING_NEARBY"

        if is_anything_nearby:
            status = "READY" if has_location else "NEED_MORE_INFO"
        else:
            status = "READY" if (has_target and has_location) else "NEED_MORE_INFO"

        print(f"  → status: {status}")
        print(f"  → merged_extracted: {merged_extracted}")

        if status == "NEED_MORE_INFO":
            question = result["question"] or "필요한 정보를 조금 더 알려주시겠어요?"
            print(f"  → 봇 질문: {question}")
            conversation.append({"role": "assistant", "content": question})
        else:
            print("  → READY, 대화 종료")
            break


async def main():
    for scenario in SCENARIOS:
        await run_scenario(scenario)


if __name__ == "__main__":
    asyncio.run(main())
