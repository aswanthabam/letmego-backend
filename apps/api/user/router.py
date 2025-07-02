from fastapi import APIRouter

from apps.api.auth.dependency import UserDependency
from apps.api.user.schema import UserDetailsResponse
from core.db.core import SessionDep

router = APIRouter(
    prefix="/user",
)


@router.get("/details", summary="Get user details")
async def get_user_details(user: UserDependency) -> UserDetailsResponse:
    """
    Endpoint to get user details by UID.
    This is a placeholder endpoint and should be implemented with actual user retrieval logic.
    """
    return user
