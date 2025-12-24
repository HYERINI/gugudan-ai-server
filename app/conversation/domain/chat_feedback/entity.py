from datetime import datetime
from typing import Optional
from app.conversation.domain.chat_feedback.enums import Satisfaction, FeedbackReason

class ChatFeedback:
    def __init__(
            self,
            message_id: int,
            account_id: int,
            satisfaction: Satisfaction,
            id: Optional[int] = None,
            reason: Optional[FeedbackReason] = None,
            comment: Optional[str] = None,
            created_at: Optional[datetime] = None,
    ):
        self.id = id
        self.message_id = message_id
        self.account_id = account_id
        self.satisfaction = satisfaction
        self.reason = reason
        self.comment = comment
        self.created_at = created_at or datetime.utcnow()

    def update_info(self, satisfaction: Satisfaction, reason: FeedbackReason, comment: str):
        """엔티티 내부에서 정보를 업데이트하는 로직"""
        self.satisfaction = satisfaction
        self.reason = reason
        self.comment = comment