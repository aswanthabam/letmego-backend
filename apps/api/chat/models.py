from sqlalchemy import UUID, Column, ForeignKey, String, Text
import sqlalchemy as sa
from sqlalchemy.orm import relationship

from apps.storage import default_storage
from avcfastapi.core.database.sqlalchamey.base import AbstractSQLModel
from avcfastapi.core.database.sqlalchamey.mixins import SoftDeleteMixin, TimestampsMixin
from avcfastapi.core.storage.sqlalchemy.fields.filefield import FileField


class ChatMessage(AbstractSQLModel, SoftDeleteMixin, TimestampsMixin):
    __tablename__ = "chat_messages"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=sa.text("gen_random_uuid()"),
        default=sa.text("gen_random_uuid()"),
    )
    report_id = Column(
        UUID(as_uuid=True), ForeignKey("vehicle_reports.id"), nullable=False
    )
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    content = Column(Text, nullable=False)
    replay_to_message_id = Column(
        UUID(as_uuid=True), ForeignKey("chat_messages.id"), nullable=True
    )

    report = relationship("VehicleReport", back_populates="chat_messages")
    replay_to_message = relationship(
        "ChatMessage",
        remote_side=[id],
        back_populates="replies",
        uselist=False,
        foreign_keys=[replay_to_message_id],
    )
    replies = relationship(
        "ChatMessage",
        back_populates="replay_to_message",
        foreign_keys=[replay_to_message_id],
        cascade="all, delete-orphan",
        uselist=True,
    )
    attachments = relationship(
        "ChatMessageAttachment",
        back_populates="message",
        cascade="all, delete-orphan",
        uselist=True,
    )


class ChatMessageAttachment(AbstractSQLModel, SoftDeleteMixin, TimestampsMixin):
    __tablename__ = "chat_message_attachments"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=sa.text("gen_random_uuid()"),
        default=sa.text("gen_random_uuid()"),
    )
    message_id = Column(
        UUID(as_uuid=True), ForeignKey("chat_messages.id"), nullable=False
    )
    attachment_type = Column(String(50), nullable=False)
    file = Column(
        FileField(
            storage=default_storage,
            upload_to="vehicle/reports/chats/",
        ),
        nullable=True,
    )

    message = relationship(
        "ChatMessage",
        back_populates="attachments",
        foreign_keys=[message_id],
        uselist=False,
    )
