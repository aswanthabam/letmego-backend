from core.exceptions.core import AbstractException


class InvalidRequestException(AbstractException):
    def __init__(
        self, message, err_code="INVALID_REQUEST", status_code=400, *args, **kwargs
    ):
        super().__init__(
            message=message, err_code=err_code, status_code=status_code, *args, **kwargs
        )
