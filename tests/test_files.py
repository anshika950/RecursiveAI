async def test_upload_rejects_bad_extension(client, registered_user):
    res = await client.post(
        "/files/upload",
        headers={"Authorization": f"Bearer {registered_user['token']}"},
        files={"file": ("notes.exe", b"binary stuff", "application/octet-stream")},
    )
    assert res.status_code == 400


async def test_upload_rejects_empty_file(client, registered_user):
    res = await client.post(
        "/files/upload",
        headers={"Authorization": f"Bearer {registered_user['token']}"},
        files={"file": ("empty.txt", b"", "text/plain")},
    )
    assert res.status_code == 400


async def test_upload_txt_succeeds_and_is_chunked(client, registered_user):
    content = b"RecursiveAI is a FastAPI service. " * 50  # long enough to span multiple chunks
    res = await client.post(
        "/files/upload",
        headers={"Authorization": f"Bearer {registered_user['token']}"},
        files={"file": ("notes.txt", content, "text/plain")},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["filename"] == "notes.txt"
    assert data["chunk_count"] > 1


async def test_list_documents_returns_only_own_documents(client, registered_user):
    content = b"The quick brown fox jumps over the lazy dog. " * 10
    upload_res = await client.post(
        "/files/upload",
        headers={"Authorization": f"Bearer {registered_user['token']}"},
        files={"file": ("fox.txt", content, "text/plain")},
    )
    assert upload_res.status_code == 200

    list_res = await client.get(
        "/files/",
        headers={"Authorization": f"Bearer {registered_user['token']}"},
    )
    assert list_res.status_code == 200
    filenames = [d["filename"] for d in list_res.json()]
    assert "fox.txt" in filenames


async def test_upload_requires_auth(client):
    res = await client.post(
        "/files/upload",
        files={"file": ("notes.txt", b"hello", "text/plain")},
    )
    assert res.status_code == 403


async def test_generate_with_context_retrieves_uploaded_content(client, registered_user):
    unique_fact = "The internal project codename for this release is Zephyr-9."
    content = (unique_fact + " ") * 5 + "Some unrelated filler text about gardening and cooking. " * 20
    upload_res = await client.post(
        "/files/upload",
        headers={"Authorization": f"Bearer {registered_user['token']}"},
        files={"file": ("secret.txt", content.encode(), "text/plain")},
    )
    assert upload_res.status_code == 200

    res = await client.post(
        "/model/generate-with-context",
        headers={"Authorization": f"Bearer {registered_user['token']}"},
        json={"prompt": "What is the internal project codename?", "max_tokens": 50, "temperature": 0.5},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["context_chunks"], "expected at least one retrieved chunk"
    assert any("Zephyr-9" in chunk for chunk in data["context_chunks"])


async def test_generate_with_context_works_with_no_documents(client, registered_user):
    # A brand new user with nothing uploaded should still get a response,
    # just with no retrieved context.
    res = await client.post(
        "/model/generate-with-context",
        headers={"Authorization": f"Bearer {registered_user['token']}"},
        json={"prompt": "What is machine learning?", "max_tokens": 50, "temperature": 0.5},
    )
    assert res.status_code == 200
    assert res.json()["context_chunks"] == []
