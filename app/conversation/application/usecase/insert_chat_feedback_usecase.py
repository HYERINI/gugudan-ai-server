from app.conversation.adapter.input.web.request.chat_feedback_request import ChatFeedbackRequest
from app.conversation.application.port.out.chat_feedback_repository_port import ChatFeedbackRepository
from app.conversation.domain.chat_feedback.entity import ChatFeedback


class ChatFeedbackUsecase:
    def __init__(self, repository: ChatFeedbackRepository):
        self.repository = repository

    async def execute_feedback(self, account_id: int, request: ChatFeedbackRequest):
        # 1. 기존 피드백이 있는지 조회
        existing = await self.repository.find_by_message_and_account(
            request.message_id, account_id
        )

        if existing:
            # 2. 존재하면 업데이트
            existing.update_info(
                satisfaction=request.satisfaction,
                reason=request.reason,
                comment=request.comment
            )
            await self.repository.updated_feedback(existing)
            return "UPDATED"
        else:
            # 3. 없으면 신규 생성
            new_feedback = ChatFeedback(
                message_id=request.message_id,
                account_id=account_id,
                satisfaction=request.satisfaction,
                reason=request.reason,
                comment=request.comment
            )
            await self.repository.add_feedback(new_feedback)
            return "CREATED"