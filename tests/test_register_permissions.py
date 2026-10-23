"""Public registration must not hand out admin rights or asset ownership."""
import os
import secrets

os.environ["JWT_SECRET_KEY"] = "k" * 16 + "-test-only-not-a-real-secret-" + "z" * 8
os.environ["DATABASE_URL"] = "postgresql://test@db.invalid/test"

from datetime import datetime, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.auth.jwt_utils import create_access_token
from src.config.database import get_db
from src.models.user import User
from src.routers import auth


class FakeResult:
    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        return self.value


class FakeSession:
    """Answers the two queries register needs: 'user exists?' and 'who is this token?'."""

    def __init__(self, token_user=None):
        self.token_user = token_user
        self.added = []

    async def execute(self, statement):
        is_lookup_by_id = "WHERE users.id =" in str(statement)
        return FakeResult(self.token_user if is_lookup_by_id else None)

    def add(self, user):
        self.added.append(user)

    async def commit(self):
        pass

    async def refresh(self, user):
        user.id = 99
        user.created_at = user.updated_at = datetime.now(timezone.utc)


def client_with(session: FakeSession) -> TestClient:
    app = FastAPI()
    app.include_router(auth.router, prefix="/auth")

    async def fake_db():
        yield session

    app.dependency_overrides[get_db] = fake_db
    return TestClient(app)


def account(**extra):
    return {"email": "new@example.com", "username": "new", "password": secrets.token_urlsafe(12), **extra}


def admin_user():
    return User(id=1, email="a@example.com", username="a", hashed_password="x", is_active=True, is_superuser=True)


@pytest.mark.parametrize("extra", [
    {"is_superuser": True},
    {"dueno_de_activo": "Gerencia de Pensiones"},
    {"is_active": False},
])
def test_anonymous_cannot_register_privileged_accounts(extra):
    session = FakeSession()
    response = client_with(session).post("/auth/register", json=account(**extra))
    assert response.status_code == 403
    assert session.added == []


def test_anonymous_can_register_a_plain_account():
    session = FakeSession()
    response = client_with(session).post("/auth/register", json=account())
    assert response.status_code == 201, response.text
    assert session.added[0].is_superuser is False
    assert session.added[0].dueno_de_activo is None


def test_superuser_can_register_privileged_accounts():
    # `sub` is a string: PyJWT 2.10 rejects non-string subjects.
    token = create_access_token({"sub": "1"})
    session = FakeSession(token_user=admin_user())
    response = client_with(session).post(
        "/auth/register",
        json=account(is_superuser=True, dueno_de_activo="Gerencia de Pensiones"),
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201, response.text
    assert session.added[0].is_superuser is True


def test_regular_user_token_does_not_unlock_privileged_fields():
    token = create_access_token({"sub": "2"})
    regular = User(id=2, email="u@example.com", username="u", hashed_password="x", is_active=True, is_superuser=False)
    session = FakeSession(token_user=regular)
    response = client_with(session).post(
        "/auth/register", json=account(is_superuser=True), headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 403


def test_invalid_token_is_rejected():
    session = FakeSession()
    response = client_with(session).post(
        "/auth/register", json=account(is_superuser=True), headers={"Authorization": "Bearer not-a-token"}
    )
    assert response.status_code == 401
