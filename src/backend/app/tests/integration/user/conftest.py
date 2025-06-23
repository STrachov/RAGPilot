import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlalchemy.pool import StaticPool
import sys
import os
#sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../src/backend")))
from app.core.models.user import User
from app.core.config.constants import UserRole
from app.main import app
from app.api.deps import get_db


@pytest.fixture(scope="function")
def db_engine():
    """Create a SQLite in-memory database for testing."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    yield engine
    SQLModel.metadata.drop_all(engine)


@pytest.fixture(scope="function")
def db(db_engine):
    """Create a new database session for each test."""
    with Session(db_engine) as session:
        yield session


@pytest.fixture(scope="function")
def client(db):
    """Create a FastAPI TestClient with the test database."""
    def override_get_db():
        try:
            yield db
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def admin_token(client):
    """Create an admin user and return their access token."""
    admin_data = {
        "email": "admin@example.com",
        "password": "adminpassword",
        "full_name": "Admin User",
        "is_active": True,
        "role": UserRole.ADMIN
    }
    
    # Register admin
    client.post("/api/users", json=admin_data)
    
    # Login and get token
    response = client.post("/api/login", data={
        "username": admin_data["email"],
        "password": admin_data["password"]
    })
    return response.json()["access_token"]


@pytest.fixture(scope="function")
def normal_token(client):
    """Create a normal user and return their access token."""
    user_data = {
        "email": "user@example.com",
        "password": "userpassword",
        "full_name": "Normal User",
        "is_active": True,
        "role": UserRole.USER
    }
    
    # Register user
    client.post("/api/users", json=user_data)
    
    # Login and get token
    response = client.post("/api/login", data={
        "username": user_data["email"],
        "password": user_data["password"]
    })
    return response.json()["access_token"] 