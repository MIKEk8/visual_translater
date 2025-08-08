"""Auth Error Handler - Authentication Error Management"""

from typing import Any, Dict, List


class AuthErrorHandler:
    """Handle authentication errors - complexity ≤ 3"""

    def __init__(self):
        self.failed_attempts = {}

    def handle_auth_error(self, error: Exception, user_id: str = None) -> Dict[str, Any]:
        """Handle authentication error - complexity 3"""
        error_info = {"type": "auth_error", "message": str(error), "user_id": user_id}

        if user_id:  # +1
            self.failed_attempts[user_id] = self.failed_attempts.get(user_id, 0) + 1  # +1

            if self.failed_attempts[user_id] >= 3:  # +1
                error_info["locked"] = True

        return error_info
