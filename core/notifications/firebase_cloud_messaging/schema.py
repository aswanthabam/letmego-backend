from enum import Enum as PyEnum
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, field_validator


class DeviceType(str, PyEnum):
    ANDROID = "android"
    IOS = "ios"
    WEB = "web"


class NotificationPriority(str, PyEnum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"


class AndroidNotificationPriority(str, PyEnum):
    MIN = "min"
    LOW = "low"
    DEFAULT = "default"
    HIGH = "high"
    MAX = "max"


class NotificationStatus(str, PyEnum):
    """
    Status of the notification.
    SENT: Successfully sent to FCM.
    FAILED: Failed to send to FCM due to an error.
    """

    SENT = "sent"
    FAILED = "failed"


class FCMNotification(BaseModel):
    """FCM Notification payload model"""

    title: str = Field(..., description="Notification title")
    body: str = Field(..., description="Notification body")
    image: Optional[str] = Field(None, description="Image URL for rich notifications")


class AndroidConfig(BaseModel):
    """Android-specific configuration"""

    collapse_key: Optional[str] = None
    priority: NotificationPriority = NotificationPriority.HIGH
    ttl: Optional[int] = Field(None, description="Time to live in seconds")
    restricted_package_name: Optional[str] = None
    data: Optional[Dict[str, str]] = None

    notification_priority: AndroidNotificationPriority = (
        AndroidNotificationPriority.HIGH
    )
    sound: str = "default"
    click_action: Optional[str] = None
    color: Optional[str] = None
    tag: Optional[str] = None
    channel_id: Optional[str] = "default"


class APNSConfig(BaseModel):
    """Apple Push Notification Service configuration"""

    headers: Optional[Dict[str, str]] = None
    badge: Optional[int] = None
    sound: str = "default"
    content_available: bool = False
    mutable_content: bool = False
    category: Optional[str] = None
    thread_id: Optional[str] = None


class WebpushConfig(BaseModel):
    """Web push configuration"""

    headers: Optional[Dict[str, str]] = None
    data: Optional[Dict[str, str]] = None
    notification: Optional[Dict[str, Any]] = None

    icon: Optional[str] = None
    badge: Optional[str] = None
    image: Optional[str] = None
    actions: Optional[List[Dict[str, str]]] = None


class FCMMessage(BaseModel):
    """Complete FCM message model for single token sends"""

    token: str = Field(..., description="Device registration token")

    notification: Optional[FCMNotification] = None
    data: Optional[Dict[str, str]] = None

    android: Optional[AndroidConfig] = None
    apns: Optional[APNSConfig] = None
    webpush: Optional[WebpushConfig] = None

    @field_validator("data")
    @classmethod
    def validate_data(cls, v):
        if v:
            for key, value in v.items():
                if not isinstance(value, str):
                    v[key] = str(value)
        return v


class FCMOperationResult(BaseModel):
    """
    Response containing details about the FCM operation.
    """

    success: bool
    fcm_message_id: Optional[str] = Field(
        None, description="FCM message ID if successful"
    )
    fcm_error_code: Optional[str] = Field(None, description="FCM error code if failed")
    error_message: Optional[str] = Field(
        None, description="Detailed error message if failed"
    )
    notification_status: NotificationStatus = Field(
        ..., description="Status of the notification (SENT/FAILED)"
    )
