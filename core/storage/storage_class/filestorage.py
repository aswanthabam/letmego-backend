import os
from pathlib import Path
from core.storage.storage_class.abstract import Storage


class FileSystemStorage(Storage):
    def __init__(self, volume, base_path, url_prefix=None):
        super().__init__(volume, base_path)
        self.url_prefix = url_prefix or ""

    def save(self, content, filepath, *args, **kwargs):
        """
        Synchronously save a file buffer to the local filesystem at volume/base_path/filepath.

        Args:
            content (bytes or file-like object): The file data to write.
            filepath (str): The relative path where the file should be saved.

        Returns:
            str: The full path to the saved file.

        Raises:
            IOError: If the file could not be written.
        """
        full_path = Path(self.volume) / self.base_path / filepath

        try:
            # Ensure the parent directories exist
            full_path.parent.mkdir(parents=True, exist_ok=True)

            with open(full_path, "wb") as f:
                content = self._get_bytes(content)
                f.write(content)

            return str(full_path)

        except Exception as e:
            raise IOError(f"Failed to save file to {full_path}: {e}")

    def get_path(self, filepath):
        full_path = Path(self.volume) / self.base_path / filepath
        return str(full_path)

    def get_url(self, filepath):
        """
        Get the URL for a file stored in the local filesystem.

        Args:
            filepath (str): The relative path to the file.

        Returns:
            str: The URL to access the file.
        """
        full_path = str(Path(self.volume) / self.base_path / filepath)

        if self.url_prefix:
            if full_path.startswith("/"):
                full_path = full_path[1:]
            return f"{self.url_prefix}/{full_path}" if full_path else None
        return full_path
