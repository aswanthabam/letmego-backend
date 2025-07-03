import os
import io
from typing import Dict, Optional, Union
from sqlalchemy.types import TypeDecorator, String

from core.exceptions.request import InvalidRequestException
from core.storage.sqlalchemy.inputs.file import InputFile
from core.storage.storage_class.abstract import Storage


class AbstractFileField(TypeDecorator):
    """
    A custom SQLAlchemy field for handling images with S3 storage.
    Only stores the original file path and generates variants on demand.
    """

    impl = String
    cache_ok = True

    def __init__(
        self,
        storage: Storage,
        upload_to: str = "uploads",
    ):
        super().__init__()
        self.storage = storage
        self.upload_to = upload_to

    def _get_filepath(self, path: str) -> str:
        """Generate the full file path for the image."""
        return os.path.join(self.upload_to, path)

    def save_file(self, content: bytes, path: str) -> str:
        """Save the file to the storage and return the file path."""
        raise NotImplementedError("Subclasses must implement save_file method.")

    def get_result(self, path: str):
        """
        Get the URL for the file stored in the storage system.
        """
        raise NotImplementedError("Subclasses must implement get_file_url method.")

    def process_bind_param(
        self, value: Union[Dict, bytes, io.BytesIO], dialect
    ) -> Optional[str]:
        """Process the value before saving to database."""

        if not value:
            return None

        if isinstance(value, str):
            return value

        try:
            if not isinstance(value, InputFile):
                raise InvalidRequestException(
                    message="Invalid input type. Expected File, dict, bytes, or io.BytesIO."
                )
            path = self._get_filepath(
                value.filename
            )  # this will be the value stored in the database
            self.save_file(content=value.content, path=path)
            return path
        except InvalidRequestException as e:
            raise e
        except Exception as e:
            raise ValueError(f"Error processing image: {str(e)}")

    def process_result_value(self, value: str, dialect) -> Optional[str]:
        """Process the value when retrieving from database."""
        return self.get_result(value)
