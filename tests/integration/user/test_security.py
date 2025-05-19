import pytest
import time


def test_brute_force_protection(client, monkeypatch):
    """Test protection against brute force attacks."""
    # Mock rate limiter to have a lower threshold for testing
    from app.api.endpoints.login import router
    
    # Store the original dependency
    original_deps = router.dependencies.copy()
    
    # Replace with a test dependency that has a lower threshold
    def mock_rate_limiter():
        # Here you would replace the actual rate limiter with one 
        # that has a lower threshold for testing purposes
        pass
    
    # Patch the router
    monkeypatch.setattr(router, "dependencies", [])
    
    # Attempt multiple failed logins
    for _ in range(6):  # Assuming 5 is the threshold
        client.post("/api/login", data={
            "username": "user@example.com",
            "password": "wrongpassword"
        })
    
    # Next attempt should be rate limited
    response = client.post("/api/login", data={
        "username": "user@example.com",
        "password": "wrongpassword"
    })
    
    # Restore original dependencies
    monkeypatch.setattr(router, "dependencies", original_deps)
    
    assert response.status_code == 429
    assert "too many" in response.json()["detail"].lower()


def test_csrf_protection(client, normal_token, monkeypatch):
    """Test CSRF protection."""
    # This test assumes the app is using CSRF protection middleware
    # Mock CSRF verification to fail
    from app.api.deps import get_current_user
    
    original_get_current_user = get_current_user
    
    async def mock_get_current_user_csrf_check(token: str):
        # Simulate a CSRF check failure
        raise ValueError("CSRF token validation failed")
    
    monkeypatch.setattr("app.api.deps.get_current_user", mock_get_current_user_csrf_check)
    
    headers = {
        "Authorization": f"Bearer {normal_token}",
        "X-CSRF-Token": "invalid-token"
    }
    
    response = client.post(
        "/api/users/me/change-password",
        headers=headers,
        json={"current_password": "userpassword", "new_password": "newpassword123"}
    )
    
    # Restore original function
    monkeypatch.setattr("app.api.deps.get_current_user", original_get_current_user)
    
    assert response.status_code == 403
    assert "csrf" in response.json()["detail"].lower()


def test_secure_headers(client):
    """Test that security headers are properly set."""
    response = client.get("/api/health")
    headers = response.headers
    
    # Check for common security headers
    assert "X-Content-Type-Options" in headers
    assert headers["X-Content-Type-Options"] == "nosniff"
    
    assert "X-Frame-Options" in headers
    assert headers["X-Frame-Options"] == "DENY"
    
    assert "X-XSS-Protection" in headers
    assert headers["X-XSS-Protection"] == "1; mode=block"
    
    assert "Content-Security-Policy" in headers


def test_password_hashing(client, db):
    """Test that passwords are properly hashed and not stored in plaintext."""
    # Create a user
    user_data = {
        "email": "hashtest@example.com",
        "password": "securepassword123",
        "full_name": "Hash Test User",
        "is_active": True
    }
    
    client.post("/api/users", json=user_data)
    
    # Query the database directly to check password storage
    from app.core.models.user import User
    from sqlmodel import select
    
    user = db.exec(select(User).where(User.email == user_data["email"])).first()
    
    # Ensure password is not stored in plaintext
    assert user.hashed_password != user_data["password"]
    assert len(user.hashed_password) > 20  # Reasonable length for a hash
    
    # Verify that original password verifies against the hash
    from app.core.security import verify_password
    assert verify_password(user_data["password"], user.hashed_password)


def test_session_timeout(client, normal_token, monkeypatch):
    """Test that sessions timeout properly."""
    # This test would simulate a token with a timeout mechanism
    from app.core.security import create_access_token
    
    # Create a token with a very short timeout
    short_token = create_access_token(
        subject="user@example.com",
        expires_delta=0.01  # Very short expiration
    )
    
    # Wait for token to expire
    time.sleep(0.02)
    
    # Try to use expired token
    response = client.get(
        "/api/users/me",
        headers={"Authorization": f"Bearer {short_token}"}
    )
    
    assert response.status_code == 401
    assert "expired" in response.json()["detail"].lower() 