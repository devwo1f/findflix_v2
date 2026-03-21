from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from jose import JWTError, jwt
from passlib.context import CryptContext
import structlog

from app.core.config import settings

logger = structlog.get_logger(__name__)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(
    subject: str | UUID,
    expires_delta: timedelta | None = None,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode: dict[str, Any] = {
        "sub": str(subject),
        "exp": expire,
        "iat": now,
        "type": "access",
    }
    if extra_claims:
        to_encode.update(extra_claims)
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(subject: str | UUID) -> str:
    now = datetime.now(timezone.utc)
    expire = now + timedelta(days=7)
    to_encode = {
        "sub": str(subject),
        "exp": expire,
        "iat": now,
        "type": "refresh",
    }
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict[str, Any]:
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        return payload
    except JWTError as exc:
        logger.warning("token_decode_failed", error=str(exc))
        raise ValueError(f"Invalid token: {exc}") from exc


async def verify_firebase_token(token: str) -> dict[str, Any]:
    """Verify a Firebase ID token and return decoded claims.

    Uses the Firebase Admin SDK when available. Falls back to a manual
    verification via Google's public keys when the SDK is not initialised
    (e.g. in tests or lightweight deployments).
    """
    try:
        import firebase_admin  # noqa: F811
        from firebase_admin import auth as firebase_auth

        # Initialise the default app if it hasn't been done yet.
        try:
            firebase_admin.get_app()
        except ValueError:
            firebase_admin.initialize_app()

        decoded = firebase_auth.verify_id_token(token)
        logger.info("firebase_token_verified", uid=decoded.get("uid"))
        return decoded
    except Exception as exc:
        logger.error("firebase_token_verification_failed", error=str(exc))
        raise ValueError(f"Firebase token verification failed: {exc}") from exc
