import io
import os
from typing import Optional

from core.storage.sqlalchemy.fields.abstract import AbstractFileField
from core.storage.storage_class.abstract import Storage


class FileObject(str):
    def __new__(cls, storage, file_path, file_url):
        obj = str.__new__(cls, file_url)
        obj.storage = storage
        obj.file_path = file_path
        obj.file_url = file_url
        return obj

    def delete(self):
        raise NotImplementedError(
            "File does not support direct delete operation. Use the S3 client to delete the file."
        )


class FileField(AbstractFileField):
    """
    A custom SQLAlchemy field for handling file uploads with S3 storage.
    Stores the file path and handles direct file uploads without variants.
    """

    def __init__(
        self,
        storage=None,
        upload_to="uploads",
        max_size: int = 50 * 1024 * 1024,  # 50MB default
        allowed_extensions: Optional[list[str]] = None,
    ):
        super().__init__(storage, upload_to)
        self.max_size = max_size
        self.allowed_extensions = allowed_extensions

    def save_file(self, content, path):
        ext = path.split(".")[-1].lower()
        if self.allowed_extensions and ext not in self.allowed_extensions:
            raise ValueError(
                f"Unsupported file extension. Allowed extensions: {self.allowed_extensions}"
            )

        if isinstance(content, bytes):
            file_size = len(content)
        elif isinstance(content, io.BytesIO):
            content.seek(0, os.SEEK_END)
            file_size = content.tell()
            content.seek(0)

        if self.max_size and file_size > self.max_size:
            raise ValueError(
                f"File size exceeds maximum allowed size of {self.max_size} bytes"
            )

        self.storage.save(
            content=content,
            filepath=path,
            content_type=None,  # Content type can be determined by the storage system
        )

    def get_result(self, path):
        url = self.storage.get_url(path)
        return FileObject(storage=self.storage, file_path=path, file_url=url)
