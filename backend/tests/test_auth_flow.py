async def test_signup_creates_a_default_workspace(client):
    response = await client.post("/auth/signup", json={"email": "alice@example.com", "password": "correcthorse123"})
    assert response.status_code == 201

    orgs = await client.get("/organizations")
    assert orgs.status_code == 200
    body = orgs.json()
    assert len(body) == 1
    assert body[0]["role"] == "owner"


async def test_duplicate_signup_is_rejected(client):
    payload = {"email": "bob@example.com", "password": "correcthorse123"}
    first = await client.post("/auth/signup", json=payload)
    assert first.status_code == 201

    second = await client.post("/auth/signup", json=payload)
    assert second.status_code == 409


async def test_wrong_password_is_rejected(client):
    await client.post("/auth/signup", json={"email": "carol@example.com", "password": "correcthorse123"})
    await client.post("/auth/logout")

    response = await client.post("/auth/login", json={"email": "carol@example.com", "password": "wrongpassword"})
    assert response.status_code == 401


async def test_logout_invalidates_the_session(client):
    await client.post("/auth/signup", json={"email": "dave@example.com", "password": "correcthorse123"})
    assert (await client.get("/auth/me")).status_code == 200

    await client.post("/auth/logout")
    assert (await client.get("/auth/me")).status_code == 401


async def test_me_requires_authentication(client):
    response = await client.get("/auth/me")
    assert response.status_code == 401
