from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User
from app.models.refresh_session import RefreshSession

from app.schemas.auth import (
    RegisterRequest,
    TokenResponse
)
from app.schemas.user import UserResponse

from app.core.config import settings
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    hash_refresh_token
)

from app.api.deps import get_current_user


router = APIRouter()

REFRESH_COOKIE_NAME = "dxf2bom_refresh"
REFRESH_COOKIE_PATH = "/api/v1/auth"


def set_refresh_cookie(
    response: Response,
    token: str
) -> None:
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=token,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        httponly=True,
        secure=settings.ENVIRONMENT == "production",
        samesite="lax",
        path=REFRESH_COOKIE_PATH
    )


def clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(
        key=REFRESH_COOKIE_NAME,
        httponly=True,
        secure=settings.ENVIRONMENT == "production",
        samesite="lax",
        path=REFRESH_COOKIE_PATH
    )


@router.post("/register", response_model=UserResponse, status_code=201)
def register(
    payload: RegisterRequest,
    db: Session = Depends(get_db)
):
    email = payload.email.lower()

    existing_user = db.query(User).filter(
        User.email == email
    ).first()

    if existing_user:
        raise HTTPException(
            status_code=409,
            detail="Email already registered"
        )

    user = User(
        email=email,
        password_hash=hash_password(payload.password)
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user


@router.post("/login", response_model=TokenResponse)
def login(
    response: Response,
    payload: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(
        User.email == payload.username.lower()
    ).first()

    if not user or not verify_password(
        payload.password,
        user.password_hash
    ):
        raise HTTPException(
            status_code=401,
            detail="Incorrect email or password"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=403,
            detail="Account inactive"
        )

    refresh_token = create_refresh_token()

    refresh_session = RefreshSession(
        user_id=user.id,
        token_hash=hash_refresh_token(refresh_token),
        expires_at=datetime.now(timezone.utc) + timedelta(
            days=settings.REFRESH_TOKEN_EXPIRE_DAYS
        )
    )

    db.add(refresh_session)
    db.commit()

    set_refresh_cookie(response, refresh_token)

    access_token = create_access_token(str(user.id))

    return TokenResponse(
        access_token=access_token
    )


@router.post("/refresh", response_model=TokenResponse)
def refresh(
    request: Request,
    response: Response,
    db: Session = Depends(get_db)
):
    refresh_token = request.cookies.get(REFRESH_COOKIE_NAME)

    if not refresh_token:
        raise HTTPException(
            status_code=401,
            detail="Refresh session missing"
        )

    token_hash = hash_refresh_token(refresh_token)

    # Lock this session row so simultaneous refresh requests
    # cannot both rotate the same token successfully.
    refresh_session = db.query(RefreshSession).filter(
        RefreshSession.token_hash == token_hash
    ).with_for_update().first()

    now = datetime.now(timezone.utc)

    if (
        not refresh_session
        or refresh_session.revoked_at is not None
        or refresh_session.expires_at <= now
    ):
        raise HTTPException(
            status_code=401,
            detail="Refresh session is invalid or expired"
        )

    user = db.query(User).filter(
        User.id == refresh_session.user_id
    ).first()

    if not user or not user.is_active:
        refresh_session.revoked_at = now
        db.commit()

        raise HTTPException(
            status_code=401,
            detail="User session is no longer valid"
        )

    # Revoke the old refresh session.
    refresh_session.revoked_at = now

    # Create a replacement refresh session.
    new_refresh_token = create_refresh_token()

    new_refresh_session = RefreshSession(
        user_id=user.id,
        token_hash=hash_refresh_token(new_refresh_token),
        expires_at=now + timedelta(
            days=settings.REFRESH_TOKEN_EXPIRE_DAYS
        )
    )

    db.add(new_refresh_session)
    db.commit()

    set_refresh_cookie(response, new_refresh_token)

    access_token = create_access_token(str(user.id))

    return TokenResponse(
        access_token=access_token
    )


@router.post("/logout", status_code=204)
def logout(
    request: Request,
    db: Session = Depends(get_db)
):
    refresh_token = request.cookies.get(REFRESH_COOKIE_NAME)

    if refresh_token:
        token_hash = hash_refresh_token(refresh_token)

        refresh_session = db.query(RefreshSession).filter(
            RefreshSession.token_hash == token_hash
        ).first()

        if refresh_session and refresh_session.revoked_at is None:
            refresh_session.revoked_at = datetime.now(timezone.utc)
            db.commit()

    response = Response(status_code=204)
    clear_refresh_cookie(response)

    return response


@router.get("/me", response_model=UserResponse)
def get_me(
    current_user: User = Depends(get_current_user)
):
    return current_user