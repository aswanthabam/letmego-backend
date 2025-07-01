from fastapi import APIRouter
from core.authentication.firebase.client import create_firebase_client

router = APIRouter(prefix="/auth", tags=["auth"])

firebase_client = create_firebase_client()


@router.get("/authenticate", summary="Authenticate user")
async def authenticate_user(token: str):
    """
    Endpoint to authenticate a user.
    This is a placeholder endpoint and should be implemented with actual authentication logic.
    """
    return firebase_client.verify_token(token)
