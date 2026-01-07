from __future__ import annotations
from typing import Protocol


class SurveyRepositoryPort(Protocol):
    def get_active_template(self) -> dict | None:
        """return: {version, title, subtitle, footer, questions(list)} or None"""

    def save_response(
        self,
        user_id: int | None,
        template_version: int,
        answers: dict[str, str],
    ) -> tuple[bool, bool, str | None]:
        """return: (ok, duplicated, message)"""
