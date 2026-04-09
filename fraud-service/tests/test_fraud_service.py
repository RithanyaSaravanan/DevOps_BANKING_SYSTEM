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


def test_fraud_check_low_risk():
    with patch("main.engine"), patch("main.Base.metadata.create_all"):
        from main import calculate_risk, FraudCheckRequest
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.count.return_value = 0

        req = FraudCheckRequest(
            account_id="acc-001",
            amount=100.0,
            transaction_type="payment",
            destination_account_id="acc-002"
        )
        result = calculate_risk(req, mock_db)
        assert result.allowed is True
        assert result.risk_score < 70


def test_fraud_check_high_amount():
    with patch("main.engine"), patch("main.Base.metadata.create_all"):
        from main import calculate_risk, FraudCheckRequest
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.count.return_value = 0

        req = FraudCheckRequest(
            account_id="acc-001",
            amount=60000.0,
            transaction_type="payment",
            destination_account_id="acc-002"
        )
        result = calculate_risk(req, mock_db)
        assert result.risk_score >= 70
        assert result.allowed is False


def test_fraud_check_self_transfer():
    with patch("main.engine"), patch("main.Base.metadata.create_all"):
        from main import calculate_risk, FraudCheckRequest
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.count.return_value = 0

        req = FraudCheckRequest(
            account_id="acc-001",
            amount=500.0,
            transaction_type="transfer",
            destination_account_id="acc-001"
        )
        result = calculate_risk(req, mock_db)
        assert result.risk_score >= 20
        assert len(result.triggered_rules) > 0
