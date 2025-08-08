"""Session Manager - User Session Management"""

from typing import Any, Dict, Optional


class SessionManager:
    """Manage user sessions - complexity ≤ 3"""

    def __init__(self):
        self.active_sessions = {}

    def create_session(self, user_id: str, token: str) -> Dict[str, Any]:
        """Create user session - complexity 3"""
        if not user_id or not token:  # +1
            return {"success": False, "error": "Missing user ID or token"}

        session_id = f"session_{user_id}_{len(self.active_sessions)}"

        session_data = {
            "session_id": session_id,
            "user_id": user_id,
            "token": token,
            "active": True,
        }

        self.active_sessions[session_id] = session_data  # +1

        return {"success": True, "session_data": session_data}  # +1
