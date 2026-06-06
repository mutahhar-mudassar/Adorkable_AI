"""
Adorkable AI - API Tests

Integration tests for FastAPI endpoints using httpx.
"""

import pytest
import httpx
from fastapi.testclient import TestClient

from backend.main import app
from backend.database import get_db, create_all_tables


# Create test client
client = TestClient(app)


class TestHealthEndpoints:
    """Test health check endpoints."""
    
    def test_root_endpoint(self):
        """Test root endpoint returns status."""
        response = client.get("/")
        
        assert response.status_code == 200
        assert "Adorkable AI" in response.json()["status"]
    
    def test_health_endpoint(self):
        """Test health check endpoint."""
        response = client.get("/health")
        
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
    
    def test_api_root(self):
        """Test API root endpoint."""
        response = client.get("/api/v1")
        
        assert response.status_code == 200
        data = response.json()
        assert "endpoints" in data


class TestAuthEndpoints:
    """Test authentication endpoints."""
    
    def test_register_success(self):
        """Test successful user registration."""
        # Use unique email to avoid conflicts
        import uuid
        email = f"test_{uuid.uuid4().hex[:8]}@example.com"
        
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": "testpassword123",
                "gender": "Female",
                "city": "London"
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["email"] == email
    
    def test_register_duplicate_email(self):
        """Test registration with duplicate email fails."""
        import uuid
        email = f"dup_{uuid.uuid4().hex[:8]}@example.com"
        
        # First registration
        client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": "testpassword123"
            }
        )
        
        # Second registration should fail
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": "testpassword123"
            }
        )
        
        assert response.status_code == 400
    
    def test_login_success(self):
        """Test successful login."""
        import uuid
        email = f"login_{uuid.uuid4().hex[:8]}@example.com"
        password = "testpassword123"
        
        # Register first
        client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": password
            }
        )
        
        # Login
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": email,
                "password": password
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
    
    def test_login_wrong_password(self):
        """Test login with wrong password fails."""
        import uuid
        email = f"wrong_{uuid.uuid4().hex[:8]}@example.com"
        
        # Register
        client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": "correctpassword"
            }
        )
        
        # Login with wrong password
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": email,
                "password": "wrongpassword"
            }
        )
        
        assert response.status_code == 401


class TestProtectedEndpoints:
    """Test protected endpoints require authentication."""
    
    def test_wardrobe_without_auth(self):
        """Test that wardrobe endpoint requires authentication."""
        response = client.get("/api/v1/wardrobe/")
        
        assert response.status_code == 403  # FastAPI returns 403 for missing auth
    
    def test_profile_without_auth(self):
        """Test that profile endpoint requires authentication."""
        response = client.get("/api/v1/profile/")
        
        assert response.status_code == 403


class TestResponseStructure:
    """Test API response structures."""
    
    def test_error_response_format(self):
        """Test that error responses have expected format."""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "nonexistent@example.com",
                "password": "wrongpassword"
            }
        )
        
        assert response.status_code == 401
        data = response.json()
        assert "detail" in data


# ✅ tests/test_api.py generated — Adorkable AI
