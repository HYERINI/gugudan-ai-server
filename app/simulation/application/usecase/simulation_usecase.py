import base64
from typing import List, Dict
from app.config.call_gpt import CallGPT
from app.simulation.application.port.simulation_repository_port import SimulationRepositoryPort
from app.simulation.domain.entity.simulation_chat import SimulationChat
from app.config.security.message_crypto import AESEncryption


class SimulationService:
    def __init__(self, repository: SimulationRepositoryPort):
        self.repository = repository
        self.crypto = AESEncryption()

    def _build_system_prompt(self, mbti: str, gender: str, topic: str) -> str:
        mbti = mbti.upper()
        traits = []
        if "E" in mbti:
            traits.append("- 반응을 크게 하고 이모티콘이나 느낌표(!)를 자주 사용하며 활발하게 대화하세요.")
        else:
            traits.append("- 차분하고 신중하게 대화하며, 말수가 아주 많지는 않지만 깊이 있게 반응하세요.")

        if "S" in mbti:
            traits.append("- 구체적인 사실, 현실적인 상황, 오감으로 느껴지는 것에 집중해서 말하세요.")
        else:
            traits.append("- 비유나 상상, '만약에~' 같은 가정적인 상황에 흥미를 보이며 창의적으로 대화하세요.")

        if "T" in mbti:
            traits.append("- 공감보다는 상황에 대한 분석이나 해결책, 논리적인 판단을 우선해서 말하세요.")
        else:
            traits.append("- 상대방의 감정에 깊이 공감하고 '헐', '진짜?', '힘들었겠다' 같은 리액션을 꼭 포함하세요.")

        if "J" in mbti:
            traits.append("- 계획적이고 깔끔하게 정리된 결론을 선호하며, 대화의 흐름을 주도하려 하세요.")
        else:
            traits.append("- 유연하고 즉흥적이며, 상대방의 말에 따라 대화 주제가 바뀌는 것을 즐기세요.")

        style_guide = "\n".join(traits)
        return (
            f"### [SYSTEM INSTRUCTION: 가상 대화 샌드박스] ###\n"
            f"당신은 AI임을 완전히 잊고 다음의 페르소나로 완벽히 변신합니다.\n"
            f"- 성별: {gender}\n"
            f"- MBTI 유형: {mbti}\n"
            f"- 현재 상황: {topic}\n\n"
            f"### [말투 및 행동 지침] ###\n"
            f"{style_guide}\n"
            f"- 실제 카톡처럼 짧은 문장(10~40자) 위주로 대답하세요.\n"
            f"---------------------------------\n"
            f"지금부터 {mbti} {gender}로서 대화를 시작합니다."
        )

    def _decrypt_messages(self, messages: List[Dict]) -> List[Dict]:
        decrypted_list = []
        if not messages: return []

        for msg in messages:
            content_enc = msg.get("content", "")
            iv_enc = msg.get("iv", "")
            try:
                if iv_enc and content_enc:
                    # 저장된 Base64 데이터를 bytes로 변환
                    cipher_bytes = base64.b64decode(content_enc)
                    iv_bytes = base64.b64decode(iv_enc)
                    # 수정 불가능한 암호화 클래스의 decrypt에 iv를 명시적으로 전달
                    decrypted_val = self.crypto.decrypt(ciphertext=cipher_bytes, iv=iv_bytes)
                    content_text = decrypted_val
                else:
                    content_text = content_enc
            except Exception as e:
                print(f"!!! Decryption Failed: {str(e)}")
                content_text = "[복호화 오류]"

            decrypted_list.append({
                "role": msg.get("role"),
                "content": content_text,
                "timestamp": msg.get("timestamp")
            })
        return decrypted_list

    async def start_new_session_stream(self, account_id: int, mbti: str, gender: str, topic: str):
        chat = SimulationChat(account_id=account_id, mbti=mbti, gender=gender, topic=topic)

        await self.repository.save(chat, is_new=True)

        prompt = self._build_system_prompt(mbti, gender, topic) + "\n상황에 맞는 첫 인사를 해주세요."

        async def generator():
            full_text = ""
            async for chunk in CallGPT.call_gpt(prompt):
                if chunk:
                    full_text += chunk
                    yield chunk

            chat.add_message("assistant", full_text)
            await self.repository.save(chat, is_new=False)

        return generator(), chat.id

    async def send_user_message_stream(self, chat_id: str, account_id: int, content: str):
        chat = await self.repository.find_by_id(chat_id)
        if not chat or not chat.is_owned_by(account_id):
            raise PermissionError("접근 권한이 없습니다.")

        # 히스토리 복호화 (GPT 맥락 전달용)
        chat.messages = self._decrypt_messages(chat.messages)
        chat.add_message("user", content)

        system_prompt = self._build_system_prompt(chat.mbti, chat.gender, chat.topic)
        # 최근 6개의 대화만 컨텍스트로 유지
        history_context = "\n".join([f"{m['role']}: {m['content']}" for m in chat.messages[-6:]])
        final_prompt = f"{system_prompt}\n\n[대화 기록]\n{history_context}\nassistant: "

        async def generator():
            full_response = ""
            async for chunk in CallGPT.call_gpt(final_prompt):
                full_response += chunk
                yield chunk
            chat.add_message("assistant", full_response)
            await self.repository.save(chat, is_new=False)

        return generator()

    async def get_user_chat_list(self, account_id: int) -> List[Dict]:
        chats = await self.repository.find_all_by_account_id(account_id)
        result = []
        for chat in chats:
            decrypted_msgs = self._decrypt_messages(chat.messages)
            last_msg = decrypted_msgs[-1].get("content", "") if decrypted_msgs else ""
            result.append({
                "id": chat.id, "mbti": chat.mbti, "gender": chat.gender, "topic": chat.topic,
                "last_message": last_msg[:50] + "..." if len(last_msg) > 50 else last_msg
            })
        return result

    async def get_chat_details(self, chat_id: str, account_id: int) -> SimulationChat:
        chat = await self.repository.find_by_id(chat_id)
        if not chat: raise ValueError("Not Found")
        chat.messages = self._decrypt_messages(chat.messages)
        return chat

    async def delete_session(self, chat_id: str, account_id: int) -> bool:
        """
        특정 채팅을 삭제합니다.
        삭제 전 본인의 채팅인지 권한을 확인한 후 리포지토리에 삭제를 요청합니다.
        """
        chat = await self.repository.find_by_id(chat_id)

        if not chat:
            return False

        if not chat.is_owned_by(account_id):
            raise PermissionError("해당 대화를 삭제할 권한이 없습니다.")

        success = await self.repository.delete_by_id(chat_id, account_id)

        return success
