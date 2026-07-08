"""인증 라우터 — 회원가입 / 로그인 / 내 정보 / 탈퇴 (FR-27, FR-28)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import (
    create_access_token,
    get_current_user_id,
    hash_password,
    verify_password,
)
from app.db import get_db
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(body: RegisterRequest, db: Session = Depends(get_db)) -> TokenResponse:
    """회원가입 — 이메일 중복 시 409."""
    if db.query(User).filter(User.email == body.email).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="이미 사용 중인 이메일입니다.")
    user = User(
        email=body.email,
        password_hash=hash_password(body.password),
        display_name=body.display_name,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token(user.id, user.email)
    return TokenResponse(access_token=token)


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    """로그인 — 이메일+비밀번호 검증 후 JWT 발급."""
    user = db.query(User).filter(User.email == body.email).first()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="이메일 또는 비밀번호가 올바르지 않습니다.",
        )
    token = create_access_token(user.id, user.email)
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserResponse)
def get_me(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> UserResponse:
    """현재 로그인한 사용자 정보 조회."""
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="사용자를 찾을 수 없습니다.")
    return UserResponse.model_validate(user)


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
def delete_me(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> None:
    """계정 및 개인 데이터 삭제 (FR-28 — 개인정보 삭제권)."""
    user = db.get(User, user_id)
    if user:
        db.delete(user)
        db.commit()


@router.get("/weaknesses", status_code=status.HTTP_200_OK)
def get_my_weaknesses(
    user_id: int = Depends(get_current_user_id),
) -> dict:
    """로그인한 현재 사용자의 AI 취약점 진단 및 다음 추천 학습 조회 (Phase 4)."""
    from packages.graphrag import get_user_weaknesses
    return get_user_weaknesses(user_id)
