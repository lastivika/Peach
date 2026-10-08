import uuid
from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient

from app.db import get_session
from app.main import create_app
from app.models import User
from tests.tokens import make_token


@pytest.fixture
async def auth_client() -> AsyncIterator[AsyncClient]:
    app = create_app()

    async def unused_session():
        user = User(
            id=uuid.uuid4(),
            cognito_sub="alice-sub",
            email="alice@example.com",
            name="alice",
        )

        class Result:
            def scalar_one(self):
                return user

        class Session:
            executions = 0

            async def execute(self, _statement):
                self.executions += 1
                return Result() if self.executions == 2 else None

        yield Session()

    app.dependency_overrides[get_session] = unused_session
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            yield client
    finally:
        app.dependency_overrides.clear()


async def test_anonymous_cannot_access_items(auth_client):
    assert (await auth_client.get("/api/v1/items")).status_code == 401


async def test_rejects_wrong_audience_and_expired_token(auth_client):
    for overrides in [
        {"aud": "wrong"},
        {"exp": 1},
        {"token_use": "access"},
    ]:
        token = make_token(**overrides)
        response = await auth_client.get(
            "/api/v1/items", headers={"Authorization": "Bearer " + token}
        )
        assert response.status_code == 401


async def test_accepts_valid_token_with_unverified_email(auth_client):
    token = make_token(email_verified=False)
    response = await auth_client.get("/api/v1/me", headers={"Authorization": "Bearer " + token})

    assert response.status_code == 200
    assert response.json()["email"] == "alice@example.com"


async def test_rejects_malformed_token(auth_client):
    response = await auth_client.get(
        "/api/v1/me", headers={"Authorization": "Bearer not-a-valid-token"}
    )

    assert response.status_code == 401
