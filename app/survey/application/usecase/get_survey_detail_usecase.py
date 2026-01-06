from __future__ import annotations
from app.survey.application.port.survey_repository_port import SurveyRepositoryPort


class GetSurveyDetailUsecase:
    def __init__(self, repo: SurveyRepositoryPort):
        self.repo = repo

    def execute(self) -> dict | None:
        return self.repo.get_active_template()
