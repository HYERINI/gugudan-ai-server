from __future__ import annotations
import os

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.config.database.session import get_db_session
from app.survey.infrastructure.repository.survey_repository_impl import SurveyRepositoryImpl
from app.survey.adapter.input.web.request.create_survey_request import CreateSurveyRequest

# ✅ 이미 가지고 있는 인증 의존성 사용
from app.account.adapter.input.web.account_router import get_current_account_id

router = APIRouter(tags=["survey"])

# 정책: 몇 개 메시지 이후 설문 노출할지
SURVEY_TRIGGER_MESSAGE_COUNT = int(os.getenv("SURVEY_TRIGGER_MESSAGE_COUNT", "5"))


@router.get("/questions")
def get_questions(
    db: Session = Depends(get_db_session),
    account_id: int = Depends(get_current_account_id),  # ✅ 로그인 유저 확보
):
    """설문 표시 여부 및 설문 데이터 반환"""
    repo = SurveyRepositoryImpl(db)

    # 1) 활성 템플릿 조회
    template = repo.get_active_template()
    if not template:
        return {"show": False, "reason": "no_active_template"}

    # 2) payload 파싱
    payload = repo.get_active_template_payload()
    if not payload or not payload.get("questions"):
        return {"show": False, "reason": "invalid_payload"}

    template_version = template.version

    # 3) 이미 응답했으면 show=false
    if repo.has_user_responded(user_id=account_id, template_version=template_version):
        return {"show": False, "reason": "already_responded"}

    # 4) 메시지 카운트 조건 (이상으로 변경)
    msg_count = repo.get_user_message_count(user_id=account_id)
    if msg_count < SURVEY_TRIGGER_MESSAGE_COUNT:
        return {
            "show": False,
            "reason": "not_enough_messages",
            "trigger": SURVEY_TRIGGER_MESSAGE_COUNT,
            "current": msg_count,
        }

    # 5) 보여준다
    return {
        "show": True,
        "title": payload.get("title"),
        "subtitle": payload.get("subtitle"),
        "footer": payload.get("footer"),
        "version": template_version,
        "questions": payload.get("questions"),
    }


@router.post("/responses")
def create_response(
        req: CreateSurveyRequest,
        db: Session = Depends(get_db_session),
        account_id: int = Depends(get_current_account_id),
):
    """설문 응답 저장"""
    repo = SurveyRepositoryImpl(db)
    tpl = repo.get_active_template()

    if not tpl:
        return {"ok": False, "duplicated": False, "message": "설문 템플릿이 없습니다."}

    ok, duplicated, message = repo.save_survey_response(
        user_id=account_id,
        template_version=tpl.version,
        answers=req.answers,
    )
    return {"ok": ok, "duplicated": duplicated, "message": message}