from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.chat_analysis_service import analyze_conversation
from app.services.chat_recommend_service import recommend_from_chat
from app.services.chat_session_service import (
    append_message,
    create_session,
    get_extracted,
    save_extracted,
)

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    session_id: str | None = None
    message: str


@router.post("")
async def chat(request: ChatRequest, db: Session = Depends(get_db)):
    user_message = {"role": "user", "content": request.message}

    if request.session_id is None:
        session_id = await create_session(user_message)
        conversation = [user_message]
        previous_extracted: dict = {}
    else:
        conversation = await append_message(request.session_id, user_message)
        if conversation is None:
            session_id = await create_session(user_message)
            conversation = [user_message]
            previous_extracted = {}
        else:
            session_id = request.session_id
            previous_extracted = await get_extracted(session_id) or {}

    analysis = await analyze_conversation(conversation)

    if analysis is None:
        return {
            "session_id": session_id,
            "type": "ERROR",
            "message": "죄송해요, 지금 답변을 만드는 데 문제가 생겼어요. 다시 시도해주시겠어요?",
        }

    # 새로 추출된 값과 이전 값을 병합 - 새 값이 None이면 이전 값 유지
    merged_extracted = {**previous_extracted}
    for key, value in analysis["extracted"].items():
        if value is not None:
            merged_extracted[key] = value

    await save_extracted(session_id, merged_extracted)

    # 병합된 값 기준으로 다시 판단
    has_target = merged_extracted.get("place_name") or merged_extracted.get("category")
    has_location = merged_extracted.get("current_location")
    is_anything_nearby = merged_extracted.get("search_mode") == "ANYTHING_NEARBY"

    if is_anything_nearby:
        status = "READY" if has_location else "NEED_MORE_INFO"
    else:
        status = "READY" if (has_target and has_location) else "NEED_MORE_INFO"

    if status == "NEED_MORE_INFO":
        question = analysis["question"] or "필요한 정보를 조금 더 알려주시겠어요?"
        assistant_message = {"role": "assistant", "content": question}
        await append_message(session_id, assistant_message)
        return {"session_id": session_id, "type": "QUESTION", "message": question}

    # READY 상태 - 실제 추천 실행
    print(
        f"[DEBUG] place_name={merged_extracted.get('place_name')!r}, category={merged_extracted.get('category')!r}"
    )
    recommend_result = await recommend_from_chat(
        db,
        place_name=merged_extracted.get("place_name"),
        category=merged_extracted.get("category"),
        current_location=merged_extracted["current_location"],
        transport=merged_extracted.get("transport") or "CAR",
        search_mode=merged_extracted.get("search_mode") or "SAME_CATEGORY",
    )

    if not recommend_result["success"]:
        error_messages = {
            "PLACE_NOT_FOUND": "말씀하신 장소를 찾지 못했어요. 정확한 이름을 다시 알려주시겠어요?",
            "LOCATION_NOT_FOUND": "현재 위치를 찾지 못했어요. 좀 더 구체적으로 알려주시겠어요?",
            "CATEGORY_NOT_SUPPORTED": "죄송해요, 이 장소는 지원하지 않는 카테고리예요.",
        }
        message = error_messages.get(
            recommend_result["reason"], "추천을 만드는 데 문제가 생겼어요."
        )
        assistant_message = {"role": "assistant", "content": message}
        await append_message(session_id, assistant_message)
        return {"session_id": session_id, "type": "ERROR", "message": message}

    return {
        "session_id": session_id,
        "type": "RECOMMENDATION",
        "data": recommend_result["data"],
    }
