"""JWT signing/verification and the FastAPI auth dependency (SPEC.md §6).

Tokens are HS256-signed with ``JWT_SECRET``. The frontend (Phase 5) will
obtain signed tokens through NextAuth Google OAuth; this dependency only
verifies signature/claims and resolves the user from the database.
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import User

ALGORITHM = "HS256"
ISSUER = "ci-backend"


def _require_jwt_secret() -> str:
    secret = os.getenv("JWT_SECRET", "").strip()
    if not secret or "replace_with" in secret:
        raise RuntimeError(
            "JWT_SECRET is not configured. Set a strong random secret in .env."
        )
    return secret


def create_access_token(
    subject: str, expires_delta: Optional[timedelta] = None
) -> str:
    """Issue an HS256 JWT for the given subject (user UUID string)."""
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta or timedelta(hours=1))
    payload = {
        "sub": str(subject),
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "iss": ISSUER,
    }
    return jwt.encode(payload, _require_jwt_secret(), algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict:
    """Verify and decode a JWT; raises ``jwt.PyJWTError`` on failure."""
    return jwt.decode(
        token, _require_jwt_secret(), algorithms=[ALGORITHM], issuer=ISSUER
    )


async def get_current_user(
    authorization: Optional[str] = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> User:
    """FastAPI dependency: resolve the authenticated user from a bearer JWT."""
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing bearer token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not authorization or not authorization.lower().startswith("bearer "):
        raise credentials_error
    token = authorization.split(" ", 1)[1].strip()
    try:
        payload = decode_access_token(token)
        user_id = uuid.UUID(str(payload.get("sub", "")))
    except (jwt.PyJWTError, ValueError, TypeError, KeyError):
        raise credentials_error
    user = await db.get(User, user_id)
    if user is None:
        raise credentials_error
    return user