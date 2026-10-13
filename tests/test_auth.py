async def test_register_returns_token(client):
    payload = {
        "username": "bob_register",
        "email": "bob@example.com",
        "password": "StrongPass123",
    }
    res = await client.post("/auth/register", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


async def test_duplicate_username_rejected(client):
    payload = {
        "username": "dup_user",
        "email": "dup1@example.com",
        "password": "StrongPass123",
    }
    first = await client.post("/auth/register", json=payload)
    assert first.status_code == 200

    payload["email"] = "dup2@example.com"
    second = await client.post("/auth/register", json=payload)
    assert second.status_code == 400
    assert "already registered" in second.json()["detail"].lower()


async def test_duplicate_email_rejected(client):
    payload = {
        "username": "email_dup_1",
        "email": "shared@example.com",
        "password": "StrongPass123",
    }
    first = await client.post("/auth/register", json=payload)
    assert first.status_code == 200

    payload["username"] = "email_dup_2"
    second = await client.post("/auth/register", json=payload)
    assert second.status_code == 400


async def test_login_success(client, registered_user):
    res = await client.post(
        "/auth/login",
        json={"username": registered_user["username"], "password": registered_user["password"]},
    )
    assert res.status_code == 200
    assert "access_token" in res.json()


async def test_login_wrong_password_rejected(client, registered_user):
    res = await client.post(
        "/auth/login",
        json={"username": registered_user["username"], "password": "WrongPassword"},
    )
    assert res.status_code == 401


async def test_login_unknown_user_rejected(client):
    res = await client.post(
        "/auth/login",
        json={"username": "nobody_here", "password": "whatever123"},
    )
    assert res.status_code == 401


async def test_register_rejects_short_password(client):
    res = await client.post(
        "/auth/register",
        json={"username": "shortpw", "email": "shortpw@example.com", "password": "short"},
    )
    assert res.status_code == 422


async def test_register_rejects_invalid_email(client):
    res = await client.post(
        "/auth/register",
        json={"username": "bademail", "email": "not-an-email", "password": "StrongPass123"},
    )
    assert res.status_code == 422
