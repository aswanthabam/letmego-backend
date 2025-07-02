# models.py
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, EmailStr
from datetime import datetime


class UserMetadata(BaseModel):
    """User metadata information"""

    creation_timestamp: Optional[datetime] = Field(
        None, description="Account creation timestamp"
    )
    last_sign_in_timestamp: Optional[datetime] = Field(
        None, description="Last sign-in timestamp"
    )
    last_refresh_timestamp: Optional[datetime] = Field(
        None, description="Last token refresh timestamp"
    )


class ProviderUserInfo(BaseModel):
    """Provider-specific user information"""

    uid: str = Field(..., description="Provider-specific user ID")
    display_name: Optional[str] = Field(None, description="Display name from provider")
    email: Optional[EmailStr] = Field(None, description="Email from provider")
    photo_url: Optional[str] = Field(None, description="Photo URL from provider")
    provider_id: str = Field(
        ..., description="Provider ID (e.g., 'google.com', 'facebook.com')"
    )


class FirebaseUser(BaseModel):
    """Firebase user information"""

    uid: str = Field(..., description="User's unique ID")
    email: Optional[EmailStr] = Field(None, description="User's email address")
    email_verified: bool = Field(False, description="Whether email is verified")
    display_name: Optional[str] = Field(None, description="User's display name")
    photo_url: Optional[str] = Field(None, description="User's photo URL")
    phone_number: Optional[str] = Field(None, description="User's phone number")
    disabled: bool = Field(False, description="Whether user account is disabled")
    metadata: Optional[UserMetadata] = Field(None, description="User metadata")
    custom_claims: Optional[Dict[str, Any]] = Field(None, description="Custom claims")
    provider_data: Optional[List[ProviderUserInfo]] = Field(
        None, description="Provider-specific data"
    )
    tokens_valid_after_timestamp: Optional[datetime] = Field(
        None, description="Tokens valid after timestamp"
    )


class DecodedToken(BaseModel):
    """Decoded Firebase ID token"""

    iss: str = Field(..., description="Issuer")
    aud: str = Field(..., description="Audience")
    auth_time: int = Field(..., description="Authentication time")
    uid: str = Field(..., description="User ID")
    sub: str = Field(..., description="Subject")
    iat: int = Field(..., description="Issued at")
    exp: int = Field(..., description="Expiration time")
    email: Optional[EmailStr] = Field(None, description="User email")
    email_verified: Optional[bool] = Field(
        None, description="Email verification status"
    )
    phone_number: Optional[str] = Field(None, description="Phone number")
    name: Optional[str] = Field(None, description="Full name")
    picture: Optional[str] = Field(None, description="Profile picture URL")
    firebase: Optional[Dict[str, Any]] = Field(
        None, description="Firebase-specific claims"
    )
    custom_claims: Optional[Dict[str, Any]] = Field(None, description="Custom claims")

    class Config:
        validate_by_name = True


class CustomTokenRequest(BaseModel):
    """Request to create custom token"""

    uid: str = Field(..., description="User ID for token creation")
    additional_claims: Optional[Dict[str, Any]] = Field(
        None, description="Additional claims to include"
    )


class CustomTokenResponse(BaseModel):
    """Response containing custom token"""

    custom_token: str = Field(..., description="Generated custom token")
    expires_in: int = Field(3600, description="Token expiration time in seconds")


class RevokeTokensRequest(BaseModel):
    """Request to revoke refresh tokens"""

    uid: str = Field(..., description="User ID whose tokens to revoke")


class SetCustomClaimsRequest(BaseModel):
    """Request to set custom claims"""

    uid: str = Field(..., description="User ID")
    custom_claims: Dict[str, Any] = Field(..., description="Custom claims to set")


class AuthenticationResponse(BaseModel):
    """Standard authentication response"""

    success: bool = Field(..., description="Whether authentication was successful")
    user: Optional[FirebaseUser] = Field(None, description="User information")
    token_claims: Optional[DecodedToken] = Field(
        None, description="Decoded token claims"
    )
    message: Optional[str] = Field(None, description="Response message")


class ErrorResponse(BaseModel):
    """Error response model"""

    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    code: Optional[int] = Field(None, description="Error code")
    details: Optional[Dict[str, Any]] = Field(
        None, description="Additional error details"
    )


class TokenVerificationResponse(BaseModel):
    """Token verification response"""

    valid: bool = Field(..., description="Whether token is valid")
    decoded_token: Optional[DecodedToken] = Field(
        None, description="Decoded token if valid"
    )
    user: Optional[FirebaseUser] = Field(
        None, description="User information if token is valid"
    )
    error: Optional[str] = Field(None, description="Error message if token is invalid")


class UserListResponse(BaseModel):
    """Response for listing users"""

    users: List[FirebaseUser] = Field(..., description="List of users")
    next_page_token: Optional[str] = Field(None, description="Token for next page")
    total_count: Optional[int] = Field(None, description="Total number of users")


class CreateUserRequest(BaseModel):
    """Request to create a new user"""

    email: Optional[EmailStr] = Field(None, description="User email")
    password: Optional[str] = Field(None, description="User password", min_length=6)
    display_name: Optional[str] = Field(None, description="Display name")
    photo_url: Optional[str] = Field(None, description="Photo URL")
    phone_number: Optional[str] = Field(None, description="Phone number")
    email_verified: bool = Field(False, description="Email verification status")
    disabled: bool = Field(False, description="Whether user should be disabled")


class UpdateUserRequest(BaseModel):
    """Request to update user information"""

    uid: str = Field(..., description="User ID to update")
    email: Optional[EmailStr] = Field(None, description="New email")
    password: Optional[str] = Field(None, description="New password", min_length=6)
    display_name: Optional[str] = Field(None, description="New display name")
    photo_url: Optional[str] = Field(None, description="New photo URL")
    phone_number: Optional[str] = Field(None, description="New phone number")
    email_verified: Optional[bool] = Field(
        None, description="Email verification status"
    )
    disabled: Optional[bool] = Field(
        None, description="Whether user should be disabled"
    )


class BatchGetUsersRequest(BaseModel):
    """Request to get multiple users"""

    uids: Optional[List[str]] = Field(None, description="List of user IDs")
    emails: Optional[List[EmailStr]] = Field(None, description="List of emails")
    phone_numbers: Optional[List[str]] = Field(
        None, description="List of phone numbers"
    )


class BatchGetUsersResponse(BaseModel):
    """Response for batch get users"""

    users: List[FirebaseUser] = Field(..., description="Found users")
    not_found: List[str] = Field(..., description="Identifiers that were not found")


class SessionCookieRequest(BaseModel):
    """Request to create session cookie"""

    id_token: str = Field(..., description="Firebase ID token")
    expires_in: int = Field(3600, description="Session duration in seconds")


class SessionCookieResponse(BaseModel):
    """Response containing session cookie"""

    session_cookie: str = Field(..., description="Generated session cookie")
    expires_at: datetime = Field(..., description="Cookie expiration time")


class VerifySessionCookieResponse(BaseModel):
    """Response for session cookie verification"""

    valid: bool = Field(..., description="Whether session cookie is valid")
    decoded_claims: Optional[DecodedToken] = Field(
        None, description="Decoded claims if valid"
    )
    check_revoked: bool = Field(True, description="Whether revocation was checked")
    error: Optional[str] = Field(None, description="Error message if invalid")


class FirebaseConfig(BaseModel):
    """Firebase configuration"""

    project_id: Optional[str] = Field(None, description="Firebase project ID")
    service_account_path: Optional[str] = Field(
        None, description="Path to service account file"
    )
    service_account_key: Optional[str] = Field(
        None, description="Service account JSON string"
    )
    database_url: Optional[str] = Field(None, description="Firebase database URL")
    storage_bucket: Optional[str] = Field(None, description="Firebase storage bucket")


class HealthCheckResponse(BaseModel):
    """Health check response"""

    status: str = Field(..., description="Service status")
    firebase_connected: bool = Field(..., description="Firebase connection status")
    timestamp: datetime = Field(..., description="Check timestamp")
    version: Optional[str] = Field(None, description="Service version")
