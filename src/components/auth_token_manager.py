"""Auth Token Manager - Authentication Token Handling"""

import time
from typing import Any, Dict, Optional


class AuthTokenManager:
    """Manage authentication tokens - complexity ≤ 4"""

    def __init__(self):
        self.active_tokens = {}
        self.token_expiry = 3600  # 1 hour

    def generate_token(self, user_id: str, permissions: List[str] = None) -> Dict[str, Any]:
        """Generate authentication token - complexity 4"""
        if not user_id:  # +1
            return {"success": False, "error": "No user ID provided"}

        try:
            current_time = time.time()
            token = f"token_{user_id}_{int(current_time)}"

            token_data = {
                "token": token,
                "user_id": user_id,
                "permissions": permissions or [],  # +1
                "issued_at": current_time,
                "expires_at": current_time + self.token_expiry,
            }

            self.active_tokens[token] = token_data  # +1

            return {"success": True, "token_data": token_data}  # +1

        except Exception as e:
            return {"success": False, "error": str(e)}
