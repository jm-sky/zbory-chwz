"""Local filesystem storage adapter."""

import shutil
from pathlib import Path

import aiofiles

from app.core.storage.adapter import StorageAdapter


class LocalStorageAdapter(StorageAdapter):
    """Local filesystem storage adapter."""

    def __init__(self, base_path: str = "./uploads", base_url: str | None = None):
        """
        Initialize local storage adapter.

        Args:
            base_path: Base directory for file storage
            base_url: Base URL for serving files (e.g., https://api.gear-stack.com). If None, uses relative paths.
        """
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.base_url = base_url.rstrip("/") if base_url else None

    async def upload(
        self,
        file_content: bytes,
        destination_path: str,
        content_type: str,
        metadata: dict | None = None,
    ) -> str:
        """Upload file to local filesystem."""
        full_path = self.base_path / destination_path
        full_path.parent.mkdir(parents=True, exist_ok=True)

        async with aiofiles.open(full_path, "wb") as f:
            await f.write(file_content)

        return str(destination_path)

    async def download(self, file_path: str) -> bytes:
        """Download file from local filesystem."""
        full_path = self.base_path / file_path
        async with aiofiles.open(full_path, "rb") as f:
            content: bytes = await f.read()
            return content

    async def delete(self, file_path: str) -> bool:
        """Delete file from local filesystem."""
        full_path = self.base_path / file_path
        if full_path.exists():
            full_path.unlink()
            return True
        return False

    async def exists(self, file_path: str) -> bool:
        """Check if file exists."""
        return (self.base_path / file_path).exists()

    async def get_url(self, file_path: str, expires_in: int = 3600) -> str:
        """Get URL for local file (served via FastAPI static files)."""
        url_path = f"/uploads/{file_path}"
        if self.base_url:
            return f"{self.base_url}{url_path}"
        return url_path

    async def get_available_space(self) -> int | None:
        """Get available disk space."""
        stat = shutil.disk_usage(self.base_path)
        return stat.free
