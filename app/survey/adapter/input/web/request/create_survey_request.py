from __future__ import annotations
from pydantic import BaseModel, Field


class CreateSurveyRequest(BaseModel):
    # 프론트에서 answers: Record<string,string> 보냄
    answers: dict[str, str] = Field(default_factory=dict)
