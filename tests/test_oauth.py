"""
GOOGLE_CLIENT_ID/SECRET are intentionally left unset in the test
environment (same as this sandbox's actual deployment) -- these tests
verify the "not configured" path returns a clean 503 instead of
crashing on an empty client_id. The real OAuth exchange (code -> token
-> userinfo -> user provisioning) can only be exercised with a real
Google Cloud OAuth client, which only the project owner can create.
"""


async def test_google_login_without_credentials_returns_503(client):
    res = await client.get("/auth/oauth/google/login", follow_redirects=False)
    assert res.status_code == 503
    assert "not configured" in res.json()["detail"].lower()


async def test_google_callback_without_credentials_returns_503(client):
    res = await client.get("/auth/oauth/google/callback", params={"code": "fake-code"})
    assert res.status_code == 503
