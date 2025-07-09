from fastapi import APIRouter

from apps.api.auth.dependency import FirebaseAuthDependency
from apps.api.auth.schema import UserDetailsResponse
from apps.api.auth.service import AuthServiceDependency

router = APIRouter(prefix="/auth", tags=["Authentication"])


# @router.post("/firebase/register", summary="Register a new user using firebase")
# async def authenticate_user_endpoint(
#     auth_service: AuthServiceDependency, decoded_token: FirebaseAuthDependency
# ) -> UserDetailsResponse:
#     """
#     Endpoint to authenticate a user.
#     This is a placeholder endpoint and should be implemented with actual authentication logic.
#     """
#     user = await auth_service.firebase_authenticate(uid=decoded_token.uid)
#     return user
