"""Auth endpoints (LC-U1-6): POST /auth/login, POST /auth/mfa/verify."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..foundation.persistence.database import get_session
from ...shared.errors import AuthorizationError
from .service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


class MfaRequest(BaseModel):
    user_id: str
    code: str


class LoginResponse(BaseModel):
    token: str | None = None
    mfa_required: bool = False
    user_id: str | None = None


@router.post("/login", response_model=LoginResponse)
def login(body: LoginRequest, session: Session = Depends(get_session)):
    try:
        outcome = AuthService(session).login(body.username, body.password)
        session.commit()
    except AuthorizationError as exc:
        session.commit()  # persist throttle counter updates
        raise HTTPException(status_code=401, detail=str(exc))
    return LoginResponse(token=outcome.token, mfa_required=outcome.mfa_required, user_id=outcome.user_id)


@router.post("/mfa/verify", response_model=LoginResponse)
def mfa_verify(body: MfaRequest, session: Session = Depends(get_session)):
    try:
        outcome = AuthService(session).verify_mfa(body.user_id, body.code)
    except AuthorizationError as exc:
        raise HTTPException(status_code=401, detail=str(exc))
    return LoginResponse(token=outcome.token)
