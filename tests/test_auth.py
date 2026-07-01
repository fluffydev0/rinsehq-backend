def test_signup_and_login(client):
    signup = client.post(
        "/v1/auth/signup",
        json={"email": "user@example.com", "password": "password123"},
    )
    assert signup.status_code == 201
    body = signup.json()
    assert body["success"] is True
    assert body["data"]["user"]["email"] == "user@example.com"

    login = client.post(
        "/v1/auth/login",
        json={"email": "user@example.com", "password": "password123"},
    )
    assert login.status_code == 200
    login_body = login.json()
    assert login_body["success"] is True
    assert "accessToken" in login_body["data"]

    token = login_body["data"]["accessToken"]
    me = client.get("/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["data"]["user"]["email"] == "user@example.com"


def test_signup_duplicate_email(client):
    payload = {"email": "dup@example.com", "password": "password123"}
    assert client.post("/v1/auth/signup", json=payload).status_code == 201
    duplicate = client.post("/v1/auth/signup", json=payload)
    assert duplicate.status_code == 409
    assert duplicate.json()["error"] == "An account with this email already exists"


def test_login_invalid_credentials(client):
    client.post(
        "/v1/auth/signup",
        json={"email": "user2@example.com", "password": "password123"},
    )
    response = client.post(
        "/v1/auth/login",
        json={"email": "user2@example.com", "password": "wrongpassword"},
    )
    assert response.status_code == 401
    assert response.json()["error"] == "Invalid email or password"


def test_me_requires_auth(client):
    response = client.get("/v1/auth/me")
    assert response.status_code == 401


def test_verify_email_flow(client):
    client.post("/v1/auth/signup", json={"email": "verify@example.com", "password": "password123"})
    from sqlalchemy import select
    from rinsehq.infrastructure.db.models import VerificationCodeModel
    from rinsehq.infrastructure.db import session as db_session

    session = db_session.get_session_factory()()
    code_row = session.scalar(
        select(VerificationCodeModel).where(VerificationCodeModel.email == "verify@example.com")
    )
    session.close()
    assert code_row is not None
    verify = client.post(
        "/v1/auth/verify-email",
        json={"email": "verify@example.com", "code": code_row.code},
    )
    assert verify.status_code == 200
    assert verify.json()["data"]["user"]["emailVerified"] is True


def test_forgot_password_sends_code(client):
    client.post("/v1/auth/signup", json={"email": "reset@example.com", "password": "password123"})
    response = client.post("/v1/auth/forgot-password", json={"email": "reset@example.com"})
    assert response.status_code == 200
    assert response.json()["success"] is True

    from sqlalchemy import select
    from rinsehq.infrastructure.db.models import PasswordResetCodeModel
    from rinsehq.infrastructure.db import session as db_session

    session = db_session.get_session_factory()()
    code_row = session.scalar(
        select(PasswordResetCodeModel).where(PasswordResetCodeModel.email == "reset@example.com")
    )
    session.close()
    assert code_row is not None
    assert len(code_row.code) == 6


def test_reset_password_success(client):
    client.post("/v1/auth/signup", json={"email": "reset2@example.com", "password": "password123"})
    client.post("/v1/auth/forgot-password", json={"email": "reset2@example.com"})

    from sqlalchemy import select
    from rinsehq.infrastructure.db.models import PasswordResetCodeModel
    from rinsehq.infrastructure.db import session as db_session

    session = db_session.get_session_factory()()
    code_row = session.scalar(
        select(PasswordResetCodeModel).where(PasswordResetCodeModel.email == "reset2@example.com")
    )
    session.close()
    assert code_row is not None

    reset = client.post(
        "/v1/auth/reset-password",
        json={"email": "reset2@example.com", "code": code_row.code, "newPassword": "newpassword123"},
    )
    assert reset.status_code == 200

    login = client.post(
        "/v1/auth/login",
        json={"email": "reset2@example.com", "password": "newpassword123"},
    )
    assert login.status_code == 200


def test_reset_password_invalid_code(client):
    client.post("/v1/auth/signup", json={"email": "reset3@example.com", "password": "password123"})
    client.post("/v1/auth/forgot-password", json={"email": "reset3@example.com"})
    response = client.post(
        "/v1/auth/reset-password",
        json={"email": "reset3@example.com", "code": "000000", "newPassword": "newpassword123"},
    )
    assert response.status_code == 400
    assert response.json()["error"] == "Invalid reset code"


def test_forgot_password_unknown_email(client):
    response = client.post("/v1/auth/forgot-password", json={"email": "nobody@example.com"})
    assert response.status_code == 200
    assert response.json()["success"] is True
