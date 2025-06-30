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


class FirebaseClient:
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
        self, token: str, check_revoked: bool = True
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
            user_info = self.get_user_by_uid(decoded_token.get("uid"))

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

    def verify_token_strict(self, token: str) -> DecodedToken:
        """
        Verify token and raise HTTPException if invalid (for use with FastAPI dependencies).

        Args:
            token: Firebase ID token

        Returns:
            DecodedToken model

        Raises:
            HTTPException: If token is invalid
        """
        verification_result = self.verify_token(token)

        if not verification_result.valid:
            raise HTTPException(status_code=401, detail=verification_result.error)

        return verification_result.decoded_token

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

    def list_users(
        self, page_token: Optional[str] = None, max_results: int = 1000
    ) -> UserListResponse:
        """
        List all users.

        Args:
            page_token: Token for pagination
            max_results: Maximum number of results per page

        Returns:
            UserListResponse with list of users
        """
        try:
            page = auth.list_users(page_token=page_token, max_results=max_results)

            users = [self._convert_user_record_to_model(user) for user in page.users]

            return UserListResponse(
                users=users,
                next_page_token=page.next_page_token,
                total_count=len(users),
            )
        except Exception as e:
            logger.error(f"Failed to list users: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to list users")

    def batch_get_users(
        self,
        uids: Optional[List[str]] = None,
        emails: Optional[List[str]] = None,
        phone_numbers: Optional[List[str]] = None,
    ) -> BatchGetUsersResponse:
        """
        Get multiple users by identifiers.

        Args:
            uids: List of user IDs
            emails: List of emails
            phone_numbers: List of phone numbers

        Returns:
            BatchGetUsersResponse with found users and not found identifiers
        """
        try:
            identifiers = []

            if uids:
                identifiers.extend([auth.UidIdentifier(uid) for uid in uids])
            if emails:
                identifiers.extend([auth.EmailIdentifier(email) for email in emails])
            if phone_numbers:
                identifiers.extend(
                    [auth.PhoneIdentifier(phone) for phone in phone_numbers]
                )

            result = auth.get_users(identifiers)

            users = [self._convert_user_record_to_model(user) for user in result.users]
            not_found = [
                (
                    identifier.uid
                    if hasattr(identifier, "uid")
                    else (
                        identifier.email
                        if hasattr(identifier, "email")
                        else identifier.phone_number
                    )
                )
                for identifier in result.not_found
            ]

            return BatchGetUsersResponse(users=users, not_found=not_found)
        except Exception as e:
            logger.error(f"Failed to batch get users: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to batch get users")

    def create_custom_token(
        self, uid: str, additional_claims: Optional[Dict] = None
    ) -> CustomTokenResponse:
        """
        Create a custom token for a user.

        Args:
            uid: User ID
            additional_claims: Additional claims to include in the token

        Returns:
            CustomTokenResponse with token and expiration info
        """
        try:
            custom_token = auth.create_custom_token(uid, additional_claims)
            return CustomTokenResponse(
                custom_token=custom_token.decode("utf-8"),
                expires_in=3600,  # Custom tokens expire in 1 hour
            )
        except Exception as e:
            logger.error(f"Failed to create custom token: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to create custom token")

    def revoke_refresh_tokens(self, uid: str) -> AuthenticationResponse:
        """
        Revoke all refresh tokens for a user.

        Args:
            uid: User ID

        Returns:
            AuthenticationResponse indicating success
        """
        try:
            auth.revoke_refresh_tokens(uid)
            logger.info(f"Refresh tokens revoked for user: {uid}")
            return AuthenticationResponse(
                success=True, message=f"Refresh tokens revoked for user {uid}"
            )
        except Exception as e:
            logger.error(f"Failed to revoke refresh tokens: {str(e)}")
            raise HTTPException(
                status_code=500, detail="Failed to revoke refresh tokens"
            )

    def set_custom_user_claims(
        self, uid: str, custom_claims: Dict
    ) -> AuthenticationResponse:
        """
        Set custom claims for a user.

        Args:
            uid: User ID
            custom_claims: Dictionary of custom claims

        Returns:
            AuthenticationResponse indicating success
        """
        try:
            auth.set_custom_user_claims(uid, custom_claims)
            logger.info(f"Custom claims set for user: {uid}")
            return AuthenticationResponse(
                success=True, message=f"Custom claims set for user {uid}"
            )
        except Exception as e:
            logger.error(f"Failed to set custom claims: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to set custom claims")

    def create_session_cookie(
        self, id_token: str, expires_in: int = 3600
    ) -> SessionCookieResponse:
        """
        Create a session cookie from an ID token.

        Args:
            id_token: Firebase ID token
            expires_in: Session duration in seconds

        Returns:
            SessionCookieResponse with session cookie
        """
        try:
            session_cookie = auth.create_session_cookie(id_token, expires_in=expires_in)
            expires_at = datetime.now(timezone.utc).replace(microsecond=0)
            expires_at = expires_at.replace(second=expires_at.second + expires_in)

            return SessionCookieResponse(
                session_cookie=session_cookie, expires_at=expires_at
            )
        except Exception as e:
            logger.error(f"Failed to create session cookie: {str(e)}")
            raise HTTPException(
                status_code=500, detail="Failed to create session cookie"
            )

    def verify_session_cookie(
        self, session_cookie: str, check_revoked: bool = True
    ) -> VerifySessionCookieResponse:
        """
        Verify a session cookie.

        Args:
            session_cookie: Session cookie to verify
            check_revoked: Whether to check if session has been revoked

        Returns:
            VerifySessionCookieResponse with verification results
        """
        try:
            decoded_claims = auth.verify_session_cookie(
                session_cookie, check_revoked=check_revoked
            )
            decoded_token_model = DecodedToken(**decoded_claims)

            return VerifySessionCookieResponse(
                valid=True,
                decoded_claims=decoded_token_model,
                check_revoked=check_revoked,
            )
        except auth.InvalidSessionCookieError:
            return VerifySessionCookieResponse(
                valid=False, check_revoked=check_revoked, error="Invalid session cookie"
            )
        except auth.ExpiredSessionCookieError:
            return VerifySessionCookieResponse(
                valid=False,
                check_revoked=check_revoked,
                error="Session cookie has expired",
            )
        except auth.RevokedSessionCookieError:
            return VerifySessionCookieResponse(
                valid=False,
                check_revoked=check_revoked,
                error="Session cookie has been revoked",
            )
        except Exception as e:
            logger.error(f"Failed to verify session cookie: {str(e)}")
            return VerifySessionCookieResponse(
                valid=False,
                check_revoked=check_revoked,
                error="Session verification failed",
            )

    def health_check(self) -> HealthCheckResponse:
        """
        Perform health check on Firebase connection.

        Returns:
            HealthCheckResponse with service status
        """
        try:
            # Try to get app info to verify connection
            app_info = self.app
            firebase_connected = app_info is not None
            status = "healthy" if firebase_connected else "unhealthy"

            return HealthCheckResponse(
                status=status,
                firebase_connected=firebase_connected,
                timestamp=datetime.now(timezone.utc),
            )
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            return HealthCheckResponse(
                status="unhealthy",
                firebase_connected=False,
                timestamp=datetime.now(timezone.utc),
            )


class FirebaseAuth(HTTPBearer):
    """
    FastAPI dependency for Firebase authentication.
    """

    def __init__(self, firebase_client: FirebaseClient):
        super(FirebaseAuth, self).__init__()
        self.firebase_client = firebase_client

    async def __call__(self, request: Request) -> DecodedToken:
        """
        Authenticate request and return decoded token.

        Args:
            request: FastAPI request object

        Returns:
            DecodedToken model with user claims
        """
        credentials: HTTPAuthorizationCredentials = await super(
            FirebaseAuth, self
        ).__call__(request)
        return self.firebase_client.verify_token_strict(credentials.credentials)


# Factory function to create Firebase client
def create_firebase_client() -> FirebaseClient:
    """
    Factory function to create Firebase client.
    You can customize this based on your configuration needs.
    """
    return FirebaseClient()
