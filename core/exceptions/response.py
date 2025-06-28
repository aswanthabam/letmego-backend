from core.exceptions.core import AbstractException


class ServerSideException(AbstractException):

    def __init__(
        self, message, err_code="SERVER_ERROR", status_code=500, *args, **kwargs
    ):
        super().__init__(
            message=message, err_code=err_code, status_code=status_code, *args, **kwargs
        )
