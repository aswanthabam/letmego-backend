import io
from abc import ABC, abstractmethod


class Storage(ABC):
    def __init__(self, volume: str, base_path: str):
        """
        Initialize a storage instance.

        Args:
            volume (str): Root directory or mount point for storage.
            base_path (str): Subdirectory inside the volume to store files.
        """
        self.volume = volume
        self.base_path = base_path

    def _get_bytes(self, content: bytes | io.BytesIO):
        """
        Convert the input content to bytes.

        Args:
            content (Union[UploadFile, BytesIO, bytes]): The file content.

        Returns:
            bytes: The content as bytes.
        """
        if isinstance(content, io.BytesIO):
            return content.getvalue()
        elif isinstance(content, bytes):
            return content
        else:
            raise TypeError(
                "Unsupported content. Must be UploadFile, BytesIO, or bytes."
            )

    @abstractmethod
    def save(
        self,
        content: bytes,
        filepath: str,
        content_type: str | None = None,
    ) -> str:
        """
        Synchronously save a file to the storage system.

        Args:
            content (Union[UploadFile, BytesIO, bytes]): The file content.
                - UploadFile: typical FastAPI upload
                - BytesIO: in-memory stream
                - bytes: raw binary data
            filepath (str): Relative file path where the file should be stored.
            content_type (str | None): MIME type of the file, optional.

        Returns:
            str: The final saved file path.

        Raises:
            IOError: If saving the file fails.
        """
        raise NotImplementedError("Subclasses must implement this method.")

    @abstractmethod
    def get_path(self, filepath: str) -> str:
        """
        Get the full path to a file in the storage system.

        Args:
            filepath (str): Relative file path.

        Returns:
            str: Full path to the file in the storage system.
        """
        raise NotImplementedError("Subclasses must implement this method.")

    @abstractmethod
    def get_url(self, filepath: str) -> str:
        """
        Get the URL for accessing a file in the storage system.

        Args:
            filepath (str): Relative file path.

        Returns:
            str: URL to access the file.
        """
        raise NotImplementedError("Subclasses must implement this method.")
