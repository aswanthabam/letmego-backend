import uuid
from pydantic import Field

from core.response.models import CustomBaseModel


class UserDetailsResponse(CustomBaseModel):
    id: uuid.UUID = Field(...)
    uid: str = Field(...)
    email: str = Field(...)
    phone_number: str | None = Field(None)
    fullname: str = Field(...)
    email_verified: bool = Field(...)
    profile_picture: dict | None = Field(None)
