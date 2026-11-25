from app.core.config import settings
from app.services.storage.base import StorageService
from app.services.storage.local import LocalStorageService


def get_storage_service() -> StorageService:
    backend = settings.STORAGE_BACKEND.lower()

    if backend == "local":
        return LocalStorageService()

    raise ValueError(
        f"Unsupported storage backend: {backend}"
    )