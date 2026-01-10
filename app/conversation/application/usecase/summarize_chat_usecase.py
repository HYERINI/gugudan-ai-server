from typing import Optional
from fastapi import HTTPException
from app.config.call_gpt import CallGPT
from app.config.security.message_crypto import AESEncryption
from app.config.prompt_loader import prompt_loader
from app.conversation.domain.conversation.aggregate import Conversation


class SummarizeChatUseCase:
    """채팅 요약 UseCase"""
    
    def __init__(
        self,
        chat_room_repo,
        chat_message_repo,
        crypto_service: AESEncryption,
        llm_service: CallGPT = None,
    ):
        self.chat_room_repo = chat_room_repo
        self.chat_message_repo = chat_message_repo
        self.crypto_service = crypto_service
        self.llm_service = llm_service or CallGPT()
    
    async def execute(self, room_id: str, account_id: int) -> dict:
        """
        채팅 내용을 요약합니다.
        
        Returns:
            {
                "summary": "요약 텍스트",
                "room_title": "대화방 제목",
                "message_count": 메시지 수,
                "created_at": datetime,
                "room_id": room_id
            }
        """
        # 1. 대화방 및 메시지 로드
        room_orm = await self.chat_room_repo.find_by_id(room_id)
        if not room_orm:
            raise HTTPException(status_code=404, detail="대화방을 찾을 수 없습니다.")
        
        if room_orm.account_id != account_id:
            raise HTTPException(status_code=403, detail="권한이 없습니다.")
        
        msg_orms = await self.chat_message_repo.find_by_room_id(room_id)
        if not msg_orms:
            raise HTTPException(status_code=400, detail="대화 내용이 없습니다.")
        
        # 2. Conversation 애그리거트 생성
        conversation = Conversation(room=room_orm, messages=msg_orms)
        
        # 3. 대화 내용 복호화 및 텍스트로 변환
        conversation_text = self._format_conversation_for_summary(conversation)
        
        # 4. 요약 프롬프트 구성
        summary_prompt = self._create_summary_prompt(conversation_text)
        
        # 5. LLM 호출 (비스트리밍)
        try:
            summary_text = await self.llm_service.call_gpt_non_stream(summary_prompt)
        except Exception as e:
            raise HTTPException(
                status_code=500, 
                detail=f"요약 생성 실패: {str(e)}"
            )
        
        # 6. 결과 반환
        return {
            "summary": summary_text.strip(),
            "room_title": room_orm.title or "제목 없음",
            "message_count": len(msg_orms),
            "created_at": room_orm.created_at,
            "room_id": room_id
        }
    
    def _format_conversation_for_summary(self, conversation: Conversation) -> str:
        """대화 내용을 요약용 텍스트로 변환"""
        text_parts = []
        
        sorted_msgs = sorted(conversation.messages, key=lambda x: x.id)
        for msg in sorted_msgs:
            try:
                decrypted = self.crypto_service.decrypt(
                    ciphertext=msg.content_enc,
                    iv=msg.iv if (msg.iv and len(msg.iv) == 16) else None
                )
                role = "사용자" if str(msg.role).upper() == "USER" else "상담사"
                text_parts.append(f"{role}: {decrypted}")
            except Exception:
                continue
        
        return "\n\n".join(text_parts)
    
    def _create_summary_prompt(self, conversation_text: str) -> str:
        """요약 프롬프트 생성 (prompt_loader 사용)"""
        return prompt_loader.get_summary_prompt(conversation_text)
