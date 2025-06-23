import pytest
from app.core.config.constants import UserRole


def test_register_user_success(client):
    """Test successful user registration with valid data."""
    user_data = {
        "email": "newuser@example.com",
        "password": "securepassword123",
        "full_name": "New User",
        "is_active": True,
        "role": UserRole.USER
    }
    
    response = client.post("/api/users", json=user_data)
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == user_data["email"]
    assert data["full_name"] == user_data["full_name"]
    assert "password" not in data
    assert "hashed_password" not in data


def test_register_existing_email(client, normal_token):
    """Test registration failure when email already exists."""
    user_data = {
        "email": "user@example.com",  # Already exists from fixture
        "password": "anotherpassword",
        "full_name": "Duplicate User",
        "is_active": True,
        "role": UserRole.USER
    }
    
    response = client.post("/api/users", json=user_data)
    assert response.status_code == 400
    assert "email already registered" in response.json()["detail"].lower()


def test_register_invalid_email(client):
    """Test registration failure with invalid email format."""
    user_data = {
        "email": "notavalidemail",
        "password": "password123",
        "full_name": "Invalid Email User",
        "is_active": True,
        "role": UserRole.USER
    }
    
    response = client.post("/api/users", json=user_data)
    assert response.status_code == 422  # Validation error


def test_register_short_password(client):
    """Test registration failure with too short password."""
    user_data = {
        "email": "shortpw@example.com",
        "password": "short",  # Too short password
        "full_name": "Short Password User",
        "is_active": True,
        "role": UserRole.USER
    }
    
    response = client.post("/api/users", json=user_data)
    assert response.status_code == 422
    assert "password" in response.json()["detail"].lower() 