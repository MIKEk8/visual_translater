"""Refactored Authenticate User - Main Coordinator"""

from typing import Any, Dict, Optional

from .auth_error_handler import AuthErrorHandler
from .auth_token_manager import AuthTokenManager
from .session_manager import SessionManager
from .user_credential_validator import UserCredentialValidator


class RefactoredAuthenticateUser:
    """Main coordinator for user authentication - complexity ≤ 5"""

    def __init__(self):
        self.validator = UserCredentialValidator()
        self.token_manager = AuthTokenManager()
        self.session_manager = SessionManager()
        self.error_handler = AuthErrorHandler()

    def authenticate_user(
        self, credentials: Dict[str, Any], options: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Authenticate user - complexity 5"""
        options = options or {}
        user_id = credentials.get("username", "unknown")

        try:
            # Step 1: Validate credentials
            is_valid, errors = self.validator.validate_credentials(credentials)
            if not is_valid:  # +1
                return {"success": False, "stage": "validation", "errors": errors}

            # Step 2: Generate token
            permissions = options.get("permissions", ["read"])
            token_result = self.token_manager.generate_token(user_id, permissions)

            if not token_result["success"]:  # +1
                return {
                    "success": False,
                    "stage": "token_generation",
                    "error": token_result["error"],
                }

            # Step 3: Create session
            token = token_result["token_data"]["token"]
            session_result = self.session_manager.create_session(user_id, token)

            if not session_result["success"]:  # +1
                return {
                    "success": False,
                    "stage": "session_creation",
                    "error": session_result["error"],
                }

            # Step 4: Return authentication result
            if options.get("include_permissions"):  # +1
                return {
                    "success": True,
                    "user_id": user_id,
                    "token": token,
                    "session_id": session_result["session_data"]["session_id"],
                    "permissions": permissions,
                    "stage": "completed",
                }
            else:
                return {"success": True, "user_id": user_id, "token": token, "stage": "completed"}

        except Exception as e:  # +1
            error_info = self.error_handler.handle_auth_error(e, user_id)
            return {"success": False, "error": str(e), "stage": "error"}
