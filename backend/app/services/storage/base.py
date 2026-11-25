from abc import ABC, abstractmethod
from pathlib import Path
from typing import BinaryIO


class StorageService(ABC):

    @abstractmethod
    def save(
        self,
        file: BinaryIO,
        storage_key: str,
    ) -> int:
        """Save a file and return its byte size."""
        raise NotImplementedError

    @abstractmethod
    def open(self, storage_key: str) -> BinaryIO:
        """Open a stored file for reading."""
        raise NotImplementedError

    @abstractmethod
    def delete(self, storage_key: str) -> None:
        """Delete a stored file."""
        raise NotImplementedError

    @abstractmethod
    def exists(self, storage_key: str) -> bool:
        raise NotImplementedError