from pathlib import Path
from typing import BinaryIO

from app.core.config import settings
from app.services.storage.base import StorageService


class LocalStorageService(StorageService):

    def __init__(self):
        self.root = Path(settings.LOCAL_STORAGE_PATH).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _resolve(self, storage_key: str) -> Path:
        path = (self.root / storage_key).resolve()

        # Prevent path traversal outside the storage directory.
        if not path.is_relative_to(self.root):
            raise ValueError("Invalid storage key")

        return path

    def save(self, file: BinaryIO, storage_key: str) -> int:
        destination = self._resolve(storage_key)
        destination.parent.mkdir(parents=True, exist_ok=True)

        total_size = 0

        with destination.open("wb") as output:
            while chunk := file.read(1024 * 1024):
                output.write(chunk)
                total_size += len(chunk)

        return total_size

    def open(self, storage_key: str) -> BinaryIO:
        path = self._resolve(storage_key)

        if not path.is_file():
            raise FileNotFoundError(storage_key)

        return path.open("rb")

    def delete(self, storage_key: str) -> None:
        path = self._resolve(storage_key)

        if path.exists():
            path.unlink()

    def exists(self, storage_key: str) -> bool:
        return self._resolve(storage_key).is_file()