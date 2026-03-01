from fastapi import APIRouter, Form, UploadFile
from fastapi.params import File

from apps.api.auth.dependency import UserDependency
from apps.api.auth.service import AuthServiceDependency
from apps.api.user.models import UserStatus
from apps.api.user.schema import PrivacyPreference, UserDetailsResponse
from apps.api.user.service import UserServiceDependency
from avcfastapi.core.authentication.firebase.dependency import FirebaseAuthDependency
from avcfastapi.core.fastapi.response.models import MessageResponse

router = APIRouter(
    prefix="/user",
    tags=["User"],
)

from apps.api.user.schema import UserStatsResponse

@router.get("/stats", summary="Get user statistics")
async def get_user_stats(
    user: UserDependency,
    user_service: UserServiceDependency,
) -> UserStatsResponse:
    stats = await user_service.get_user_stats(user_id=user.id)
    return UserStatsResponse(**stats)


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


@router.delete("/delete", summary="Delete user account")
async def delete_user(
    user: UserDependency,
    user_service: UserServiceDependency,
) -> MessageResponse:
    """
    Endpoint to delete a user account.
    This endpoint soft deletes the user and returns the user details after deletion
    """
    user = await user_service.delete_user(user_id=user.id)
    return {
        "message": "User account deleted successfully",
    }


@router.post("/logout", summary="Logout user")
async def logout_user(
    user: UserDependency,
    user_service: UserServiceDependency,
    device_id: str | None = Form(None, description="Device ID to logout from"),
) -> MessageResponse:
    """
    Endpoint to logout a user.
    If a device ID is provided, it will delete the device associated with the user.
    """
    await user_service.logout_user(user_id=user.id, device_id=device_id)
    return {"message": "User logged out successfully"}


@router.patch("/status", summary="Change user status")
async def change_user_status(
    user: UserDependency,
    user_service: UserServiceDependency,
    new_status: UserStatus = Form(..., description="New status to set for the user"),
) -> UserDetailsResponse:
    user = await user_service.change_user_status(user_id=user.id, new_status=new_status)
    return user
