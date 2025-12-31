from fastapi import APIRouter, Depends, Body, HTTPException, UploadFile, File
import uuid

from app.account.adapter.input.web.account_router import get_current_account_id
from app.config.database.session import get_db_session
from sqlalchemy.orm import Session

# 전역 객체는 상태가 없는 것들만 유지
from app.config.call_gpt import CallGPT
from app.config.s3_service import S3Service
from app.conversation.adapter.input.web.request.chat_feedback_request import ChatFeedbackRequest
from app.conversation.application.usecase.end_chat_usecase import EndChatUseCase
from app.conversation.application.usecase.get_chat_room_status_usecase import GetChatRoomStatusUseCase
from app.conversation.application.usecase.delete_chat_usecase import DeleteChatUseCase
from app.conversation.application.usecase.get_chat_message_usecase import GetChatMessagesUseCase
from app.conversation.application.usecase.get_chat_room_usecase import GetChatRoomsUseCase
from app.conversation.application.usecase.insert_chat_feedback_usecase import ChatFeedbackUsecase
from app.conversation.infrastructure.repository.chat_feedback_repository_impl import ChatFeedbackRepositoryImpl
from app.conversation.infrastructure.repository.chat_room_repository_impl import ChatRoomRepositoryImpl
from app.conversation.infrastructure.repository.usage_meter_impl import UsageMeterImpl
from app.config.security.message_crypto import AESEncryption
from app.conversation.adapter.output.stream.stream_adapter import StreamAdapter

crypto_service = AESEncryption()
llm_chat_port = CallGPT()
usage_meter = UsageMeterImpl()

conversation_router = APIRouter(tags=["conversation"])


@conversation_router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    account_id: int = Depends(get_current_account_id)
):
    """
    S3에 저장 후, 화면에서 보여줄 수 있는 URL을 반환합니다.
    """
    s3_service = S3Service()
    try:
        url = await s3_service.upload_file(file, account_id)
        return {"file_url": url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"파일 업로드 실패: {str(e)}")

@conversation_router.get("/rooms")
async def get_my_rooms(
        account_id: int = Depends(get_current_account_id),
        db: Session = Depends(get_db_session)  # 1. 세션 주입 필요
):
    # 2. 레포지토리에 현재 세션을 넣어서 생성
    room_repo = ChatRoomRepositoryImpl(db)
    uc = GetChatRoomsUseCase(room_repo)

    rooms = await uc.execute(account_id)
    return rooms


@conversation_router.post("/chat/stream-auto")
async def stream_chat_auto(
        account_id: int = Depends(get_current_account_id),
        message: str = Body(..., embed=True),
        room_id: str | None = Body(default=None, embed=True),
        file_urls: list[str] = Body(default=[], embed=True),
        contents_type: str = Body(default="TEXT", embed=True),
        db: Session = Depends(get_db_session)
):
    from app.conversation.infrastructure.repository.chat_room_repository_impl import ChatRoomRepositoryImpl
    from app.conversation.infrastructure.repository.chat_message_repository_impl import ChatMessageRepositoryImpl
    from app.conversation.application.usecase.stream_chat_usecase import StreamChatUsecase

    chat_room_repo = ChatRoomRepositoryImpl(db)
    chat_message_repo = ChatMessageRepositoryImpl(db)

    # 1. room_id 판단 로직 보정
    # 프론트에서 'null' 문자열이 오거나 아예 없을 때를 대비
    is_new_room = room_id is None or room_id == "" or room_id == "null"

    if is_new_room:
        current_room_id = str(uuid.uuid4())
        title_preview = message[:20].replace("\n", " ")
        # 새 방 생성
        await chat_room_repo.create(
            room_id=current_room_id,
            account_id=account_id,
            title=title_preview,
            category="GENERAL",
            division="DEFAULT",
            out_api="FALSE"
        )
    else:
        current_room_id = room_id
        # 기존 방 존재 여부 확인
        room_exists = await chat_room_repo.find_by_id(current_room_id)
        if not room_exists:
            raise HTTPException(status_code=404, detail="Room not found")

    # 2. UseCase 생성 (이미 검증된 current_room_id 사용)
    usecase = StreamChatUsecase(
        chat_room_repo=chat_room_repo,
        chat_message_repo=chat_message_repo,
        llm_chat_port=llm_chat_port,
        usage_meter=usage_meter,
        crypto_service=crypto_service
    )

    generator = usecase.execute(
        room_id=current_room_id,
        account_id=account_id,
        message=message,
        contents_type=contents_type,
        file_urls=file_urls,
    )

    return StreamAdapter.to_streaming_response(generator)


# 피드백 생성 (POST)
@conversation_router.post("/feedback")
async def add_feedback(
        feedback_req: ChatFeedbackRequest,
        account_id: int = Depends(get_current_account_id),
        db: Session = Depends(get_db_session)
):
    chat_feedback_repo = ChatFeedbackRepositoryImpl(db)
    use_case = ChatFeedbackUsecase(chat_feedback_repo)

    success = await use_case.execute_feedback(account_id, feedback_req)

    if not success:
        raise HTTPException(status_code=400, detail="피드백 저장에 실패했습니다.")

    return {"message": "피드백이 성공적으로 등록되었습니다."}


# 피드백 수정 (PUT/PATCH)
@conversation_router.put("/feedback")
async def update_feedback(
        feedback_req: ChatFeedbackRequest,
        account_id: int = Depends(get_current_account_id),
        db: Session = Depends(get_db_session)
):
    chat_feedback_repo = ChatFeedbackRepositoryImpl(db)
    use_case = ChatFeedbackUsecase(chat_feedback_repo)

    # 수정 로직 실행
    success = await use_case.execute_feedback(account_id, feedback_req)

    if not success:
        raise HTTPException(status_code=404, detail="수정할 피드백을 찾을 수 없습니다.")

    return {"message": "피드백이 성공적으로 수정되었습니다."}



@conversation_router.delete("/rooms/{room_id}")
async def delete_chat_room(
        room_id: str,
        account_id: int = Depends(get_current_account_id),
        db: Session = Depends(get_db_session)
):
    chat_room_repo = ChatRoomRepositoryImpl(db)

    usecase = DeleteChatUseCase(chat_room_repo)

    # 3. 실행
    success = await usecase.execute(room_id=room_id, account_id=account_id)

    if not success:
        raise HTTPException(status_code=404, detail="채팅방을 찾을 수 없거나 삭제 권한이 없습니다.")

    return {"message": "채팅방과 모든 메시지가 성공적으로 삭제되었습니다."}


@conversation_router.patch("/rooms/{room_id}/end")
async def end_chat(
    room_id: str,
    account_id: int = Depends(get_current_account_id),
    db: Session = Depends(get_db_session),
):
    room_repo = ChatRoomRepositoryImpl(db)
    uc = EndChatUseCase(room_repo)

    await uc.execute(room_id=room_id, account_id=account_id)
    return {"room_id": room_id, "status": "ENDED"}

@conversation_router.get("/rooms/{room_id}/status")
async def get_room_status(
    room_id: str,
    account_id: int = Depends(get_current_account_id),
    db: Session = Depends(get_db_session),
):
    repo = ChatRoomRepositoryImpl(db)
    uc = GetChatRoomStatusUseCase(repo)
    status = await uc.execute(room_id, account_id)
    return {"room_id": room_id, "status": status}

@conversation_router.get("/rooms/{room_id}/messages")
async def get_room_messages(
        room_id: str,
        account_id: int = Depends(get_current_account_id),
        db: Session = Depends(get_db_session)
):
    # 2. 함수 안에서 필요한 리포지토리 생성
    from app.conversation.infrastructure.repository.chat_message_repository_impl import ChatMessageRepositoryImpl

    chat_message_repo = ChatMessageRepositoryImpl(db)

    # 3. UseCase 실행
    uc = GetChatMessagesUseCase(chat_message_repo, crypto_service)
    return await uc.execute(room_id, account_id)