from __future__ import annotations
from pydantic import BaseModel


class SurveyDetailResponse(BaseModel):
    fallback: bool = False
    version: int
    title: str
    subtitle: str | None = None
    footer: str | None = None
    questions: list[dict]  # questions_json을 그대로 내려주므로 dict로


class CreateSurveyResponse(BaseModel):
    ok: bool
    duplicated: bool = False
    message: str | None = None
