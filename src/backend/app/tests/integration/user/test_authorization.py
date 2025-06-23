import pytest
from app.core.config.constants import UserRole


def test_admin_only_access(client, admin_token, normal_token):
    """Test that admin-only endpoints reject normal users."""
    # Test with admin token (should succeed)
    response = client.get(
        "/api/users",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    
    # Test with normal user token (should fail)
    response = client.get(
        "/api/users",
        headers={"Authorization": f"Bearer {normal_token}"}
    )
    assert response.status_code == 403
    assert "permission" in response.json()["detail"].lower()


def test_inactive_user_access(client, db):
    """Test that inactive users cannot login."""
    # Create inactive user
    user_data = {
        "email": "inactive@example.com",
        "password": "inactivepassword",
        "full_name": "Inactive User",
        "is_active": False,
        "role": UserRole.USER
    }
    
    # Register user
    client.post("/api/users", json=user_data)
    
    # Try to login with inactive user
    response = client.post("/api/login", data={
        "username": user_data["email"],
        "password": user_data["password"]
    })
    
    assert response.status_code == 400
    assert "inactive" in response.json()["detail"].lower()


def test_unauthorized_access(client):
    """Test accessing protected endpoints without a token."""
    response = client.get("/api/users/me")
    assert response.status_code == 401
    assert "not authenticated" in response.json()["detail"].lower()


def test_invalid_token_format(client):
    """Test using an improperly formatted token."""
    response = client.get(
        "/api/users/me",
        headers={"Authorization": "Bearer invalid_token_format"}
    )
    assert response.status_code == 401
    assert "could not validate" in response.json()["detail"].lower()


def test_role_based_permissions(client, db):
    """Test that different user roles have appropriate permissions."""
    # Create users with different roles
    roles_data = [
        {
            "email": "editor@example.com", 
            "password": "editorpassword",
            "full_name": "Editor User",
            "is_active": True,
            "role": UserRole.EDITOR
        },
        {
            "email": "viewer@example.com", 
            "password": "viewerpassword",
            "full_name": "Viewer User",
            "is_active": True,
            "role": UserRole.VIEWER
        }
    ]
    
    tokens = {}
    
    # Create users and get tokens
    for user_data in roles_data:
        client.post("/api/users", json=user_data)
        response = client.post("/api/login", data={
            "username": user_data["email"],
            "password": user_data["password"]
        })
        tokens[user_data["role"]] = response.json()["access_token"]
    
    # Test editor permissions (can view but not admin)
    editor_token = tokens[UserRole.EDITOR]
    
    # Should succeed - editors can view content
    response = client.get(
        "/api/content",
        headers={"Authorization": f"Bearer {editor_token}"}
    )
    assert response.status_code == 200
    
    # Should succeed - editors can create content
    response = client.post(
        "/api/content",
        headers={"Authorization": f"Bearer {editor_token}"},
        json={"title": "Test Content", "body": "Test body"}
    )
    assert response.status_code == 201
    
    # Should fail - editors cannot access admin endpoints
    response = client.get(
        "/api/admin/stats",
        headers={"Authorization": f"Bearer {editor_token}"}
    )
    assert response.status_code == 403
    
    # Test viewer permissions (view only)
    viewer_token = tokens[UserRole.VIEWER]
    
    # Should succeed - viewers can view content
    response = client.get(
        "/api/content",
        headers={"Authorization": f"Bearer {viewer_token}"}
    )
    assert response.status_code == 200
    
    # Should fail - viewers cannot create content
    response = client.post(
        "/api/content",
        headers={"Authorization": f"Bearer {viewer_token}"},
        json={"title": "Test Content", "body": "Test body"}
    )
    assert response.status_code == 403 