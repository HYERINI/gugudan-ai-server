from pydantic import BaseModel
from datetime import datetime
from typing import List, Dict

class SimulationChatResponse(BaseModel):
    id: str
    mbti: str
    topic: str
    messages: List[Dict]
    created_at: datetime

    class Config:
        from_attributes = True