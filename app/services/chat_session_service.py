import json
import uuid

from app.core.redis_client import redis_client

SESSION_TTL_SECONDS = 1800


async def create_session(initial_message: dict) -> str:
    """새 대화 세션 생성. session_id 반환."""
    session_id = str(uuid.uuid4())
    conversation = [initial_message]
    await redis_client.set(
        f"chat_session:{session_id}",
        json.dumps(conversation, ensure_ascii=False),
        ex=SESSION_TTL_SECONDS,
    )
    return session_id


async def get_conversation(session_id: str) -> list[dict] | None:
    """세션 ID로 대화 이력 조회. 없거나 만료됐으면 None."""
    data = await redis_client.get(f"chat_session:{session_id}")
    if data is None:
        return None
    return json.loads(data)


async def append_message(session_id: str, message: dict) -> list[dict] | None:
    """세션에 메시지 하나 추가하고, 전체 대화 이력 반환. 세션 없으면 None."""
    conversation = await get_conversation(session_id)
    if conversation is None:
        return None
    conversation.append(message)
    await redis_client.set(
        f"chat_session:{session_id}",
        json.dumps(conversation, ensure_ascii=False),
        ex=SESSION_TTL_SECONDS,
    )
    return conversation


async def save_extracted(session_id: str, extracted: dict) -> None:
    """세션에 지금까지 파악된 정보(extracted)를 별도로 저장."""
    await redis_client.set(
        f"chat_extracted:{session_id}",
        json.dumps(extracted, ensure_ascii=False),
        ex=SESSION_TTL_SECONDS,
    )


async def get_extracted(session_id: str) -> dict | None:
    """세션에 저장된 extracted 정보 조회."""
    data = await redis_client.get(f"chat_extracted:{session_id}")
    if data is None:
        return None
    return json.loads(data)
