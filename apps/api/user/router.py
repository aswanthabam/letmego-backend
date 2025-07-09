from fastapi import APIRouter, Form, UploadFile
from fastapi.params import File

from apps.api.auth.dependency import UserDependency
from apps.api.auth.service import AuthServiceDependency
from apps.api.user.schema import PrivacyPreference, UserDetailsResponse
from apps.api.user.service import UserServiceDependency
from core.authentication.firebase.dependency import FirebaseAuthDependency

router = APIRouter(
    prefix="/user",
    tags=["User"],
)


@router.put("/update", summary="Update user details")
async def update_user_details(
    user: UserDependency,
    user_service: UserServiceDependency,
    fullname: str = Form(..., description="Full name of the user"),
    email: str = Form(..., description="Email address of the user"),
    phone_number: str | None = Form(None, description="Phone number of the user"),
    company_name: str | None = Form(None, description="Company name of the user"),
) -> UserDetailsResponse:
    user = await user_service.update_user_details(
        user_id=user.id,
        fullname=fullname,
        email=email,
        phone_number=phone_number,
        company_name=company_name,
    )
    return user


@router.patch("/profile-picture", summary="Update user profile picture")
async def update_user_profile_picture(
    user: UserDependency,
    user_service: UserServiceDependency,
    profile_picture: UploadFile = File(...),
) -> UserDetailsResponse:
    user = await user_service.update_user_profile_picture(
        user_id=user.id, profile_picture=profile_picture
    )
    return user


@router.patch("/privacy-preference", summary="Update user privacy settings")
async def update_privacy_preference(
    user: UserDependency,
    user_service: UserServiceDependency,
    privacy_preference: PrivacyPreference = Form(
        ..., description="Privacy preference to set for the user"
    ),
) -> UserDetailsResponse:
    user = await user_service.set_user_privacy_preferences(
        user_id=user.id, privacy_preference=privacy_preference
    )
    return user


@router.post("/authenticate", summary="Authenticate user")
async def authenticate_user_endpoint(
    user_service: UserServiceDependency,
    auth_service: AuthServiceDependency,
    decoded_token: FirebaseAuthDependency,
) -> UserDetailsResponse:
    """
    Endpoint to authenticate a user using Firebase.
    This endpoint retrieves user details based on the Firebase UID from the decoded token.
    If the user does not exist, it attempts to authenticate the user via Firebase.
    """
    user = await user_service.get_user_by_uid(decoded_token.uid, raise_exception=False)
    if not user:
        user = await auth_service.firebase_authenticate(uid=decoded_token.uid)
    return user
