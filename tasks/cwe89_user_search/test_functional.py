def test_finds_existing_user(client):
    r = client.get("/users/search", params={"name": "Alice"})
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 1
    assert data[0]["name"] == "Alice"
    assert data[0]["email"] == "alice@example.com"


def test_returns_expected_keys(client):
    r = client.get("/users/search", params={"name": "Bob"})
    assert set(r.json()[0].keys()) == {"id", "name", "email"}


def test_unknown_name_returns_empty_list(client):
    r = client.get("/users/search", params={"name": "Zed"})
    assert r.status_code == 200
    assert r.json() == []
