from abc import ABC, abstractmethod

from app.models.case import Finding, Target


class BaseAdapter(ABC):
    name: str = "base"
    description: str = ""
    supported_target_types: list = []

    @abstractmethod
    async def run(self, target: Target) -> list[Finding]:
        pass

    def can_handle(self, target: Target) -> bool:
        return target.type in self.supported_target_types
