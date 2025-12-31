from sqlalchemy.orm import Session
from Crypto.Random import get_random_bytes

from app.conversation.infrastructure.orm.chat_message_feedback_orm import ChatFeedbackOrm
from app.conversation.infrastructure.orm.chat_message_orm import ChatMessageOrm


class ChatMessageRepositoryImpl:
    def __init__(self, session: Session):
        self.db = session

    async def save_message(self, **kwargs):
        try:
            # 1. IV 자동 생성
            if not kwargs.get('iv'):
                kwargs['iv'] = get_random_bytes(16)

            # 2. parent_id 유효성 검사
            parent_id = kwargs.get('parent_id')
            if parent_id is not None:
                exists = self.db.query(ChatMessageOrm).filter(ChatMessageOrm.id == parent_id).first()
                if not exists:
                    kwargs['parent_id'] = None

            # 3. file_urls 처리
            file_urls = kwargs.get('file_urls')
            kwargs['file_urls'] = file_urls if file_urls is not None else []

            # 4. 객체 생성 및 저장
            msg = ChatMessageOrm(**kwargs)
            self.db.add(msg)
            self.db.flush()
            return msg

        except Exception as e:
            self.db.rollback()
            raise e

    async def find_by_room_id(self, room_id: str):
        return (
            self.db.query(ChatMessageOrm)
            .filter(ChatMessageOrm.room_id == room_id)
            .order_by(ChatMessageOrm.id.asc())
            .all()
        )

    async def find_by_room_id_with_feedback(self, room_id: str, account_id: int):
        from app.conversation.infrastructure.orm.chat_message_feedback_orm import ChatFeedbackOrm

        return (
            self.db.query(ChatMessageOrm, ChatFeedbackOrm.satisfaction)
            .outerjoin(
                ChatFeedbackOrm,
                (ChatMessageOrm.id == ChatFeedbackOrm.message_id) &
                (ChatFeedbackOrm.account_id == account_id)
            )
            .filter(ChatMessageOrm.room_id == room_id)
            .order_by(ChatMessageOrm.id.asc())
            .all()
        )