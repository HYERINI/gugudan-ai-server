from sqlalchemy import Column, String, Integer, DateTime, JSON, Boolean, Index

from app.config.database.session import Base

class SimulationChatORM(Base):
    __tablename__ = "simulation_chat"

    id = Column(String(50), primary_key=True)
    account_id = Column(Integer, nullable=False, index=True)
    mbti = Column(String(4))
    topic = Column(String(255))
    gender = Column(String(10))
    messages = Column(JSON)
    is_training_data = Column(Boolean, default=False)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)

    __table_args__ = (
        Index('ix_account_id_created_at', 'account_id', 'created_at'),
    )