from datetime import datetime
from typing import Optional, List, Dict
import uuid

class SimulationChat:
    def __init__(
        self,
        account_id: int,
        mbti: str,
        topic: str,
        gender: str,
        id: Optional[str] = None,
        messages: Optional[List[Dict]] = None,
        is_training_data: bool = False, # 일단 학습 제외로 세팅
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ):
        self.id = id or str(uuid.uuid4())
        self.account_id = account_id
        self.mbti = mbti
        self.topic = topic
        self.gender = gender
        self.messages = messages or []
        self.is_training_data = is_training_data
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()

    def is_owned_by(self, account_id: int) -> bool:
        """해당 계정이 시뮬레이션 대화의 소유자인지 확인"""
        return self.account_id == account_id

    def add_message(self, role: str, content: str) -> None:
        """메시지 추가 및 업데이트 시간 갱신"""
        self.messages.append({
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat()
        })
        self.updated_at = datetime.utcnow()