async def test_regular_user_forbidden_from_admin_users(client, registered_user):
    res = await client.get(
        "/admin/users",
        headers={"Authorization": f"Bearer {registered_user['token']}"},
    )
    assert res.status_code == 403


async def test_regular_user_forbidden_from_admin_stats(client, registered_user):
    res = await client.get(
        "/admin/stats",
        headers={"Authorization": f"Bearer {registered_user['token']}"},
    )
    assert res.status_code == 403


async def test_admin_user_can_list_users(client, admin_user, registered_user):
    res = await client.get(
        "/admin/users",
        headers={"Authorization": f"Bearer {admin_user['token']}"},
    )
    assert res.status_code == 200
    usernames = [u["username"] for u in res.json()]
    assert admin_user["username"] in usernames
    assert registered_user["username"] in usernames


async def test_admin_user_can_view_stats(client, admin_user):
    res = await client.get(
        "/admin/stats",
        headers={"Authorization": f"Bearer {admin_user['token']}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert "total_requests" in data
    assert "total_tokens_used" in data
    assert "fallback_responses" in data


async def test_admin_endpoints_require_auth(client):
    res = await client.get("/admin/users")
    assert res.status_code == 403
