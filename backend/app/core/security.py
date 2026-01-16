"""
Security utilities: encryption, JWT tokens, password hashing.
"""
import base64
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from cryptography.fernet import Fernet
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def derive_fernet_key(secret: str) -> bytes:
    """Derive a Fernet-compatible key from the encryption key."""
    key = hashlib.sha256(secret.encode()).digest()
    return base64.urlsafe_b64encode(key)


# Token encryption
_fernet = Fernet(derive_fernet_key(settings.encryption_key))


def encrypt_token(token: str) -> str:
    """Encrypt a token for secure storage."""
    return _fernet.encrypt(token.encode()).decode()


def decrypt_token(encrypted_token: str) -> str:
    """Decrypt a stored token."""
    try:
        return _fernet.decrypt(encrypted_token.encode()).decode()
    except Exception as e:
        logger.error("Failed to decrypt token", error=str(e))
        raise ValueError("Invalid encrypted token")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def hash_password(password: str) -> str:
    """Hash a password for storage."""
    return pwd_context.hash(password)


def create_access_token(
    data: dict[str, Any],
    expires_delta: timedelta | None = None,
) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(hours=settings.jwt_expiration_hours)
    )
    to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc)})
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, Any] | None:
    """Decode and validate a JWT access token."""
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        return payload
    except JWTError as e:
        logger.warning("Invalid JWT token", error=str(e))
        return None


def generate_api_key() -> str:
    """Generate a secure API key."""
    return secrets.token_urlsafe(32)


def verify_shopify_hmac(hmac_header: str, body: bytes) -> bool:
    """Verify Shopify webhook HMAC signature."""
    import hmac as hmac_lib

    if not settings.shopify_api_secret:
        logger.warning("Shopify API secret not configured, HMAC verification skipped")
        return False

    computed_hmac = base64.b64encode(
        hmac_lib.new(
            settings.shopify_api_secret.encode(),
            body,
            hashlib.sha256,
        ).digest()
    ).decode()
    return hmac_lib.compare_digest(computed_hmac, hmac_header)
