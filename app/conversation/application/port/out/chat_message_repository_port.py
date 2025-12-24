from abc import ABC, abstractmethod


class ChatMessageRepositoryPort(ABC):
    @abstractmethod
    async def save_message(self, **kwargs):
        """유저/AI 구분 없이 메시지를 저장하고 생성된 객체를 반환"""
        pass

    @abstractmethod
    async def find_by_room_id(self, room_id: str):
        pass

    @abstractmethod
    async def find_by_room_id_with_feedback(self, room_id: str, account_id: int):
        pass