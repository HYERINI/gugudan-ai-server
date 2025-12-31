class Conversation:
    def __init__(self, room, messages):
        self.room = room
        self.messages = messages

    def get_last_id(self) -> int | None:
        """현재 방의 마지막 메시지 ID 추출 (다음 메시지의 부모)"""
        if not self.messages:
            return None
        # ORM 객체의 id 필드 기준
        return max([m.id for m in self.messages])

    def is_active(self) -> bool:
        # ChatRoomOrm의 status 필드 확인
        return getattr(self.room, "status", "ACTIVE") == "ACTIVE"

    def get_prompt_context(self, crypto_service) -> str:
        """기존 메시지들을 복호화하여 프롬프트 텍스트로 변환"""
        context = ""
        # ID 순서대로 정렬하여 대화 흐름 보장
        sorted_msgs = sorted(self.messages, key=lambda x: x.id)
        for m in sorted_msgs:
            try:
                # 필드명은 content_enc와 iv로 매칭
                decrypted_txt = crypto_service.decrypt(
                    ciphertext=m.content_enc,
                    iv=m.iv if (m.iv and len(m.iv) == 16) else None
                )
                role_label = "상담사" if str(m.role).upper() == "ASSISTANT" else "사용자"
                file_note = f" [첨부파일 {len(m.file_urls)}개]" if getattr(m, 'file_urls', None) else ""
                context += f"{role_label}: {decrypted_txt}{file_note}\n"
            except Exception:
                continue
        return context

    def to_llm_payload(self, crypto_service) -> list:
        """
        이미지는 'image_url' 객체로, 텍스트는 'text' 객체로 변환.
        """
        ai_context = []
        sorted_msgs = sorted(self.messages, key=lambda x: x.id)

        for m in sorted_msgs:
            try:
                decrypted_txt = crypto_service.decrypt(
                    ciphertext=m.content_enc,
                    iv=m.iv if (m.iv and len(m.iv) == 16) else None
                )
                role = "assistant" if str(m.role).upper() == "ASSISTANT" else "user"

                file_urls = getattr(m, 'file_urls', [])

                if role == "user":
                    user_content = [{"type": "text", "text": decrypted_txt}]

                    for url in file_urls:
                        if any(url.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.webp']):
                            user_content.append({
                                "type": "image_url",
                                "image_url": {"url": url}
                            })
                        else:
                            user_content[0]["text"] += f"\n(첨부파일 경로: {url})"

                    ai_context.append({"role": "user", "content": user_content})

                else:
                    ai_context.append({"role": "assistant", "content": decrypted_txt})

            except Exception:
                continue

        return ai_context