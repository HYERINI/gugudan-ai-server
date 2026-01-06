from abc import ABC, abstractmethod
from typing import Optional, List

from app.simulation.domain.entity.simulation_chat import SimulationChat

class SimulationRepositoryPort(ABC):
    @abstractmethod
    async def save(self, chat: SimulationChat, is_new: bool = False) -> None:
        pass

    @abstractmethod
    async def find_by_id(self, chat_id: str) -> Optional[SimulationChat]:
        pass

    @abstractmethod
    async def find_all_by_account_id(self, account_id: int) -> List[SimulationChat]:
        pass

    @abstractmethod
    async def delete_by_id(self, chat_id: str, account_id: int) -> bool:
        pass