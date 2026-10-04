def test_login_success(client):
    response = client.post(
        "/api/v1/auth/login",
        json={"username_or_email": "admin@anvaya.demo", "password": "DemoPassword123!"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "admin@anvaya.demo"
    assert data["user"]["role"] == "SUPER_ADMIN"
    assert "patient.view" in data["user"]["permissions"]

def test_login_invalid_password(client):
    response = client.post(
        "/api/v1/auth/login",
        json={"username_or_email": "admin@anvaya.demo", "password": "WrongPassword!"}
    )
    assert response.status_code == 401
    assert "Incorrect username/email or password" in response.json()["detail"]

def test_login_unknown_user(client):
    response = client.post(
        "/api/v1/auth/login",
        json={"username_or_email": "unknown@hospital.com", "password": "DemoPassword123!"}
    )
    assert response.status_code == 401

def test_get_current_user_me(client, admin_headers):
    response = client.get("/api/v1/auth/me", headers=admin_headers)
    assert response.status_code == 200
    assert response.json()["email"] == "admin@anvaya.demo"

def test_unauthorized_access(client):
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401
