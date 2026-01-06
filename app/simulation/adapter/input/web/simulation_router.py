from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from starlette.responses import StreamingResponse

from app.config.database.session import get_db_session
from app.account.adapter.input.web.account_router import get_current_account_id
from app.simulation.application.usecase.simulation_usecase import SimulationService
from app.simulation.infrastructure.repository.simulation_repository_impl import SimulationRepositoryImpl
from app.conversation.adapter.output.stream.stream_adapter import StreamAdapter
from app.simulation.adapter.input.web.request.start_simulation_request import StartSimulationRequest, SendMessageRequest

simulation_router = APIRouter(tags=["simulation"])

@simulation_router.post("/start")
async def start_simulation(
        req: StartSimulationRequest,
        account_id: int = Depends(get_current_account_id),
        db: Session = Depends(get_db_session)
):
    repo = SimulationRepositoryImpl(db)
    service = SimulationService(repo)

    try:
        generator, chat_id = await service.start_new_session_stream(
            account_id=account_id,
            mbti=req.mbti,
            gender=req.gender,
            topic=req.topic
        )
        return StreamingResponse(
            generator,
            media_type="text/event-stream",
            headers={
                "X-Chat-Id": str(chat_id),
                "Access-Control-Expose-Headers": "X-Chat-Id"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"시뮬레이션 시작 실패: {str(e)}")
@simulation_router.post("/{chat_id}/stream")
async def send_simulation_stream(
        chat_id: str,
        req: SendMessageRequest,
        account_id: int = Depends(get_current_account_id),
        db: Session = Depends(get_db_session)
):
    """
    사용자 메시지를 보내고 AI 답변을 스트리밍으로 받습니다.
    """
    repo = SimulationRepositoryImpl(db)
    service = SimulationService(repo)

    try:
        generator = await service.send_user_message_stream(
            chat_id=chat_id,
            account_id=account_id,
            content=req.content
        )
        return StreamAdapter.to_streaming_response(generator)
    except PermissionError:
        raise HTTPException(status_code=403, detail="해당 대화방에 대한 권한이 없습니다.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"스트리밍 오류: {str(e)}")


@simulation_router.get("/{chat_id}")
async def get_simulation_detail(
        chat_id: str,
        account_id: int = Depends(get_current_account_id),
        db: Session = Depends(get_db_session)
):
    repo = SimulationRepositoryImpl(db)
    service = SimulationService(repo)

    # 1. "list" 문자열이 들어오면 목록 반환 로직으로 분기
    if chat_id == "list":
        return await service.get_user_chat_list(account_id)

    # 2. 그 외에는 기존 상세 조회 (UUID 기반 조회)
    try:
        chat = await service.get_chat_details(chat_id, account_id)
        return chat
    except Exception as e:
        # DB 조회 에러 또는 권한 에러 처리
        raise HTTPException(status_code=404, detail="대화를 찾을 수 없습니다.")


@simulation_router.delete("/{chat_id}")
async def delete_simulation(
        chat_id: str,
        account_id: int = Depends(get_current_account_id),
        db: Session = Depends(get_db_session)
):

    repo = SimulationRepositoryImpl(db)
    service = SimulationService(repo)

    try:
        success = await service.delete_session(chat_id, account_id)

        if not success:
            raise HTTPException(status_code=404, detail="삭제할 대상을 찾을 수 없습니다.")

        return {"status": "success", "message": "성공적으로 삭제되었습니다."}

    except PermissionError:
        raise HTTPException(status_code=403, detail="해당 대화방을 삭제할 권한이 없습니다.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"삭제 중 오류 발생: {str(e)}")