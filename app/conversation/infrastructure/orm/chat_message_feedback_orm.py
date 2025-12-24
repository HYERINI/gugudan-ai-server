from sqlalchemy import Column, Integer, DateTime, ForeignKey, Text, Enum as SqlEnum
from sqlalchemy.orm import relationship
from datetime import datetime
from app.config.database.session import Base
from app.conversation.domain.chat_feedback.enums import Satisfaction, FeedbackReason


class ChatFeedbackOrm(Base):
    __tablename__ = "chat_feedback"

    id = Column(Integer, primary_key=True, autoincrement=True)

    account_id = Column(Integer, nullable=False)

    message_id = Column(
        Integer,
        ForeignKey("chat_msg.id", ondelete="CASCADE"),
        nullable=False,
        unique=True
    )

    satisfaction = Column(
        SqlEnum(Satisfaction),
        nullable=False,
        info={"description": "LIKE 또는 DISLIKE"}
    )

    reason = Column(
        SqlEnum(FeedbackReason),
        nullable=True,
        info={"description": "상세 사유 (선택 사항)"}
    )

    comment = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    message = relationship("ChatMessageOrm", backref="feedback", uselist=False)