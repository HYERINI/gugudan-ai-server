from pydantic import BaseModel

from app.conversation.domain.chat_feedback.enums import Satisfaction


class ChatFeedbackResponse(BaseModel):
    message_id: int
    satisfaction: Satisfaction
    status: str  # "CREATED" or "UPDATED"