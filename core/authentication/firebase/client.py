# firebase_client.py
import os
import json
from typing import Optional, Dict, Any, List
import firebase_admin
from firebase_admin import credentials, auth
from fastapi import HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import logging
from datetime import datetime, timezone

# Import Pydantic models
from .models import (
    FirebaseUser,
    DecodedToken,
    CustomTokenResponse,
    TokenVerificationResponse,
    AuthenticationResponse,
    ErrorResponse,
    UserListResponse,
    BatchGetUsersResponse,
    SessionCookieResponse,
    VerifySessionCookieResponse,
    HealthCheckResponse,
    UserMetadata,
    ProviderUserInfo,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FirebaseAuthClient:
    def __init__(
        self,
        service_account_path: Optional[str] = None,
        service_account_dict: Optional[Dict] = None,
    ):
        """
        Initialize Firebase client with service account credentials.

        Args:
            service_account_path: Path to service account JSON file
            service_account_dict: Service account credentials as dictionary
        """
        self.app = None
        self._initialize_firebase(service_account_path, service_account_dict)

    def _initialize_firebase(
        self,
        service_account_path: Optional[str] = None,
        service_account_dict: Optional[Dict] = None,
    ):
        """
        Initialize Firebase Admin SDK.
        """
        try:
            # Check if Firebase is already initialized
            if firebase_admin._apps:
                logger.info("Firebase already initialized")
                self.app = firebase_admin.get_app()
                return

            # Initialize with service account file
            if service_account_path and os.path.exists(service_account_path):
                cred = credentials.Certificate(service_account_path)
                logger.info(
                    f"Initializing Firebase with service account file: {service_account_path}"
                )

            # Initialize with service account dictionary
            elif service_account_dict:
                cred = credentials.Certificate(service_account_dict)
                logger.info("Initializing Firebase with service account dictionary")

            # Try to initialize with environment variable
            elif os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
                cred = credentials.ApplicationDefault()
                logger.info(
                    "Initializing Firebase with application default credentials"
                )

            # Try to initialize with service account from environment variable
            elif os.getenv("FIREBASE_SERVICE_ACCOUNT_KEY"):
                service_account_info = json.loads(
                    os.getenv("FIREBASE_SERVICE_ACCOUNT_KEY")
                )
                cred = credentials.Certificate(service_account_info)
                logger.info(
                    "Initializing Firebase with service account from environment variable"
                )

            else:
                raise ValueError("No valid Firebase credentials provided")

            self.app = firebase_admin.initialize_app(cred)
            logger.info("Firebase initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize Firebase: {str(e)}")
            raise HTTPException(
                status_code=500, detail=f"Firebase initialization failed: {str(e)}"
            )

    def verify_token(
        self, token: str, check_revoked: bool = True, fetch_user_info: bool = True
    ) -> TokenVerificationResponse:
        """
        Verify Firebase ID token and return verification response.

        Args:
            token: Firebase ID token
            check_revoked: Whether to check if token has been revoked

        Returns:
            TokenVerificationResponse with verification results
        """
        try:
            # Remove 'Bearer ' prefix if present
            if token.startswith("Bearer "):
                token = token[7:]

            # Verify the token
            decoded_token = auth.verify_id_token(token, check_revoked=check_revoked)

            # Convert to Pydantic model
            decoded_token_model = DecodedToken(**decoded_token)

            # Get user information
            if fetch_user_info:
                user_info = self.get_user_by_uid(decoded_token.get("uid"))
            else:
                user_info = None

            logger.info(f"Token verified for user: {decoded_token.get('uid')}")

            return TokenVerificationResponse(
                valid=True, decoded_token=decoded_token_model, user=user_info
            )

        except auth.InvalidIdTokenError:
            logger.error("Invalid ID token")
            return TokenVerificationResponse(
                valid=False, error="Invalid authentication token"
            )
        except auth.ExpiredIdTokenError:
            logger.error("Expired ID token")
            return TokenVerificationResponse(
                valid=False, error="Authentication token has expired"
            )
        except auth.RevokedIdTokenError:
            logger.error("Revoked ID token")
            return TokenVerificationResponse(
                valid=False, error="Authentication token has been revoked"
            )
        except Exception as e:
            logger.error(f"Token verification failed: {str(e)}")
            return TokenVerificationResponse(valid=False, error="Authentication failed")

    def _convert_user_record_to_model(self, user_record) -> FirebaseUser:
        """
        Convert Firebase UserRecord to Pydantic model.

        Args:
            user_record: Firebase UserRecord object

        Returns:
            FirebaseUser model
        """
        # Convert metadata
        metadata = None
        if user_record.user_metadata:
            metadata = UserMetadata(
                creation_timestamp=(
                    datetime.fromtimestamp(
                        user_record.user_metadata.creation_timestamp / 1000,
                        tz=timezone.utc,
                    )
                    if user_record.user_metadata.creation_timestamp
                    else None
                ),
                last_sign_in_timestamp=(
                    datetime.fromtimestamp(
                        user_record.user_metadata.last_sign_in_timestamp / 1000,
                        tz=timezone.utc,
                    )
                    if user_record.user_metadata.last_sign_in_timestamp
                    else None
                ),
                last_refresh_timestamp=(
                    datetime.fromtimestamp(
                        user_record.user_metadata.last_refresh_timestamp / 1000,
                        tz=timezone.utc,
                    )
                    if user_record.user_metadata.last_refresh_timestamp
                    else None
                ),
            )

        # Convert provider data
        provider_data = []
        if user_record.provider_data:
            for provider in user_record.provider_data:
                provider_data.append(
                    ProviderUserInfo(
                        uid=provider.uid,
                        display_name=provider.display_name,
                        email=provider.email,
                        photo_url=provider.photo_url,
                        provider_id=provider.provider_id,
                    )
                )

        return FirebaseUser(
            uid=user_record.uid,
            email=user_record.email,
            email_verified=user_record.email_verified,
            display_name=user_record.display_name,
            photo_url=user_record.photo_url,
            phone_number=user_record.phone_number,
            disabled=user_record.disabled,
            metadata=metadata,
            custom_claims=user_record.custom_claims,
            provider_data=provider_data if provider_data else None,
            tokens_valid_after_timestamp=(
                datetime.fromtimestamp(
                    user_record.tokens_valid_after_timestamp / 1000, tz=timezone.utc
                )
                if user_record.tokens_valid_after_timestamp
                else None
            ),
        )

    def get_user_by_uid(self, uid: str) -> FirebaseUser:
        """
        Get user information by UID.

        Args:
            uid: User ID

        Returns:
            FirebaseUser model

        Raises:
            HTTPException: If user not found or error occurs
        """
        try:
            user_record = auth.get_user(uid)
            return self._convert_user_record_to_model(user_record)
        except auth.UserNotFoundError:
            logger.error(f"User not found: {uid}")
            raise HTTPException(status_code=404, detail="User not found")
        except Exception as e:
            logger.error(f"Failed to get user: {str(e)}")
            raise HTTPException(
                status_code=500, detail="Failed to retrieve user information"
            )

    def get_user_by_email(self, email: str) -> FirebaseUser:
        """
        Get user information by email.

        Args:
            email: User email

        Returns:
            FirebaseUser model

        Raises:
            HTTPException: If user not found or error occurs
        """
        try:
            user_record = auth.get_user_by_email(email)
            return self._convert_user_record_to_model(user_record)
        except auth.UserNotFoundError:
            logger.error(f"User not found: {email}")
            raise HTTPException(status_code=404, detail="User not found")
        except Exception as e:
            logger.error(f"Failed to get user: {str(e)}")
            raise HTTPException(
                status_code=500, detail="Failed to retrieve user information"
            )

    def get_user_by_phone_number(self, phone_number: str) -> FirebaseUser:
        """
        Get user information by phone number.

        Args:
            phone_number: User phone number

        Returns:
            FirebaseUser model

        Raises:
            HTTPException: If user not found or error occurs
        """
        try:
            user_record = auth.get_user_by_phone_number(phone_number)
            return self._convert_user_record_to_model(user_record)
        except auth.UserNotFoundError:
            logger.error(f"User not found: {phone_number}")
            raise HTTPException(status_code=404, detail="User not found")
        except Exception as e:
            logger.error(f"Failed to get user: {str(e)}")
            raise HTTPException(
                status_code=500, detail="Failed to retrieve user information"
            )


# Factory function to create Firebase client
def create_firebase_client() -> FirebaseAuthClient:
    """
    Factory function to create Firebase client.
    You can customize this based on your configuration needs.
    """
    return FirebaseAuthClient()
