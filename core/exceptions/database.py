from core.exceptions.core import AbstractException


class NotFoundException(AbstractException):
    def __init__(self, message, err_code="NOT_FOUND", status_code=404, *args, **kwargs):
        super().__init__(
            message=message, err_code=err_code, status_code=status_code, *args, **kwargs
        )
