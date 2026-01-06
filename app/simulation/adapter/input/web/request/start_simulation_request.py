from pydantic import BaseModel, Field

class StartSimulationRequest(BaseModel):
    mbti: str
    gender: str
    topic: str

class SendMessageRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=500, description="사용자 메시지 내용")