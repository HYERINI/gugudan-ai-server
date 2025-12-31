from sqlalchemy import Column, String, Integer, DateTime, LargeBinary, ForeignKey, Index, JSON
from datetime import datetime
from app.config.database.session import Base


class ChatMessageOrm(Base):
    __tablename__ = "chat_msg"

    id = Column(Integer, primary_key=True, autoincrement=True)
    room_id = Column(
        String(36),
        ForeignKey("chat_room.room_id", ondelete="CASCADE"),
        nullable=False
    )
    account_id = Column(Integer, nullable=False)
    role = Column(String(20), nullable=False)
    content_enc = Column(LargeBinary, nullable=False)
    iv = Column(LargeBinary, nullable=False)
    enc_version = Column(Integer)
    contents_type = Column(String(20))
    file_urls = Column(JSON, nullable=True, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)

    # 추가: 부모 메시지 ID (자기 자신을 참조)
    parent_id = Column(
        Integer,
        ForeignKey("chat_msg.id", ondelete="CASCADE"),
        nullable=True
    )

    # --- 인덱스 설정 ---
    __table_args__ = (
        # 1. 특정 방의 메시지를 전체 조회할 때 사용
        Index('idx_room_id', 'room_id'),

        # 2. 멀티 에이전트 구조에서 부모-자식 관계를 빠르게 조회
        Index('idx_room_parent_id', 'room_id', 'parent_id'),

    )