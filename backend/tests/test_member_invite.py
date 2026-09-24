async def test_owner_can_add_an_existing_user_as_a_member(client, second_client):
    await client.post("/auth/signup", json={"email": "owner_inv@example.com", "password": "correcthorse123"})
    org_id = (await client.get("/organizations")).json()[0]["id"]

    await second_client.post("/auth/signup", json={"email": "teammate@example.com", "password": "correcthorse123"})

    response = await client.post(
        f"/organizations/{org_id}/members", json={"email": "teammate@example.com", "role": "member"}
    )
    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "teammate@example.com"
    assert body["role"] == "member"

    # The invited user can now see the workspace.
    orgs = (await second_client.get("/organizations")).json()
    assert any(org["id"] == org_id for org in orgs)


async def test_inviting_an_email_with_no_account_returns_404(client):
    await client.post("/auth/signup", json={"email": "owner_inv2@example.com", "password": "correcthorse123"})
    org_id = (await client.get("/organizations")).json()[0]["id"]

    response = await client.post(
        f"/organizations/{org_id}/members", json={"email": "nobody@example.com", "role": "member"}
    )
    assert response.status_code == 404


async def test_inviting_an_existing_member_again_returns_409(client, second_client):
    await client.post("/auth/signup", json={"email": "owner_inv3@example.com", "password": "correcthorse123"})
    org_id = (await client.get("/organizations")).json()[0]["id"]
    await second_client.post("/auth/signup", json={"email": "teammate3@example.com", "password": "correcthorse123"})

    first = await client.post(
        f"/organizations/{org_id}/members", json={"email": "teammate3@example.com", "role": "member"}
    )
    assert first.status_code == 201

    second = await client.post(
        f"/organizations/{org_id}/members", json={"email": "teammate3@example.com", "role": "member"}
    )
    assert second.status_code == 409


async def test_a_plain_member_cannot_add_other_members(client, second_client):
    await client.post("/auth/signup", json={"email": "owner_inv4@example.com", "password": "correcthorse123"})
    org_id = (await client.get("/organizations")).json()[0]["id"]

    await second_client.post("/auth/signup", json={"email": "member4@example.com", "password": "correcthorse123"})
    await client.post(f"/organizations/{org_id}/members", json={"email": "member4@example.com", "role": "member"})

    response = await second_client.post(
        f"/organizations/{org_id}/members", json={"email": "someoneelse@example.com", "role": "member"}
    )
    assert response.status_code == 403
