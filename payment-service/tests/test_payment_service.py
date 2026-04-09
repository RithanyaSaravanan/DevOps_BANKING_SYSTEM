import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_health_endpoint():
    with patch("main.engine"), patch("main.Base.metadata.create_all"):
        from main import app
        client = TestClient(app)
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["service"] == "payment-service"


def test_valid_card_luhn():
    with patch("main.engine"), patch("main.Base.metadata.create_all"):
        from main import validate_card
        assert validate_card("4532015112830366", "12/26", "123") is True
        assert validate_card("1234567890123456", "12/26", "123") is False
        assert validate_card("4532015112830366", "1226", "123") is False
        assert validate_card("4532015112830366", "12/26", "12") is False


def test_invalid_card_number_format():
    with patch("main.engine"), patch("main.Base.metadata.create_all"):
        from main import validate_card
        assert validate_card("not-a-card", "12/26", "123") is False
        assert validate_card("453201511283", "12/26", "123") is False
