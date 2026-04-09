"""
Load Testing with Locust
Run: locust -f locustfile.py --host=http://localhost:8000

Then open http://localhost:8089 to launch the web UI.
Set users=50, spawn_rate=5, and run for ~2 minutes.
"""

from locust import HttpUser, task, between
import random
import json

TEST_USER = {
    "email": f"loadtest{random.randint(1000,9999)}@test.com",
    "full_name": "Load Test User",
    "password": "TestPass123!"
}


class BankingUser(HttpUser):
    wait_time = between(1, 3)
    token = None
    account_id = None

    def on_start(self):
        """Register and login on start."""
        # Register
        r = self.client.post("/api/users/register", json={
            "email": f"user{random.randint(10000,99999)}@test.com",
            "full_name": "Load Test User",
            "password": "TestPass123!"
        })
        if r.status_code == 200:
            data = r.json()
            self.token = data.get("access_token")

        # Create account
        if self.token:
            r2 = self.client.post(
                "/api/accounts/accounts",
                json={"account_type": "savings", "initial_deposit": 10000.0},
                headers={"Authorization": f"Bearer {self.token}"}
            )
            if r2.status_code == 200:
                self.account_id = r2.json().get("account_id")

    @task(3)
    def check_balance(self):
        if self.token and self.account_id:
            self.client.get(
                f"/api/accounts/accounts/{self.account_id}/balance",
                headers={"Authorization": f"Bearer {self.token}"},
                name="/api/accounts/balance"
            )

    @task(2)
    def list_accounts(self):
        if self.token:
            self.client.get(
                "/api/accounts/accounts",
                headers={"Authorization": f"Bearer {self.token}"},
                name="/api/accounts/list"
            )

    @task(1)
    def make_payment(self):
        if self.token and self.account_id:
            self.client.post(
                "/api/payments/pay",
                json={
                    "from_account_id": self.account_id,
                    "card_number": "4532015112830366",
                    "card_expiry": "12/26",
                    "card_cvv": "123",
                    "amount": round(random.uniform(10, 500), 2),
                    "merchant": "Test Store"
                },
                headers={"Authorization": f"Bearer {self.token}"},
                name="/api/payments/pay"
            )

    @task(1)
    def gateway_health(self):
        self.client.get("/health", name="/health")
