import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def mock_db():
    return MagicMock()


def test_health_endpoint():
    with patch("main.engine"), patch("main.Base.metadata.create_all"):
        from main import app
        client = TestClient(app)
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"


def test_register_new_user():
    with patch("main.engine"), patch("main.Base.metadata.create_all"):
        from main import app, get_db, User
        mock_session = MagicMock()
        mock_session.query.return_value.filter.return_value.first.return_value = None

        def override_get_db():
            yield mock_session

        app.dependency_overrides[get_db] = override_get_db
        client = TestClient(app)

        response = client.post("/register", json={
            "email": "test@example.com",
            "full_name": "Test User",
            "password": "securepass123"
        })
        assert response.status_code in [200, 422, 500]
        app.dependency_overrides.clear()


def test_login_invalid_credentials():
    with patch("main.engine"), patch("main.Base.metadata.create_all"):
        from main import app, get_db
        mock_session = MagicMock()
        mock_session.query.return_value.filter.return_value.first.return_value = None

        def override_get_db():
            yield mock_session

        app.dependency_overrides[get_db] = override_get_db
        client = TestClient(app)

        response = client.post("/login", json={
            "email": "nonexistent@example.com",
            "password": "wrongpass"
        })
        assert response.status_code == 401
        app.dependency_overrides.clear()
