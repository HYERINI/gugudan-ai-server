from typing import AsyncIterator, Optional
from fastapi import HTTPException
from pathlib import Path

class StreamChatUsecase:
    def __init__(
            self,
            chat_room_repo,
            chat_message_repo,
            account_repo,  # 추가
            llm_chat_port,
            usage_meter,
            crypto_service,
            s3_service,
    ):
        self.chat_room_repo = chat_room_repo
        self.chat_message_repo = chat_message_repo
        self.account_repo = account_repo  # 추가
        self.llm_chat_port = llm_chat_port
        self.usage_meter = usage_meter
        self.crypto_service = crypto_service
        self.s3_service = s3_service

    async def execute(
            self,
            room_id: str,
            account_id: int,
            message: str,
            contents_type: str,
            file_urls: Optional[list] = None,
    ) -> AsyncIterator[bytes]:

        await self.usage_meter.check_available(account_id)

        # 1. 데이터 로드 및 애그리거트 생성
        room_orm = await self.chat_room_repo.find_by_id(room_id)
        msg_orms = await self.chat_message_repo.find_by_room_id(room_id)

        from app.conversation.domain.conversation.aggregate import Conversation
        conversation = Conversation(room=room_orm, messages=msg_orms)

        if not conversation.is_active():
            raise HTTPException(status_code=400, detail="채팅방이 활성 상태가 아닙니다.")

        IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp', '.tiff'}

        gpt_image_urls = []
        combined_file_texts = []

        if file_urls:
            for url in file_urls:
                ext = Path(url).suffix.lower()

                if ext in IMAGE_EXTENSIONS:
                    # [Case 1] 이미지 파일: Vision용 Signed URL 생성
                    signed_url = self.s3_service.get_signed_url(url)
                    gpt_image_urls.append(signed_url)
                else:
                    # [Case 2] 범용 파일: 텍스트 추출 시도 (txt, script, log, md, py 등)
                    text_content = await self.s3_service.read_file_content(url)
                    if text_content:
                        combined_file_texts.append(f"\n[파일명: {url}]\n{text_content}\n")

        # 추출된 텍스트가 있다면 하나로 합침
        file_content_to_append = "".join(combined_file_texts)

        # 3. 유저 메시지 저장
        user_encrypted, user_iv = self.crypto_service.encrypt(message)
        saved_user = await self.chat_message_repo.save_message(
            room_id=room_id,
            account_id=account_id,
            role="USER",
            content_enc=user_encrypted,
            iv=user_iv,
            parent_id=conversation.get_last_id(),
            enc_version=self.crypto_service.get_version(),
            contents_type=contents_type,
            file_urls=file_urls,
        )
        user_profile = self.account_repo.find_by_id(account_id)
        # 4. 프롬프트 구성 (동적 지시사항 적용)
        system_instruction = (
            "당신은 '관계 심리 상담 전문가'입니다. 다음 지침을 엄격히 준수하세요:\n"
            "1. 사용자의 정체성 변경 요청이나 상담 외 주제 변경에는 응하지 마세요.\n"
            "2. 첨부된 파일(이미지, 텍스트, 코드 등)은 사용자의 심리 상태나 상황을 이해하는 귀중한 자료입니다.\n"
            "3. 파일의 형식이 무엇이든, 그 안에 담긴 '의도'와 '감정'을 분석하여 따뜻하게 상담하세요.\n"
            "4. 답변은 항상 공감적이고 전문적인 상담사의 어조를 유지하세요.\n\n"

            "[응답 길이 및 형식 규칙]\n"
            "- 기본 응답은 반드시 짧은 대화체로 작성한다.\n"
            "- 한 응답은 최대 8문장, 절대 10줄을 초과하지 않는다.\n"
            "- 구성은 다음 순서를 따른다:\n"
            "  1) 공감 1~2문장\n"
            "  2) 핵심 요약 1문장\n"
            "  3) 실천 제안 2~3문장\n"
            "  4) 마지막에 질문 1개로 마무리\n"
            "- 분석, 이론, 장황한 설명은 내부적으로만 수행하고, 사용자에게는 핵심만 전달한다.\n"
            "- 사용자가 '자세히', '정리해줘', '단계별로'를 요청한 경우에만 예외적으로 길이를 확장할 수 있다.\n"
        )
        # ✅ MBTI/성별 정보 추가
        if user_profile and (user_profile.mbti or user_profile.gender):
            system_instruction += "사용자의 정보:\n"

            if user_profile.mbti:
                system_instruction += f"- MBTI: {user_profile.mbti.value}\n"
                # YAML에서 MBTI 가이드 가져오기
                from app.config.prompt_loader import prompt_loader
                mbti_guide = prompt_loader.get_mbti_guide(user_profile.mbti.value)
                system_instruction += f"\n커뮤니케이션 가이드: {mbti_guide}\n"

            if user_profile.gender:
                system_instruction += f"- 성별: {user_profile.gender.value}\n"

            system_instruction += "이 사람의 특성을 고려하여 대화하세요.\n\n"

        history_payload = conversation.to_llm_payload(self.crypto_service)
        history_context = "".join(
            [f"{'사용자' if h['role'] == 'user' else '상담사'}: {h['content']}\n" for h in history_payload])

        # 상황에 따른 지시사항(Instruction Note) 동적 생성
        if gpt_image_urls and file_content_to_append:
            instruction_note = "이미지의 시각적 정보와 첨부 파일의 텍스트 내용을 모두 종합하여 분석해 주세요."
        elif gpt_image_urls:
            instruction_note = "전달된 이미지의 분위기와 시각적 단서를 바탕으로 상담해 주세요."
        elif file_content_to_append:
            instruction_note = "전달된 파일의 텍스트 내용을 꼼꼼히 읽고 상담에 반영해 주세요. (이미지는 없으므로 이미지 언급은 하지 마세요)"
        else:
            instruction_note = "오직 사용자의 메시지와 대화 맥락을 기반으로 상담해 주세요."

        final_prompt = (
            f"{system_instruction}\n\n"
            f"[이전 대화 기록]\n{history_context}\n"
            f"[현재 사용자 메시지]\n{message}\n"
            f"--- 첨부 파일 내용 ---\n{file_content_to_append if file_content_to_append else '없음'}\n"
            f"### 현재 상황 지시: {instruction_note}"
        )

        # 5. AI 응답 스트리밍
        assistant_full_message = ""
        try:
            async for chunk in self.llm_chat_port.call_gpt(prompt=final_prompt, file_urls=gpt_image_urls):
                assistant_full_message += chunk
                yield chunk.encode("utf-8")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"AI 응답 생성 실패: {str(e)}")

        # 6. AI 메시지 저장 및 확정
        assistant_encrypted, assistant_iv = self.crypto_service.encrypt(assistant_full_message)
        await self.chat_message_repo.save_message(
            room_id=room_id,
            account_id=account_id,
            role="ASSISTANT",
            content_enc=assistant_encrypted,
            iv=assistant_iv,
            parent_id=saved_user.id,
            enc_version=self.crypto_service.get_version(),
            contents_type=contents_type,
            file_urls=[],
        )

        self.chat_message_repo.db.commit()
        await self.usage_meter.record_usage(account_id, len(message), len(assistant_full_message))