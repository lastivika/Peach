import uuid

from httpx import AsyncClient

from tests.tokens import make_token


def payload(**overrides):
    return {
        "title": "Planning",
        "start_at": "2026-10-12T10:00:00Z",
        "end_at": "2026-10-12T11:30:00Z",
        "location": "https://meet.example.com/room",
        "purpose": "Plan the week",
        **overrides,
    }


async def test_meeting_crud_and_range_filter(client: AsyncClient):
    created_response = await client.post("/api/v1/meetings", json=payload())
    assert created_response.status_code == 201
    created = created_response.json()
    assert created["title"] == "Planning"
    assert created["location"].startswith("https://")
    assert uuid.UUID(created["id"])

    inside = await client.get(
        "/api/v1/meetings", params={"start": "2026-10-12T00:00:00Z", "end": "2026-10-13T00:00:00Z"}
    )
    outside = await client.get(
        "/api/v1/meetings", params={"start": "2026-10-13T00:00:00Z", "end": "2026-10-14T00:00:00Z"}
    )
    assert inside.json()["total"] == 1
    assert outside.json()["meetings"] == []

    updated = await client.patch(f"/api/v1/meetings/{created['id']}", json={"title": "Updated"})
    assert updated.status_code == 200
    assert updated.json()["title"] == "Updated"
    assert (await client.delete(f"/api/v1/meetings/{created['id']}")).status_code == 204
    assert (await client.get(f"/api/v1/meetings/{created['id']}")).status_code == 404


async def test_meeting_validation(client: AsyncClient):
    assert (await client.post("/api/v1/meetings", json=payload(title=""))).status_code == 422
    assert (
        await client.post("/api/v1/meetings", json=payload(end_at="2026-10-12T10:00:00Z"))
    ).status_code == 422
    created = (await client.post("/api/v1/meetings", json=payload())).json()
    invalid = await client.patch(
        f"/api/v1/meetings/{created['id']}", json={"end_at": "2026-10-12T09:00:00Z"}
    )
    assert invalid.status_code == 422


async def test_meetings_require_auth_and_are_owner_scoped(client: AsyncClient):
    assert (
        await client.get(
            "/api/v1/meetings",
            params={"start": "2026-10-01T00:00:00Z", "end": "2026-11-01T00:00:00Z"},
            headers={"Authorization": ""},
        )
    ).status_code == 401
    created = (await client.post("/api/v1/meetings", json=payload())).json()
    bob = {"Authorization": f"Bearer {make_token('bob-sub', 'bob@example.com')}"}
    url = f"/api/v1/meetings/{created['id']}"
    assert (
        await client.get(
            "/api/v1/meetings",
            params={"start": "2026-10-01T00:00:00Z", "end": "2026-11-01T00:00:00Z"},
            headers=bob,
        )
    ).json()["meetings"] == []
    assert (await client.get(url, headers=bob)).status_code == 404
    assert (await client.patch(url, json={"title": "stolen"}, headers=bob)).status_code == 404
    assert (await client.delete(url, headers=bob)).status_code == 404
