import asyncio

from app.services.chat_session_service import append_message, create_session, get_conversation


async def main():
    session_id = await create_session(
        {"role": "user", "content": "청양 문화예술회관 갈려는데 휴일이라 못가"}
    )
    print(f"세션 생성됨: {session_id}")

    conversation = await get_conversation(session_id)
    print(f"대화 이력: {conversation}")

    updated = await append_message(
        session_id, {"role": "assistant", "content": "지금 계신 위치를 알려주시겠어요?"}
    )
    print(f"메시지 추가 후: {updated}")


if __name__ == "__main__":
    asyncio.run(main())
