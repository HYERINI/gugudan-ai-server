from sqlalchemy.orm import Session
from sqlalchemy.future import select

from app.conversation.application.port.out.chat_feedback_repository_port import ChatFeedbackRepository
from app.conversation.domain.chat_feedback.entity import ChatFeedback
from app.conversation.infrastructure.orm.chat_message_feedback_orm import ChatFeedbackOrm


class ChatFeedbackRepositoryImpl(ChatFeedbackRepository):
    def __init__(self, session: Session):
        self.session = session

    async def add_feedback(self, feedback: ChatFeedback) -> str:
        orm = ChatFeedbackOrm(
            message_id=feedback.message_id,
            account_id=feedback.account_id,
            satisfaction=feedback.satisfaction,
            reason=feedback.reason,
            comment=feedback.comment
        )
        self.session.add(orm)
        self.session.commit()
        return "SUCCESS"

    async def updated_feedback(self, feedback: ChatFeedback) -> str:
        result = self.session.execute(
            select(ChatFeedbackOrm).filter_by(message_id=feedback.message_id, account_id=feedback.account_id)
        )
        orm = result.scalars().first()
        if orm:
            orm.satisfaction = feedback.satisfaction
            orm.reason = feedback.reason
            orm.comment = feedback.comment
            self.session.commit()
        return "SUCCESS"

    async def find_by_message_and_account(self, message_id: int, account_id: int) -> ChatFeedback | None:
        result = self.session.execute(
            select(ChatFeedbackOrm).filter_by(message_id=message_id, account_id=account_id)
        )
        orm = result.scalars().first()
        if not orm:
            return None

        return ChatFeedback(
            id=orm.id,
            message_id=orm.message_id,
            account_id=orm.account_id,
            satisfaction=orm.satisfaction,
            reason=orm.reason,
            comment=orm.comment,
            created_at=orm.created_at
        )