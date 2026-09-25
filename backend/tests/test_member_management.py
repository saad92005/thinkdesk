async def _create_org_with_invited_member(client, second_client, owner_email: str, member_email: str) -> str:
    await client.post("/auth/signup", json={"email": owner_email, "password": "correcthorse123"})
    org_id = (await client.get("/organizations")).json()[0]["id"]
    await second_client.post("/auth/signup", json={"email": member_email, "password": "correcthorse123"})
    await client.post(f"/organizations/{org_id}/members", json={"email": member_email, "role": "member"})
    return org_id


async def test_owner_can_change_a_members_role(client, second_client):
    org_id = await _create_org_with_invited_member(client, second_client, "owner1@example.com", "mem1@example.com")
    member_user_id = next(
        m["user_id"] for m in (await client.get(f"/organizations/{org_id}/members")).json() if m["email"] == "mem1@example.com"
    )

    response = await client.patch(f"/organizations/{org_id}/members/{member_user_id}", json={"role": "admin"})

    assert response.status_code == 200
    assert response.json()["role"] == "admin"


async def test_owner_can_remove_a_member(client, second_client):
    org_id = await _create_org_with_invited_member(client, second_client, "owner2@example.com", "mem2@example.com")
    member_user_id = next(
        m["user_id"] for m in (await client.get(f"/organizations/{org_id}/members")).json() if m["email"] == "mem2@example.com"
    )

    response = await client.delete(f"/organizations/{org_id}/members/{member_user_id}")
    assert response.status_code == 204

    remaining_emails = {m["email"] for m in (await client.get(f"/organizations/{org_id}/members")).json()}
    assert "mem2@example.com" not in remaining_emails

    # Removed member no longer sees the workspace at all.
    orgs = (await second_client.get("/organizations")).json()
    assert not any(org["id"] == org_id for org in orgs)


async def test_last_owner_cannot_be_demoted(client):
    await client.post("/auth/signup", json={"email": "soleowner1@example.com", "password": "correcthorse123"})
    org_id = (await client.get("/organizations")).json()[0]["id"]
    owner_user_id = (await client.get(f"/organizations/{org_id}/members")).json()[0]["user_id"]

    response = await client.patch(f"/organizations/{org_id}/members/{owner_user_id}", json={"role": "member"})

    assert response.status_code == 409


async def test_last_owner_cannot_be_removed(client):
    await client.post("/auth/signup", json={"email": "soleowner2@example.com", "password": "correcthorse123"})
    org_id = (await client.get("/organizations")).json()[0]["id"]
    owner_user_id = (await client.get(f"/organizations/{org_id}/members")).json()[0]["user_id"]

    response = await client.delete(f"/organizations/{org_id}/members/{owner_user_id}")

    assert response.status_code == 409


async def test_member_can_remove_themselves(client, second_client):
    org_id = await _create_org_with_invited_member(client, second_client, "owner3@example.com", "mem3@example.com")
    member_user_id = next(
        m["user_id"] for m in (await client.get(f"/organizations/{org_id}/members")).json() if m["email"] == "mem3@example.com"
    )

    response = await second_client.delete(f"/organizations/{org_id}/members/{member_user_id}")

    assert response.status_code == 204


async def test_plain_member_cannot_change_others_roles(client, second_client):
    org_id = await _create_org_with_invited_member(client, second_client, "owner4@example.com", "mem4@example.com")
    owner_user_id = next(
        m["user_id"] for m in (await client.get(f"/organizations/{org_id}/members")).json() if m["email"] == "owner4@example.com"
    )

    response = await second_client.patch(f"/organizations/{org_id}/members/{owner_user_id}", json={"role": "member"})

    assert response.status_code == 403


async def test_plain_member_cannot_remove_others(client, second_client):
    org_id = await _create_org_with_invited_member(client, second_client, "owner5@example.com", "mem5@example.com")
    owner_user_id = next(
        m["user_id"] for m in (await client.get(f"/organizations/{org_id}/members")).json() if m["email"] == "owner5@example.com"
    )

    response = await second_client.delete(f"/organizations/{org_id}/members/{owner_user_id}")

    assert response.status_code == 403
