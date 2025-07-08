from enum import Enum
import uuid
from pydantic import Field

from apps.context import get_current_user_id
from core.response.models import CustomBaseModel


class PrivacyPreference(Enum):
    PUBLIC = "public"
    PRIVATE = "private"
    ANONYMOUS = "anonymous"


class UserPrivacyWrapper(CustomBaseModel):
    id: uuid.UUID = Field(...)
    privacy_preference: PrivacyPreference = Field(...)

    def model_post_init(self, context):
        viewer_id = get_current_user_id()
        has_perm = viewer_id == self.id
        if hasattr(self, "fullname"):
            if not has_perm and self.privacy_preference == PrivacyPreference.ANONYMOUS:
                self.fullname = "Anonymous User"
        if hasattr(self, "email"):
            if not has_perm and self.privacy_preference != PrivacyPreference.PUBLIC:
                self.email = "xxxxxxxxxx"
        if hasattr(self, "phone_number"):
            if not has_perm and self.privacy_preference != PrivacyPreference.PUBLIC:
                self.phone_number = "xxxxxxxxxx"
        if hasattr(self, "profile_picture"):
            if not has_perm and self.privacy_preference != PrivacyPreference.PUBLIC:
                self.profile_picture = None
        if hasattr(self, "company_name"):
            if not has_perm and self.privacy_preference != PrivacyPreference.PUBLIC:
                self.company_name = "xxxxxxxxxx"
        if hasattr(self, "uid"):
            if not has_perm:
                self.uid = "xxxxxxxxxx"


class UserDetailsResponse(CustomBaseModel):
    id: uuid.UUID = Field(...)
    uid: str = Field(...)
    email: str = Field(...)
    phone_number: str | None = Field(None)
    fullname: str = Field(...)
    email_verified: bool = Field(...)
    profile_picture: dict | None = Field(None)
    company_name: str | None = Field(None)
    privacy_preference: PrivacyPreference = Field(...)
