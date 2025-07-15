import logging
import os
from typing import Optional, Dict, Any
from firebase_admin import messaging, initialize_app, credentials
import firebase_admin

from core.notifications.firebase_cloud_messaging.exceptions import (
    FirebaseInvalidArgumentError,
    FirebaseQuotaExceededError,
    FirebaseUnavailableError,
    FirebaseUnknownError,
    FirebaseUnregisteredTokenError,
)
from core.notifications.firebase_cloud_messaging.schema import (
    FCMMessage,
    FCMOperationResult,
    NotificationStatus,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FirebaseCloudMessagingCore:
    """
    Standalone FCM Handler focused on sending single notifications to device tokens.
    Handles error scenarios by raising custom FirebaseException types.
    """

    def __init__(
        self,
        service_account_path: Optional[str] = None,
        service_account_info: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize FCM Handler

        Args:
            service_account_path: Path to service account JSON file
            service_account_info: Service account info as dictionary
        """
        self._initialize_firebase(service_account_path, service_account_info)

    def _initialize_firebase(
        self,
        service_account_path: Optional[str],
        service_account_info: Optional[Dict[str, Any]],
    ):
        """Initialize Firebase Admin SDK"""
        # Check if an app is already initialized to prevent re-initialization errors
        if not firebase_admin._apps:
            try:
                if service_account_path:
                    cred = credentials.Certificate(service_account_path)
                elif service_account_info:
                    cred = credentials.Certificate(service_account_info)
                else:
                    cred = credentials.ApplicationDefault()

                initialize_app(cred)
                logger.info("Firebase initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Firebase: {e}", exc_info=True)
                raise FirebaseUnknownError(f"Failed to initialize Firebase: {str(e)}")
        else:
            logger.info("Firebase already initialized.")

    def send_to_token(self, message: FCMMessage) -> FCMOperationResult:
        """
        Send notification to a single token and return operation result details.
        Raises custom FirebaseException on failure.

        Args:
            message: FCM message with token specified

        Returns:
            FCMOperationResult with operation result and details.

        Raises:
            FirebaseInvalidArgumentError: If the message is malformed.
            FirebaseUnregisteredTokenError: If the token is invalid/unregistered.
            FirebaseQuotaExceededError: If FCM sending quota is exceeded.
            FirebaseUnavailableError: If FCM service is temporarily unavailable.
            FirebaseUnknownError: For any other unexpected errors.
        """
        try:
            fcm_firebase_message = self._build_firebase_message(message)
            response_id = messaging.send(fcm_firebase_message)

            logger.info(
                f"Message sent successfully to token: {message.token[:10]}... Message ID: {response_id}"
            )
            return FCMOperationResult(
                success=True,
                fcm_message_id=response_id,
                notification_status=NotificationStatus.SENT,
            )

        except messaging.InvalidArgumentError as e:
            logger.error(f"Invalid argument for FCM message: {e}", exc_info=True)
            raise FirebaseInvalidArgumentError(
                str(e), fcm_error_code=e.code.name if hasattr(e, "code") else None
            )
        except messaging.UnregisteredError as e:
            logger.error(
                f"Unregistered token: {message.token[:10]}... Error: {e}", exc_info=True
            )
            raise FirebaseUnregisteredTokenError(
                str(e),
                token=message.token,
                fcm_error_code=e.code.name if hasattr(e, "code") else None,
            )
        except messaging.QuotaExceededError as e:
            logger.error(f"FCM quota exceeded: {e}", exc_info=True)
            raise FirebaseQuotaExceededError(
                str(e), fcm_error_code=e.code.name if hasattr(e, "code") else None
            )
        except messaging.UnavailableError as e:
            logger.error(f"FCM service unavailable: {e}", exc_info=True)
            raise FirebaseUnavailableError(
                str(e), fcm_error_code=e.code.name if hasattr(e, "code") else None
            )
        except Exception as e:
            logger.error(
                f"An unexpected error occurred while sending FCM message: {e}",
                exc_info=True,
            )
            raise FirebaseUnknownError(f"Unexpected error: {str(e)}")

    def _build_firebase_message(self, message: FCMMessage) -> messaging.Message:
        """
        Build Firebase message from FCMMessage model for a single token.

        Args:
            message: FCM message model

        Returns:
            Firebase messaging.Message object
        """
        kwargs = {"token": message.token}

        # Set notification
        if message.notification:
            kwargs["notification"] = messaging.Notification(
                title=message.notification.title,
                body=message.notification.body,
                image=message.notification.image,
            )

        # Set data
        if message.data:
            kwargs["data"] = message.data

        # Set Android config
        if message.android:
            android_notification = None
            if (
                message.notification
            ):  # Use top-level notification for Android if available
                android_notification = messaging.AndroidNotification(
                    title=message.notification.title,
                    body=message.notification.body,
                    # image is not directly in AndroidNotification, often passed via data payload
                    icon=None,  # Assuming icon is not passed via generic FCMNotification
                    color=message.android.color,
                    sound=message.android.sound,
                    tag=message.android.tag,
                    click_action=message.android.click_action,
                    channel_id=message.android.channel_id,
                    priority=message.android.notification_priority.value,
                )
            # If AndroidConfig has its own data, merge it with the main data payload
            android_data_merged = message.data.copy() if message.data else {}
            if message.android.data:
                android_data_merged.update(message.android.data)

            kwargs["android"] = messaging.AndroidConfig(
                collapse_key=message.android.collapse_key,
                priority=message.android.priority.value,
                ttl=message.android.ttl,
                restricted_package_name=message.android.restricted_package_name,
                data=android_data_merged,
                notification=android_notification,
            )

        # Set APNS config
        if message.apns:
            apns_alert = None
            if message.notification:  # Use top-level notification for APNS if available
                apns_alert = messaging.ApsAlert(
                    title=message.notification.title,
                    body=message.notification.body,
                    # image not directly in ApsAlert, often handled via mutable-content or data
                )

            kwargs["apns"] = messaging.APNSConfig(
                headers=message.apns.headers,
                payload=messaging.APNSPayload(
                    aps=messaging.Aps(
                        alert=apns_alert,
                        badge=message.apns.badge,
                        sound=message.apns.sound,
                        content_available=message.apns.content_available,
                        mutable_content=message.apns.mutable_content,
                        category=message.apns.category,
                        thread_id=message.apns.thread_id,
                    )
                ),
            )

        # Set Webpush config
        if message.webpush:
            webpush_notification_dict = None
            # Prioritize webpush.notification if provided, otherwise use generic FCMNotification
            if message.webpush.notification:
                webpush_notification_dict = message.webpush.notification
            elif message.notification:
                webpush_notification_dict = {
                    "title": message.notification.title,
                    "body": message.notification.body,
                    "image": message.notification.image,  # Webpush notification supports image
                    "icon": message.webpush.icon,
                    "badge": message.webpush.badge,
                    "actions": message.webpush.actions,
                }
                # Clean up None values
                webpush_notification_dict = {
                    k: v for k, v in webpush_notification_dict.items() if v is not None
                }

            kwargs["webpush"] = messaging.WebpushConfig(
                headers=message.webpush.headers,
                data=message.webpush.data,
                notification=webpush_notification_dict,
            )

        return messaging.Message(**kwargs)
