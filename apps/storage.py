from core.storage.storage_class import FileSystemStorage

default_storage = FileSystemStorage(
    volume="media",
    base_path="",
    url_prefix="http://localhost:8000/media",
)
