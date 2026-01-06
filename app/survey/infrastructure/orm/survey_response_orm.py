from __future__ import annotations

from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Integer, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config.database.session import Base


class SurveyResponseOrm(Base):
    __tablename__ = "survey_response"
    __table_args__ = (
        UniqueConstraint("user_id", "template_version", name="uq_survey_user_template"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("account.id"), nullable=True
    )
    template_version: Mapped[int] = mapped_column(Integer, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )

    items = relationship(
        "SurveyResponseItemOrm",
        back_populates="response",
        cascade="all, delete-orphan",
    )
