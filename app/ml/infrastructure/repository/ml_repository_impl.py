from datetime import datetime, timedelta
from typing import List

from sqlalchemy import literal
from sqlalchemy.orm import Session, aliased

from app.config.database.session import get_db_session
from app.conversation.infrastructure.orm.chat_message_feedback_orm import ChatFeedbackOrm
from app.conversation.infrastructure.orm.chat_message_orm import ChatMessageOrm
from app.ml.application.port.ml_repository_port import MLRepositoryPort
from app.ml.domain.output_message import CounselRow


class MLRepositoryImpl(MLRepositoryPort):
    __instance = None

    def __new__(cls, *args, **kwargs):
        if cls.__instance is None:
            cls.__instance = super().__new__(cls)

        return cls.__instance

    @classmethod
    def get_instance(cls):
        if cls.__instance is None:
            cls.__instance = cls()
        return cls.__instance

    def __init__(self, session: Session | None = None):
        if session is not None:
            self.db: Session = session
            self._db_generator = None
        else:
            # get_db_session()은 generator를 반환하므로 next()로 Session을 꺼냄
            self._db_generator = get_db_session()
            self.db: Session = next(self._db_generator)

    def get_counsel_data(self, start: str, end: str) -> List[CounselRow]:
        try:
            m1 = aliased(ChatMessageOrm)  # USER
            m2 = aliased(ChatMessageOrm)  # ASSISTANT

            start_dt = datetime.strptime(start, "%Y%m%d")
            end_dt = datetime.strptime(end, "%Y%m%d") + timedelta(days=1)

            user_q = (
                self.db.query(
                    m1.id.label("id"),
                    m1.account_id.label("account_id"),
                    literal("USER").label("role"),
                    m1.content_enc.label("message"),
                    literal(None).label("parent"),
                    m1.iv.label("iv"),
                    m1.created_at.label("created_at"),
                )
                .join(m2, m1.room_id == m2.room_id)
                .join(ChatFeedbackOrm, m2.id == ChatFeedbackOrm.message_id)
                .filter(
                    m1.role == "USER",
                    m2.role == "ASSISTANT",
                    m2.parent_id == m1.id,
                    ChatFeedbackOrm.satisfaction == "SATISFIED",
                    m1.created_at >= start_dt,
                    m1.created_at < end_dt,
                )
            )

            assistant_q = (
                self.db.query(
                    m2.id.label("id"),
                    m2.account_id.label("account_id"),
                    literal("ASSISTANT").label("role"),
                    m2.content_enc.label("message"),
                    m2.parent_id.label("parent"),
                    m2.iv.label("iv"),
                    m2.created_at.label("created_at"),
                )
                .join(m1, m1.room_id == m2.room_id)
                .join(ChatFeedbackOrm, m2.id == ChatFeedbackOrm.message_id)
                .filter(
                    m1.role == "USER",
                    m2.role == "ASSISTANT",
                    m2.parent_id == m1.id,
                    ChatFeedbackOrm.satisfaction == "SATISFIED",
                    m2.created_at >= start_dt,
                    m2.created_at < end_dt,
                )
            )

            rows = user_q.union_all(assistant_q).all()

            result: List[CounselRow] = [
                {
                    "id": row.id,
                    "account_id": row.account_id,
                    "role": row.role,
                    "message": row.message,
                    "parent": row.parent,
                    "iv": row.iv,
                    "created_at": row.created_at
                }
                for row in rows
            ]

            return result

        finally:
            self.db.close()


