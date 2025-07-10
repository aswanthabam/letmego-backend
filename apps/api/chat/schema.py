from datetime import datetime
from pydantic import BaseModel, Field


class ChatMessageMin(BaseModel):
    id: str = Field(..., description="Unique identifier for the chat message")
    content: str = Field(..., description="Content of the chat message")
    user_id: str = Field(..., description="ID of the user who sent the message")
    created_at: datetime = Field(
        ..., description="Timestamp when the message was created"
    )


class ChatMessageAttachmentSchema(BaseModel):
    id: str = Field(...)
    attachment_type: str | None = Field(None)
    file: str = Field(
        ...,
        description="File metadata including content type, filename, and storage details",
    )
    created_at: datetime = Field(
        ..., description="Timestamp when the attachment was created"
    )
    updated_at: datetime = Field(
        ..., description="Timestamp when the attachment was last updated"
    )


class ChatMessageListSchema(BaseModel):
    id: str = Field(...)
    user_id: str = Field(..., description="ID of the user who sent the message")
    content: str = Field(...)
    attachments: list[ChatMessageAttachmentSchema] = Field(
        [], description="List of attachments for the message"
    )
    created_at: datetime = Field(
        ..., description="Timestamp when the message was created"
    )
    updated_at: datetime = Field(
        ..., description="Timestamp when the message was last updated"
    )
    replay_to_message: ChatMessageMin | None = Field(
        None, description="ID of the message this message is replying to"
    )
