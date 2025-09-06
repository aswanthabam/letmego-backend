from uuid import UUID
from fastapi import APIRouter, Form, Request, UploadFile
from fastapi.params import File

from apps.api.auth.dependency import UserDependency
from apps.api.chat.schema import ChatMessageListSchema
from apps.api.chat.service import ChatServiceDependency
from avcfastapi.core.exception.request import InvalidRequestException
from avcfastapi.core.fastapi.response.models import MessageResponse
from avcfastapi.core.fastapi.response.pagination import (
    PaginatedResponse,
    PaginationParams,
    paginated_response,
)

router = APIRouter(prefix="/chat", tags=["Chat"])


@router.post("/message/send/{report_id}", summary="Send a chat message")
async def send_message(
    user: UserDependency,
    chat_service: ChatServiceDependency,
    report_id: str,
    content: str = Form(..., description="Content of the message"),
    replay_to_message_id: UUID = Form(
        None, description="ID of the message to reply to"
    ),
    attachments: list[UploadFile] = File(None, description="List of file attachments"),
) -> MessageResponse:
    if not await chat_service.check_user_has_permission(user.id, report_id):
        raise InvalidRequestException(
            "You do not have permission to send messages for this report."
        )
    await chat_service.add_message(
        user_id=user.id,
        report_id=report_id,
        content=content,
        attachments=attachments,
        replay_to_message_id=replay_to_message_id,
    )
    return {"message": "Message sent successfully"}


@router.get("/message/list/{report_id}", summary="List chat messages for a report")
async def list_messages(
    request: Request,
    user: UserDependency,
    chat_service: ChatServiceDependency,
    report_id: str,
    pagination: PaginationParams,
) -> PaginatedResponse[ChatMessageListSchema]:
    if not await chat_service.check_user_has_permission(user.id, report_id):
        raise InvalidRequestException(
            "You do not have permission to view messages for this report."
        )
    messages = await chat_service.get_messages_for_report(
        report_id=report_id,
        offset=pagination.offset,
        limit=pagination.limit,
    )
    return paginated_response(
        result=messages,
        request=request,
        schema=ChatMessageListSchema,
    )


@router.delete("/message/delete/{message_id}", summary="Delete a chat message")
async def delete_message(
    user: UserDependency,
    chat_service: ChatServiceDependency,
    message_id: str,
) -> MessageResponse:
    await chat_service.delete_message(message_id=message_id, user_id=user.id)
    return {"message": "Message deleted successfully"}
