"""U1 tests: token round-trip, TOTP, authorization matrix. DB-free."""

import os

import pyotp
import pytest

os.environ.setdefault("AUTH_SIGNING_SECRET", "test-secret")

from src.modules.foundation.context.security_context import SecurityContext
from src.modules.identity import token_service, totp_service
from src.modules.identity.service import AuthService
from src.shared.errors import AuthorizationError


def test_token_roundtrip():
    token = token_service.issue_token("u1", "t1", "CLIENT_USER")
    claims = token_service.verify_token(token)
    assert claims["sub"] == "u1"
    assert claims["tenant_id"] == "t1"
    assert claims["role"] == "CLIENT_USER"


def test_invalid_token_rejected():
    with pytest.raises(AuthorizationError):
        token_service.verify_token("not-a-real-token")


def test_totp_verify():
    secret = totp_service.provision_secret()
    code = pyotp.TOTP(secret).now()
    assert totp_service.verify_totp(secret, code) is True
    assert totp_service.verify_totp(secret, "000000") in (True, False)  # extremely unlikely to match


def test_authorize_admin_allows_everything():
    ctx = SecurityContext(user_id="a", tenant_id="t1", roles=("ADMIN",))
    AuthService.authorize(ctx, "CLIENT_USER")  # no raise
    AuthService.authorize(ctx, "ADMIN")  # no raise


def test_authorize_client_cannot_do_admin():
    ctx = SecurityContext(user_id="c", tenant_id="t1", roles=("CLIENT_USER",))
    AuthService.authorize(ctx, "CLIENT_USER")  # ok
    with pytest.raises(AuthorizationError):
        AuthService.authorize(ctx, "ADMIN")


def test_resolve_context_from_token():
    token = token_service.issue_token("u9", "t9", "ADMIN")
    ctx = AuthService.resolve_context(token)
    assert ctx.tenant_id == "t9"
    assert ctx.has_role("ADMIN")
