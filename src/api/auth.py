"""
Authentication module for Screen Translator API.

This module provides basic authentication functionality for the API endpoints.
"""

from typing import Dict, Optional

from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader
from starlette.status import HTTP_401_UNAUTHORIZED, HTTP_403_FORBIDDEN

# API key header configuration
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

# Simple in-memory API key storage (in production, use a proper database)
VALID_API_KEYS: Dict[str, Dict[str, str]] = {
    "demo_key_123": {"name": "Demo User", "role": "user"},
    "admin_key_456": {"name": "Admin User", "role": "admin"},
}


def get_current_user(api_key: Optional[str] = Security(api_key_header)) -> Dict[str, str]:
    """
    Validate API key and return current user info.

    Args:
        api_key: API key from request header

    Returns:
        User information dictionary

    Raises:
        HTTPException: If API key is invalid or missing
    """
    if not api_key:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail="API key required",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    user_info = VALID_API_KEYS.get(api_key)
    if not user_info:
        raise HTTPException(
            status_code=HTTP_403_FORBIDDEN,
            detail="Invalid API key",
        )

    return user_info


def require_admin(current_user: Dict[str, str] = Security(get_current_user)) -> Dict[str, str]:
    """
    Require admin role for endpoint access.

    Args:
        current_user: Current authenticated user

    Returns:
        User information if admin

    Raises:
        HTTPException: If user is not admin
    """
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user


def create_api_key(user_name: str, role: str = "user") -> str:
    """
    Create a new API key for a user.

    Args:
        user_name: Name of the user
        role: User role (user or admin)

    Returns:
        Generated API key
    """
    import secrets

    api_key = f"st_{secrets.token_urlsafe(32)}"
    VALID_API_KEYS[api_key] = {"name": user_name, "role": role}
    return api_key


def revoke_api_key(api_key: str) -> bool:
    """
    Revoke an API key.

    Args:
        api_key: API key to revoke

    Returns:
        True if revoked, False if not found
    """
    if api_key in VALID_API_KEYS:
        del VALID_API_KEYS[api_key]
        return True
    return False
