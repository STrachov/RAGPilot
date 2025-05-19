import pytest
import time


def test_login_success(client, normal_token):
    """Test successful login with valid credentials."""
    login_data = {
        "username": "user@example.com",
        "password": "userpassword"
    }
    
    response = client.post("/api/login", data=login_data)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_wrong_password(client, normal_token):
    """Test failed login with incorrect password."""
    login_data = {
        "username": "user@example.com",
        "password": "wrongpassword"
    }
    
    response = client.post("/api/login", data=login_data)
    assert response.status_code == 401
    assert "incorrect" in response.json()["detail"].lower()


def test_login_nonexistent_user(client):
    """Test failed login with non-existent email."""
    login_data = {
        "username": "nonexistent@example.com",
        "password": "anypassword"
    }
    
    response = client.post("/api/login", data=login_data)
    assert response.status_code == 401
    assert "incorrect" in response.json()["detail"].lower()


def test_token_validation(client, normal_token):
    """Test token validation."""
    response = client.get(
        "/api/users/me",
        headers={"Authorization": f"Bearer {normal_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "user@example.com"


def test_expired_token(client, monkeypatch):
    """Test behavior with expired token."""
    # Create user
    user_data = {
        "email": "expired@example.com",
        "password": "expiredpassword",
        "full_name": "Expired Token User",
        "is_active": True
    }
    
    client.post("/api/users", json=user_data)
    
    # Mock token creation with very short expiry
    from app.core.security import create_access_token
    
    original_create_token = create_access_token
    
    def mock_token(subject, expires_delta=None):
        return original_create_token(subject, expires_delta=0.1)
    
    monkeypatch.setattr("app.api.endpoints.login.create_access_token", mock_token)
    
    # Get token
    response = client.post("/api/login", data={
        "username": user_data["email"],
        "password": user_data["password"]
    })
    token = response.json()["access_token"]
    
    # Wait for token to expire
    time.sleep(0.2)
    
    # Try to use expired token
    response = client.get(
        "/api/users/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 401
    assert "expired" in response.json()["detail"].lower() 