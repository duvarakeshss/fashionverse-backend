import os
from abc import ABC, abstractmethod
from pathlib import Path
from app.config import settings

class StorageBackend(ABC):
    """Abstract interface for storing, deleting, and checking files."""

    @abstractmethod
    async def save(self, file_bytes: bytes, destination_path: str) -> str:
        """
        Saves the file bytes to the destination path.
        Returns the relative path to the saved file.
        """
        pass

    @abstractmethod
    async def delete(self, path: str) -> None:
        """Deletes the file at the specified relative path."""
        pass

    @abstractmethod
    async def exists(self, path: str) -> bool:
        """Checks if a file exists at the specified relative path."""
        pass


class LocalStorageBackend(StorageBackend):
    """Local filesystem storage implementation of StorageBackend."""

    def __init__(self, base_dir: Path = settings.UPLOAD_DIR):
        self.base_dir = base_dir

    def _get_full_path(self, relative_path: str) -> Path:
        """Converts a relative path to an absolute Path object, ensuring safety."""
        # Normalize path to prevent directory traversal
        norm_path = os.path.normpath(relative_path).lstrip("\\/")
        return self.base_dir / norm_path

    async def save(self, file_bytes: bytes, destination_path: str) -> str:
        full_path = self._get_full_path(destination_path)
        
        # Ensure directories exist
        full_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write bytes asynchronously using standard async code
        # Since standard open is blocking, let's run in thread pool or use standard write.
        # Run sync write in threadpool to prevent blocking FastAPI async loop
        import anyio
        def write_file():
            with open(full_path, "wb") as f:
                f.write(file_bytes)
        await anyio.to_thread.run_sync(write_file)
        
        # Return standardized relative path using forward slashes
        norm_relative = os.path.normpath(destination_path).replace("\\", "/")
        return norm_relative.lstrip("/")

    async def delete(self, path: str) -> None:
        if not path:
            return
        full_path = self._get_full_path(path)
        import anyio
        def remove_file():
            if full_path.exists() and full_path.is_file():
                full_path.unlink()
        await anyio.to_thread.run_sync(remove_file)

    async def exists(self, path: str) -> bool:
        if not path:
            return False
        full_path = self._get_full_path(path)
        import anyio
        def check_exists():
            return full_path.exists() and full_path.is_file()
        return await anyio.to_thread.run_sync(check_exists)


def get_storage_backend() -> StorageBackend:
    """Dependency injection provider for the active storage backend."""
    return LocalStorageBackend()
