"""Password service for The Robot Overlord API."""

import bcrypt


class PasswordService:
    """Service for password hashing and verification operations."""

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password using bcrypt.

        Args:
            password: Plain text password to hash

        Returns:
            Hashed password string
        """
        # Generate salt and hash password
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
        return hashed.decode("utf-8")

    @staticmethod
    def verify_password(password: str, hashed_password: str) -> bool:
        """Verify a password against its hash.

        Args:
            password: Plain text password to verify
            hashed_password: Hashed password to check against

        Returns:
            True if password matches, False otherwise
        """
        return bcrypt.checkpw(password.encode("utf-8"), hashed_password.encode("utf-8"))


def get_password_service() -> PasswordService:
    """Get password service instance.

    Returns:
        PasswordService instance
    """
    return PasswordService()
