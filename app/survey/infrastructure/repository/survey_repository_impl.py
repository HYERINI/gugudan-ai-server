from __future__ import annotations

import json
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select, func

from app.survey.infrastructure.orm.survey_model import SurveyTemplateModel
from app.survey.infrastructure.orm.survey_response_orm import SurveyResponseOrm
from app.survey.infrastructure.orm.survey_response_item_orm import SurveyResponseItemOrm
from app.conversation.infrastructure.orm.chat_message_orm import ChatMessageOrm


class SurveyRepositoryImpl:
    def __init__(self, db: Session):
        self.db = db

    def get_active_template(self) -> SurveyTemplateModel | None:
        return (
            self.db.query(SurveyTemplateModel)
            .filter(SurveyTemplateModel.is_active == True)  # noqa: E712
            .order_by(SurveyTemplateModel.version.desc())
            .first()
        )

    def get_active_template_payload(self) -> dict | None:
        tpl = self.get_active_template()
        if not tpl:
            return None

        try:
            questions = json.loads(tpl.questions_json) if tpl.questions_json else []
        except Exception:
            questions = []

        return {
            "fallback": False,
            "version": tpl.version,
            "title": tpl.title,
            "subtitle": tpl.subtitle,
            "footer": tpl.footer,
            "questions": questions,
        }

    def has_user_responded(self, user_id: int, template_version: int) -> bool:
        """
        유저가 특정 템플릿 버전에 이미 응답했는지 여부
        """
        q = (
            select(func.count(SurveyResponseOrm.id))
            .where(SurveyResponseOrm.user_id == user_id)
            .where(SurveyResponseOrm.template_version == template_version)
        )
        return (self.db.execute(q).scalar() or 0) > 0

    def save_survey_response(
        self,
        user_id: int | None,
        template_version: int,
        answers: dict[str, str],
    ) -> tuple[bool, bool, str | None]:
        """
        return (ok, duplicated, message)
        """

        # ✅ 로그인 유저면 중복 선체크 (유니크 제약 없어도 방지 가능)
        if user_id is not None and self.has_user_responded(user_id, template_version):
            return False, True, "이미 설문을 제출하셨어요."

        resp = SurveyResponseOrm(user_id=user_id, template_version=template_version)
        self.db.add(resp)
        self.db.flush()  # resp.id 확보

        items: list[SurveyResponseItemOrm] = []
        for qid, value in (answers or {}).items():
            qtype = "text" if qid == "one_line" else "single"
            items.append(
                SurveyResponseItemOrm(
                    response_id=resp.id,
                    question_id=qid,
                    question_type=qtype,
                    value=value,
                )
            )

        if items:
            self.db.add_all(items)

        try:
            self.db.commit()
            return True, False, None
        except IntegrityError:
            # ✅ 유니크 제약이 있다면 여기로도 중복이 들어올 수 있음
            self.db.rollback()
            return False, True, "이미 설문을 제출하셨어요."

    def get_user_message_count(self, user_id: int) -> int:
        q = (
            select(func.count(ChatMessageOrm.id))
            .where(ChatMessageOrm.account_id == user_id)
            .where(ChatMessageOrm.role == "USER")
        )
        return int(self.db.execute(q).scalar() or 0)

