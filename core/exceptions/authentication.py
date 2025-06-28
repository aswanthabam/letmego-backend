from core.exceptions.core import AbstractException


class UnauthorizedException(AbstractException):

    def __init__(
        self, message, err_code="UNAUTHORIZED", status_code=401, *args, **kwargs
    ):
        super().__init__(
            message=message, err_code=err_code, status_code=status_code, *args, **kwargs
        )


class ForbiddenException(AbstractException):

    def __init__(self, message, err_code="FORBIDDEN", status_code=403, *args, **kwargs):
        super().__init__(
            message=message, err_code=err_code, status_code=status_code, *args, **kwargs
        )


class TokenExpiredException(AbstractException):

    def __init__(
        self, message, err_code="TOKEN_EXPIRED", status_code=401, *args, **kwargs
    ):
        super().__init__(
            message=message, err_code=err_code, status_code=status_code, *args, **kwargs
        )


class TokenInvalidException(AbstractException):

    def __init__(
        self, message, err_code="TOKEN_INVALID", status_code=401, *args, **kwargs
    ):
        super().__init__(
            message=message, err_code=err_code, status_code=status_code, *args, **kwargs
        )


class TokenUpdatedException(AbstractException):

    def __init__(
        self, message, err_code="TOKEN_UPDATED", status_code=401, *args, **kwargs
    ):
        super().__init__(
            message=message, err_code=err_code, status_code=status_code, *args, **kwargs
        )
