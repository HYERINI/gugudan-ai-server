# app/config/prompt_loader.py

import yaml
from pathlib import Path


class PromptLoader:
    _instance = None
    _prompts = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._prompts is None:
            # 프로젝트 루트에서 찾기
            project_root = Path(__file__).parent.parent.parent  # app/config에서 3단계 위로
            config_path = project_root / "prompts.yaml"

            with open(config_path, 'r', encoding='utf-8') as f:
                self._prompts = yaml.safe_load(f)

    def get_base_prompt(self) -> str:
        return self._prompts['system_prompt']['base']

    def get_mbti_guide(self, mbti: str) -> str:
        return self._prompts['mbti_guides'].get(
            mbti,
            self._prompts['default_guide']
        )

    def get_summary_prompt(self, conversation_text: str) -> str:
        """채팅 요약 프롬프트 가져오기"""
        template = self._prompts['summary_prompt']['template']
        return template.format(conversation_text=conversation_text)


# 싱글톤 인스턴스
prompt_loader = PromptLoader()