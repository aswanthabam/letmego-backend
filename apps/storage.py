from apps.settings import settings
from core.storage.storage_class import FileSystemStorage

default_storage = FileSystemStorage(
    volume="media",
    base_path="",
    url_prefix=settings.STORAGE_URL_PREFIX,
)
