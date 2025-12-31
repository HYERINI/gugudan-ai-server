from datetime import datetime
from typing import List

from .enums import MessageRole, ContentType
from .value_object import EncryptedContent


class ChatMessage:
    """
    chat_msg 테이블에 1:1 대응
    """

    def __init__(
        self,
        message_id: int | None,
        room_id: str,
        account_id: int,
        role: MessageRole,
        content: EncryptedContent,
        content_type: ContentType,
        created_at: datetime,
        parent_id: int | None = None,
        updated_at: datetime | None = None,
        file_urls: List[str] | None = None,
    ):
        self.message_id = message_id
        self.room_id = room_id
        self.account_id = account_id
        self.role = role

        self.content = content
        self.content_type = content_type
        self.file_urls = file_urls if file_urls is not None else []
        self.created_at = created_at
        self.parent_id = parent_id
        self.updated_at = updated_at

    def has_files(self) -> bool:
        """첨부된 파일이 있는지 확인"""
        return len(self.file_urls) > 0

    def get_image_urls(self) -> List[str]:
        """이미지 파일만 필터링"""
        image_extensions = ('.jpg', '.jpeg', '.png', '.webp', '.gif')
        return [url for url in self.file_urls if url.lower().endswith(image_extensions)]

    def get_document_urls(self) -> List[str]:
        """이미지 외의 문서 파일만 필터링"""
        image_urls = self.get_image_urls()
        return [url for url in self.file_urls if url not in image_urls]