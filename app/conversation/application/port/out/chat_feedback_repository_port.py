from abc import ABC, abstractmethod
from app.conversation.domain.chat_feedback.entity import ChatFeedback

class ChatFeedbackRepository(ABC):
    @abstractmethod
    async def add_feedback(self, feedback: ChatFeedback) -> str:
        pass

    @abstractmethod
    async def updated_feedback(self, feedback: ChatFeedback) -> str:
        pass

    @abstractmethod
    async def find_by_message_and_account(self, message_id: int, account_id: int) -> ChatFeedback | None:
        pass