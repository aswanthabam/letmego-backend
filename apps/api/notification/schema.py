from enum import Enum


class NotificationCategory(str, Enum):
    """Defines the broad category of a notification."""

    IN_APP = "in_app"
    PUSH = "push"
    EMAIL = "email"
    SMS = "sms"


class NotificationStatus(str, Enum):
    """Defines the user's interaction status with a conceptual notification."""

    UNREAD = "unread"
    READ = "read"
    CLICKED = "clicked"


class NotificationChannelType(str, Enum):
    """Defines the specific channel through which a notification is sent."""

    FCM_PUSH = "fcm_push"
    IN_APP_CHANNEL = "in_app_channel"
    SMS_CHANNEL = "sms_channel"
    EMAIL_CHANNEL = "email_channel"


class ChannelDeliveryStatus(str, Enum):
    """Defines the delivery and interaction status on a specific channel."""

    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    DELIVERED = "delivered"
    SEEN = "seen"
    CLICKED = "clicked"
