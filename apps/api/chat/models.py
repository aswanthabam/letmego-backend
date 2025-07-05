from sqlalchemy import UUID, Column, ForeignKey, String, Text
import sqlalchemy as sa

from core.db.base import AbstractSQLModel
from core.db.mixins import SoftDeleteMixin, TimestampsMixin
from core.storage.sqlalchemy.fields.filefield import FileField
from apps.storage import default_storage


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
