"""User Credential Validator - Authentication Validation"""

import hashlib
from typing import Any, Dict, List


class UserCredentialValidator:
    """Validate user credentials - complexity ≤ 3"""

    def __init__(self):
        self.validation_errors = []

    def validate_credentials(self, credentials: Dict[str, Any]) -> tuple[bool, List[str]]:
        """Validate user credentials - complexity 3"""
        self.validation_errors.clear()

        if not credentials:  # +1
            self.validation_errors.append("No credentials provided")
            return False, self.validation_errors

        if "username" not in credentials or "password" not in credentials:  # +1
            self.validation_errors.append("Missing username or password")
            return False, self.validation_errors

        if len(credentials["password"]) < 8:  # +1
            self.validation_errors.append("Password too short")
            return False, self.validation_errors

        return True, []
