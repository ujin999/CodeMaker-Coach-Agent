"""JWT 인증 유틸 — 토큰 발급·검증, 비밀번호 해시.

passlib 대신 bcrypt 라이브러리를 직접 사용한다.
시크릿은 코드에 하드코딩하지 않고 반드시 config.settings(.env의 JWT_SECRET_KEY)로 관리한다 (NFR-3).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

from config.settings import settings

# ── 설정 ────────────────────────────────────────────────────────────────────
if not settings.jwt_secret_key:
    raise RuntimeError(
        "JWT_SECRET_KEY가 설정되지 않았습니다. .env에 안전한 랜덤 값을 설정하세요 "
        '(예: python -c "import secrets; print(secrets.token_urlsafe(64))").'
    )
_SECRET_KEY = settings.jwt_secret_key
_ALGORITHM = "HS256"
_ACCESS_TOKEN_EXPIRE_MINUTES = settings.jwt_expire_minutes

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


# ── 비밀번호 (bcrypt 직접 사용) ─────────────────────────────────────────────

def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


# ── JWT ─────────────────────────────────────────────────────────────────────

def create_access_token(user_id: int, email: str) -> str:
    """Access JWT 발급. sub = user_id(str)."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=_ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": str(user_id),
        "email": email,
        "exp": expire,
    }
    return jwt.encode(payload, _SECRET_KEY, algorithm=_ALGORITHM)


def decode_token(token: str) -> dict:
    """토큰 검증 후 payload 반환. 실패 시 HTTPException 401."""
    try:
        payload = jwt.decode(token, _SECRET_KEY, algorithms=[_ALGORITHM])
        if payload.get("sub") is None:
            raise ValueError("sub missing")
        return payload
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="인증 토큰이 유효하지 않습니다.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


# ── FastAPI 의존성 ───────────────────────────────────────────────────────────

def get_current_user_id(token: str = Depends(oauth2_scheme)) -> int:
    """보호된 라우터에서 현재 사용자 ID를 꺼내는 의존성."""
    payload = decode_token(token)
    return int(payload["sub"])
