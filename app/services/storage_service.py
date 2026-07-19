import os
from abc import ABC, abstractmethod
from pathlib import Path
from app.config import settings
from azure.storage.blob.aio import BlobServiceClient


class StorageBackend(ABC):
    """Abstract interface for storing, deleting, and checking files."""

    @abstractmethod
    async def initialize(self) -> None:
        """Initializes the backend (e.g. creating local directories or cloud containers)."""
        pass

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

    @abstractmethod
    def get_url(self, path: str) -> str:
        """Returns the public URL (relative or absolute) to access the file."""
        pass

    async def close(self) -> None:
        """Closes any open client connections (no-op by default)."""
        pass


class LocalStorageBackend(StorageBackend):
    """Local filesystem storage implementation of StorageBackend."""

    def __init__(self, base_dir: Path = settings.UPLOAD_DIR):
        self.base_dir = base_dir

    async def initialize(self) -> None:
        # Create directories
        for directory in [
            self.base_dir,
            self.base_dir / "profiles",
            self.base_dir / "wardrobe",
            self.base_dir / "processed",
            self.base_dir / "thumbnails",
            self.base_dir / "temp",
        ]:
            directory.mkdir(parents=True, exist_ok=True)

    def _get_full_path(self, relative_path: str) -> Path:
        """Converts a relative path to an absolute Path object, ensuring safety."""
        # Normalize path to prevent directory traversal
        norm_path = os.path.normpath(relative_path).lstrip("\\/")
        return self.base_dir / norm_path

    async def save(self, file_bytes: bytes, destination_path: str) -> str:
        full_path = self._get_full_path(destination_path)
        
        # Ensure directories exist
        full_path.parent.mkdir(parents=True, exist_ok=True)
        
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

    def get_url(self, path: str) -> str:
        norm_path = os.path.normpath(path).replace("\\", "/").lstrip("/")
        return f"/uploads/{norm_path}"


class AzureBlobStorageBackend(StorageBackend):

    def __init__(self, connection_string: str, container_name: str):
        self.connection_string = connection_string
        self.container_name = container_name
        self.blob_service_client = BlobServiceClient.from_connection_string(connection_string)

    async def initialize(self) -> None:
        container_client = self.blob_service_client.get_container_client(self.container_name)
        try:
            await container_client.create_container()
        except Exception:
            pass

    async def save(self, file_bytes: bytes, destination_path: str) -> str:
        norm_dest = destination_path.replace("\\", "/").lstrip("/")
        container_client = self.blob_service_client.get_container_client(self.container_name)
        blob_client = container_client.get_blob_client(norm_dest)
        await blob_client.upload_blob(file_bytes, overwrite=True)
        return norm_dest

    async def delete(self, path: str) -> None:
        if not path:
            return
        from azure.core.exceptions import ResourceNotFoundError
        norm_path = path.replace("\\", "/").lstrip("/")
        container_client = self.blob_service_client.get_container_client(self.container_name)
        blob_client = container_client.get_blob_client(norm_path)
        try:
            await blob_client.delete_blob()
        except ResourceNotFoundError:
            pass

    async def exists(self, path: str) -> bool:
        if not path:
            return False
        from azure.core.exceptions import ResourceNotFoundError
        norm_path = path.replace("\\", "/").lstrip("/")
        container_client = self.blob_service_client.get_container_client(self.container_name)
        blob_client = container_client.get_blob_client(norm_path)
        try:
            await blob_client.get_blob_properties()
            return True
        except ResourceNotFoundError:
            return False

    def get_url(self, path: str) -> str:
        account_name = None
        for pair in self.connection_string.split(";"):
            if "=" in pair:
                key, val = pair.split("=", 1)
                if key.strip().lower() == "accountname":
                    account_name = val.strip()
                    break
        if not account_name:
            account_name = "azurestd01"
            
        norm_path = path.replace("\\", "/").lstrip("/")
        return f"https://{account_name}.blob.core.windows.net/{self.container_name}/{norm_path}"

    async def close(self) -> None:
        await self.blob_service_client.close()


_active_storage_backend: StorageBackend | None = None

def get_storage_backend() -> StorageBackend:
    """Dependency injection provider for the active storage backend."""
    global _active_storage_backend
    if _active_storage_backend is None:
        if settings.AZURE_STORAGE_CONNECTION_STRING and settings.AZURE_BLOB_CONTAINER_NAME:
            _active_storage_backend = AzureBlobStorageBackend(
                connection_string=settings.AZURE_STORAGE_CONNECTION_STRING,
                container_name=settings.AZURE_BLOB_CONTAINER_NAME
            )
        else:
            _active_storage_backend = LocalStorageBackend()
    return _active_storage_backend
