# --- Custom Exception Classes ---
from typing import Optional


class FirebaseException(Exception):
    """Base exception for Firebase Cloud Messaging operations."""

    def __init__(self, message: str, fcm_error_code: Optional[str] = None):
        super().__init__(message)
        self.fcm_error_code = fcm_error_code
        self.error_message = message


class FirebaseInvalidArgumentError(FirebaseException):
    """Raised when an FCM message contains invalid arguments."""

    def __init__(
        self, message: str, fcm_error_code: Optional[str] = "INVALID_ARGUMENT"
    ):
        super().__init__(message, fcm_error_code)


class FirebaseUnregisteredTokenError(FirebaseException):
    """Raised when a device token is unregistered or invalid."""

    def __init__(
        self, message: str, token: str, fcm_error_code: Optional[str] = "UNREGISTERED"
    ):
        super().__init__(message, fcm_error_code)
        self.invalid_token = token


class FirebaseQuotaExceededError(FirebaseException):
    """Raised when FCM quota is exceeded."""

    def __init__(self, message: str, fcm_error_code: Optional[str] = "QUOTA_EXCEEDED"):
        super().__init__(message, fcm_error_code)


class FirebaseUnavailableError(FirebaseException):
    """Raised when FCM service is temporarily unavailable."""

    def __init__(self, message: str, fcm_error_code: Optional[str] = "UNAVAILABLE"):
        super().__init__(message, fcm_error_code)


class FirebaseUnknownError(FirebaseException):
    """Raised for any other unknown FCM errors."""

    def __init__(self, message: str, fcm_error_code: Optional[str] = "UNKNOWN_ERROR"):
        super().__init__(message, fcm_error_code)
