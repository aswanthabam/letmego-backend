from typing import List, Optional
from uuid import UUID
from fastapi import UploadFile
from sqlalchemy import exists, or_, select
from typing_extensions import Annotated
from sqlalchemy.orm import selectinload, joinedload

from apps.api.chat.models import ChatMessage, ChatMessageAttachment
from apps.api.vehicle.models import Vehicle
from apps.api.vehicle.report.models import VehicleReport
from core.architecture.service import AbstractService
from core.db.core import SessionDep
from core.exceptions.authentication import ForbiddenException
from core.storage.sqlalchemy.inputs.file import InputFile


class ChatService(AbstractService):
    DEPENDENCIES = {"session": SessionDep}

    def __init__(self, session: SessionDep, **kwargs):
        super().__init__(session=session, **kwargs)
        self.session = session

    async def check_user_has_permission(self, user_id: UUID, report_id: UUID) -> bool:
        """
        Check if a user has permission to access a report.
        :param user_id: The ID of the user.
        :param report_id: The ID of the report.
        :return: True if the user has permission, False otherwise.
        """
        subq = (
            select(VehicleReport.id)
            .join(Vehicle, Vehicle.id == VehicleReport.vehicle_id)
            .where(VehicleReport.id == report_id)
            .where(or_(VehicleReport.user_id == user_id, Vehicle.user_id == user_id))
        )
        result = await self.session.scalar(subq)
        return result is not None

    async def add_message(
        self,
        user_id: UUID,
        report_id: UUID,
        content: str,
        attachments: Optional[List[UploadFile]] = None,
        replay_to_message_id: Optional[UUID] = None,
    ) -> UUID:
        """
        Send a chat message with optional attachments and reply to a specific message.
        :param report_id: The ID of the report to which the message belongs.
        :param content: The content of the message.
        :param attachments: Optional list of file attachments.
        :param replay_to_message_id: Optional ID of the message to which this message is a reply.
        :return: The ID of the sent message.
        """
        message = ChatMessage(
            report_id=report_id,
            content=content,
            replay_to_message_id=replay_to_message_id,
            user_id=user_id,
        )
        self.session.add(message)
        await self.session.flush()

        if attachments:
            for attachment in attachments:
                message_attachment = ChatMessageAttachment(
                    message_id=message.id,
                    attachment_type=attachment.content_type,
                    file=InputFile(
                        content=await attachment.read(),
                        filename=attachment.filename,
                        prefix_date=True,
                        unique_filename=True,
                    ),
                )
                self.session.add(message_attachment)
                await self.session.flush()
        await self.session.commit()
        return message

    async def get_messages_for_report(
        self, report_id: UUID, limit: int = 100, offset: int = 0
    ) -> List[ChatMessage]:
        """
        Retrieve chat messages for a specific report.
        :param report_id: The ID of the report for which to retrieve messages.
        :param limit: The maximum number of messages to retrieve.
        :param offset: The number of messages to skip before starting to collect the result set.
        :return: A list of chat messages.
        """
        query = (
            select(ChatMessage)
            .options(joinedload(ChatMessage.replay_to_message))
            .options(selectinload(ChatMessage.attachments))
            .where(ChatMessage.report_id == report_id)
            .order_by(ChatMessage.created_at.desc())
        )

        if limit is not None:
            query = query.limit(limit)
        if offset is not None:
            query = query.offset(offset)
        result = (await self.session.scalars(query)).all()
        return result

    async def delete_message(self, user_id: UUID, message_id: UUID) -> None:
        """
        Delete a chat message by its ID.
        :param message_id: The ID of the message to delete.
        """
        stmt = select(ChatMessage).where(
            ChatMessage.id == message_id, ChatMessage.user_id == user_id
        )
        message = await self.session.scalar(stmt)
        if message:
            if message.user_id != user_id:
                raise ForbiddenException(
                    "You do not have permission to delete this message."
                )
            message.soft_delete()
            await self.session.commit()
            return True
        raise ForbiddenException(
            "Message not found or you do not have permission to delete it."
        )


ChatServiceDependency = Annotated[ChatService, ChatService.get_dependency()]
