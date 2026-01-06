# app/survey/domain/entity/survey.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Literal, Union

SurveyQuestionId = Literal["organize", "reason", "context", "reuse_reason"]

@dataclass(frozen=True)
class SurveySingleQuestion:
    id: SurveyQuestionId
    type: Literal["single"]
    question: str
    options: List[str]

@dataclass(frozen=True)
class SurveyTextQuestion:
    id: SurveyQuestionId
    type: Literal["text"]
    question: str
    optional: bool = False
    maxLength: int = 200
    placeholder: str = ""

@dataclass(frozen=True)
class SurveyDoneQuestion:
    type: Literal["done"]
    title: str
    desc: Optional[str] = None
    autoCloseMs: int = 1500

SurveyQuestion = Union[SurveySingleQuestion, SurveyTextQuestion, SurveyDoneQuestion]

@dataclass(frozen=True)
class SurveyContent:
    fallback: bool
    title: str
    subtitle: Optional[str]
    footer: Optional[str]
    questions: List[Dict[str, Any]]  # JSON-friendly로 내려주기 쉬움
