from typing import Optional
from pydantic import BaseModel, Field
from app.conversation.domain.chat_feedback.enums import Satisfaction, FeedbackReason


class ChatFeedbackRequest(BaseModel):
    message_id: int
    satisfaction: Satisfaction
    reason: Optional[FeedbackReason] = None
    comment: Optional[str] = None