from fastapi import APIRouter

from apps.api.auth.dependency import FirebaseAuthDependency, UserDependency
from apps.api.auth.schema import UserDetailsResponse
from apps.api.auth.service import firebase_authenticate, firebase_user_data
from core.db.core import SessionDep

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/authenticate", summary="Authenticate user")
async def authenticate_user(
    session: SessionDep, decoded_token: FirebaseAuthDependency
) -> UserDetailsResponse:
    """
    Endpoint to authenticate a user.
    This is a placeholder endpoint and should be implemented with actual authentication logic.
    """
    user = await firebase_authenticate(session=session, uid=decoded_token.uid)
    return user
