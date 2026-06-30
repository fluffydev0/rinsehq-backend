def test_signup_and_login(client):
    signup = client.post(
        "/api/v1/auth/signup",
        json={"email": "user@example.com", "password": "password123", "name": "Test User"},
    )
    assert signup.status_code == 201
    assert signup.json()["email"] == "user@example.com"

    login = client.post(
        "/api/v1/auth/login",
        json={"email": "user@example.com", "password": "password123"},
    )
    assert login.status_code == 200
    assert "access_token" in login.json()

    token = login.json()["access_token"]
    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == "user@example.com"


def test_signup_duplicate_email(client):
    payload = {"email": "dup@example.com", "password": "password123"}
    assert client.post("/api/v1/auth/signup", json=payload).status_code == 201
    duplicate = client.post("/api/v1/auth/signup", json=payload)
    assert duplicate.status_code == 409


def test_login_invalid_credentials(client):
    client.post(
        "/api/v1/auth/signup",
        json={"email": "user2@example.com", "password": "password123"},
    )
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "user2@example.com", "password": "wrongpassword"},
    )
    assert response.status_code == 401


def test_me_requires_auth(client):
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401
