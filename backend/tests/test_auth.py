from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient

from app.db import get_session
from app.main import create_app
from tests.tokens import make_token


@pytest.fixture
async def auth_client() -> AsyncIterator[AsyncClient]:
    app = create_app()

    async def unused_session():
        yield None

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


async def test_unverified_email_is_forbidden_without_invalidating_session(auth_client):
    token = make_token(email_verified=False)
    response = await auth_client.get("/api/v1/items", headers={"Authorization": "Bearer " + token})

    assert response.status_code == 403
    assert response.json()["detail"] == "Verify your email address before accessing Peach"
