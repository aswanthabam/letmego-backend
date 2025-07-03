from datetime import date
from uuid import uuid4


class InputFile:
    def __init__(
        self,
        content: bytes,
        filename: str,
        folder: str = None,
        prefix_date: bool = True,
        unique_filename: bool = True,
    ):
        """
        Initialize a File instance with content.

        Args:
            content (bytes): The file content.
        """
        self.content = content
        if "." in filename:
            ext = filename.split(".")[-1]
        else:
            ext = None

        if unique_filename:
            filename = str(uuid4()) + (f".{ext}" if ext else "")

        if folder:
            if folder.endswith("/"):
                folder = folder[:-1]
            filename = f"{folder}/{filename}"

        if prefix_date:
            date_folder = date.today().isoformat()
            filename = f"{date_folder}/{filename}"

        self.filename = filename
