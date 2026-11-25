from abc import ABC, abstractmethod
from typing import Any


class BaseEngine(ABC):

    @abstractmethod
    def process(
        self,
        input_data: dict[str, Any]
    ) -> dict[str, Any]:
        pass

    @abstractmethod
    def get_engine_info(self) -> dict[str, Any]:
        pass