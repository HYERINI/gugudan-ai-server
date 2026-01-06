import base64
from typing import Optional, List
from sqlalchemy.orm import Session

from app.config.database.session import get_db_session
from app.simulation.application.port.simulation_repository_port import SimulationRepositoryPort
from app.simulation.domain.entity.simulation_chat import SimulationChat
from app.simulation.infrastructure.orm.simulation_chat_orm import SimulationChatORM
from app.config.security.message_crypto import AESEncryption


class SimulationRepositoryImpl(SimulationRepositoryPort):
    def __init__(self, session: Session | None = None):
        self.db: Session = session or get_db_session()
        self.crypto = AESEncryption()

    async def save(self, chat: SimulationChat, is_new: bool = False) -> None:
        processed_messages = []

        for msg in chat.messages:
            # 1. 이미 암호화 정보(iv)가 있는 메시지는 그대로 유지
            if msg.get("iv"):
                processed_messages.append(msg)
                continue

            # 2. 신규 평문 메시지만 암호화 수행
            content_plain = msg.get("content", "")
            # AESEncryption.encrypt 로직을 수정 없이 그대로 사용 (고정 IV 반환)
            enc_bytes, iv_bytes = self.crypto.encrypt(content_plain)

            # JSON 내부에 저장하기 위해 Base64 인코딩
            processed_messages.append({
                "role": msg.get("role"),
                "content": base64.b64encode(enc_bytes).decode('utf-8'),
                "iv": base64.b64encode(iv_bytes).decode('utf-8'),
                "timestamp": msg.get("timestamp")
            })

        orm_chat = SimulationChatORM(
            id=chat.id,
            account_id=chat.account_id,
            mbti=chat.mbti,
            topic=chat.topic,
            gender=chat.gender,
            messages=processed_messages,
            is_training_data=chat.is_training_data,
            created_at=chat.created_at,
            updated_at=chat.updated_at
        )

        try:
            if is_new:
                self.db.add(orm_chat)
            else:
                self.db.merge(orm_chat)
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            raise e

    async def find_by_id(self, chat_id: str) -> Optional[SimulationChat]:
        orm = self.db.query(SimulationChatORM).filter(SimulationChatORM.id == chat_id).first()
        if not orm:
            return None
        return SimulationChat(
            id=orm.id,
            account_id=orm.account_id,
            mbti=orm.mbti,
            topic=orm.topic,
            gender=orm.gender,
            messages=orm.messages,
            is_training_data=orm.is_training_data,
            created_at=orm.created_at,
            updated_at=orm.updated_at
        )

    async def find_all_by_account_id(self, account_id: int) -> List[SimulationChat]:
        orm_list = self.db.query(SimulationChatORM).filter(
            SimulationChatORM.account_id == account_id
        ).order_by(SimulationChatORM.created_at.desc()).all()

        return [
            SimulationChat(
                id=orm.id,
                account_id=orm.account_id,
                mbti=orm.mbti,
                topic=orm.topic,
                gender=orm.gender,
                messages=orm.messages,
                is_training_data=orm.is_training_data,
                created_at=orm.created_at,
                updated_at=orm.updated_at
            ) for orm in orm_list
        ]

    async def delete_by_id(self, chat_id: str, account_id: int) -> bool:
        try:
            query = self.db.query(SimulationChatORM).filter(
                SimulationChatORM.id == chat_id,
                SimulationChatORM.account_id == account_id
            )

            target = query.first()

            if not target:
                return False

            query.delete(synchronize_session=False)
            self.db.commit()
            return True

        except Exception as e:
            self.db.rollback()
            print(f"Delete Error: {e}")
            raise e