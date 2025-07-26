from sqlalchemy import select
from typing import Optional, Annotated
from uuid import UUID
from datetime import datetime, timezone

# Your project's specific imports
from apps.api.notification.models import Notification, NotificationChannel
from apps.api.device.models import Device
from apps.api.device.schema import (
    DeviceStatus,
)  # To update device on unregistered token
from apps.api.notification.schema import ChannelDeliveryStatus
from core.architecture.service import AbstractService
from core.db.core import SessionDep

# --- Import your new FCM Core, Schemas, and Exceptions ---
from core.exceptions.database import NotFoundException
from core.notifications.firebase_cloud_messaging.core import FirebaseCloudMessagingCore
from core.notifications.firebase_cloud_messaging.schema import (
    FCMMessage,
    FCMNotification,
)
from core.notifications.firebase_cloud_messaging.exceptions import (
    FirebaseException,
    FirebaseUnregisteredTokenError,
)


class NotificationService(AbstractService):
    """
    Service class for managing notification creation and delivery using Firebase.
    """

    DEPENDENCIES = {
        "session": SessionDep,
    }

    def __init__(self, session: SessionDep):
        super().__init__(session=session)
        self.session = session
        self.fcm_service = FirebaseCloudMessagingCore()

    async def create_notification(
        self,
        user_id: UUID,
        title: str,
        body: str,
        notification_type: str,
        data: Optional[dict] = None,
        image: Optional[str] = None,
        redirection_target: Optional[str] = None,
    ) -> Notification:
        """
        Creates a new notification record in the database.
        This method remains unchanged.
        """
        new_notification = Notification(
            user_id=user_id,
            title=title,
            body=body,
            data=data,
            notification_type=notification_type,
            redirection_target=redirection_target,
            image=image,
        )
        self.session.add(new_notification)
        await self.session.commit()
        await self.session.refresh(new_notification)
        return new_notification

    async def send_fcm_notification(
        self,
        notification_id: UUID,
        device_id: UUID,
        additional_data: Optional[dict] = None,
    ) -> NotificationChannel:
        """
        Sends a notification via FCM and logs the attempt, handling specific FCM errors.
        """
        # 1. Retrieve the notification and device
        notification = await self.session.get(Notification, notification_id)
        if not notification:
            raise NotFoundException(
                f"Notification with ID {notification_id} not found."
            )

        device = await self.session.get(Device, device_id)
        if not device or not device.device_token:
            raise NotFoundException(
                f"Device with ID {device_id} not found or has no token."
            )

        # 2. Create a NotificationChannel entry to log the send attempt
        channel_log = NotificationChannel(
            notification_id=notification.id,
            device_id=device.id,
            channel_type="FCM_PUSH",
            status=ChannelDeliveryStatus.PENDING.value,
            additional_data=additional_data or {},
        )
        self.session.add(channel_log)
        await self.session.flush()  # Use flush to get the ID without ending the transaction

        # 3. Build the FCM message payload
        fcm_message = FCMMessage(
            token=device.device_token,
            notification=FCMNotification(
                title=notification.title,
                body=notification.body,
                image=notification.image.get("large") if notification.image else None,
            ),
            data=notification.data,
        )

        # 4. Attempt to send and handle responses/exceptions
        try:
            result = self.fcm_service.send_to_token(fcm_message)

            # --- Handle SUCCESS from FCM ---
            channel_log.status = ChannelDeliveryStatus.SENT.value
            channel_log.channel_specific_data = {
                "fcm_message_id": result.fcm_message_id
            }

        except FirebaseUnregisteredTokenError as e:
            # --- Handle UNREGISTERED token specifically ---
            channel_log.status = ChannelDeliveryStatus.FAILED.value
            channel_log.error_message = f"FCM Unregistered Token: {e.fcm_error_code}"
            # Business logic: Mark the device as inactive since the token is bad
            device.status = DeviceStatus.UNINSTALLED.value
            self.session.add(device)

        except FirebaseException as e:
            # --- Handle other known FCM errors ---
            channel_log.status = ChannelDeliveryStatus.FAILED.value
            channel_log.error_message = (
                f"FCM Error: {e.fcm_error_code} - {e.error_message}"
            )

        except Exception as e:
            # --- Handle any other unexpected errors ---
            channel_log.status = ChannelDeliveryStatus.FAILED.value
            channel_log.error_message = f"An unexpected error occurred: {str(e)}"

        await self.session.commit()
        await self.session.refresh(channel_log)
        return channel_log


# Dependency for FastAPI
NotificationServiceDependency = Annotated[
    NotificationService, NotificationService.get_dependency()
]
