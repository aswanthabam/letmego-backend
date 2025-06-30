from fastapi import Depends

from .client import FirebaseClient, FirebaseAuth, create_firebase_client
from .models import DecodedToken

client = create_firebase_client()
firebase_auth = FirebaseAuth(client)

FirebaseAuthDependency: DecodedToken = Depends(firebase_auth)
