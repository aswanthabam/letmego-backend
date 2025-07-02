from typing import Annotated
from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from core.authentication.firebase.client import create_firebase_client
from core.authentication.firebase.models import DecodedToken
from core.exceptions.authentication import UnauthorizedException


firebase_client = create_firebase_client()

http_bearer = HTTPBearer(auto_error=False)


async def firebase_authenticate(
    token: Annotated[HTTPAuthorizationCredentials, Depends(http_bearer)],
):
    if not token or not token.credentials:
        raise UnauthorizedException(
            "Missing or invalid authentication token.",
        )
    response = firebase_client.verify_token(token.credentials, fetch_user_info=False)
    if not response or not response.decoded_token:
        raise UnauthorizedException(
            "Invalid authentication token.",
        )
    return response.decoded_token


FirebaseAuthDependency = Annotated[DecodedToken, Depends(firebase_authenticate)]
