class AbstractException(Exception):
    def __init__(
        self,
        message: str,
        err_code: str | None = None,
        status_code: int = 500,
        *args,
        **kwargs,
    ):
        super().__init__(*args)
        self.message = message
        self.error_code = err_code
        self.kwargs = kwargs
        self.status_code = status_code

    def to_json(self):
        return {
            **self.kwargs,
            "message": self.message,
            "error_code": self.error_code,
        }

    def __str__(self):
        return f"RESPONSE: <{self.__class__.__name__}> {self.message})"
