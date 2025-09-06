from apps.settings import settings
from avcfastapi.core.storage.storage_class.filestorage import FileSystemStorage

default_storage = FileSystemStorage(
    volume="media",
    base_path="",
    url_prefix=settings.STORAGE_URL_PREFIX,
)
