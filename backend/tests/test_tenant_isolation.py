"""The security property the whole authorization design exists for:
one organization's data must never be reachable by another organization's
member, regardless of what they guess or request directly.
"""


async def test_non_member_cannot_list_another_orgs_members(client, second_client):
    await client.post("/auth/signup", json={"email": "owner@example.com", "password": "correcthorse123"})
    owner_orgs = (await client.get("/organizations")).json()
    org_id = owner_orgs[0]["id"]

    await second_client.post("/auth/signup", json={"email": "intruder@example.com", "password": "correcthorse123"})

    response = await second_client.get(f"/organizations/{org_id}/members")
    assert response.status_code == 403


async def test_non_member_cannot_list_another_orgs_documents(client, second_client):
    await client.post("/auth/signup", json={"email": "owner2@example.com", "password": "correcthorse123"})
    org_id = (await client.get("/organizations")).json()[0]["id"]

    await second_client.post("/auth/signup", json={"email": "intruder2@example.com", "password": "correcthorse123"})

    response = await second_client.get(f"/organizations/{org_id}/documents")
    assert response.status_code == 403


async def test_non_member_cannot_search_another_orgs_knowledge(client, second_client):
    await client.post("/auth/signup", json={"email": "owner3@example.com", "password": "correcthorse123"})
    org_id = (await client.get("/organizations")).json()[0]["id"]

    await second_client.post("/auth/signup", json={"email": "intruder3@example.com", "password": "correcthorse123"})

    response = await second_client.post(f"/organizations/{org_id}/search", json={"query": "anything", "top_k": 5})
    assert response.status_code == 403


async def test_unauthenticated_request_is_rejected_before_org_check(client):
    # No signup/login at all -- should fail at authentication, not leak
    # whether the org even exists.
    fake_org_id = "00000000-0000-0000-0000-000000000000"
    response = await client.get(f"/organizations/{fake_org_id}/members")
    assert response.status_code == 401
