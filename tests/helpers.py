def signup_and_token(client, email: str, password: str = "password123") -> dict:
    client.post("/v1/auth/signup", json={"email": email, "password": password})
    login = client.post("/v1/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200, login.text
    data = login.json()["data"]
    token = data["accessToken"]
    return {"Authorization": f"Bearer {token}"}
