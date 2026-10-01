from tests.tokens import make_token


async def test_anonymous_cannot_access_items(anon_client):
    assert (await anon_client.get("/api/v1/items")).status_code == 401


async def test_rejects_wrong_audience_and_expired_token(anon_client):
    for overrides in [
        {"aud": "wrong"},
        {"exp": 1},
        {"token_use": "access"},
        {"email_verified": False},
    ]:
        token = make_token(**overrides)
        response = await anon_client.get(
            "/api/v1/items", headers={"Authorization": "Bearer " + token}
        )
        assert response.status_code == 401
