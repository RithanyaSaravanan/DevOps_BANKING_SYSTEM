#!/usr/bin/env python3
"""
End-to-End Demo Script
Tests the full banking flow: register → create account → pay → check history

Usage:
    pip install httpx
    python demo_flow.py
"""

import httpx
import json
import sys

BASE_URL = "http://localhost:8000"
HEADERS = {"Content-Type": "application/json"}


def print_step(step, msg):
    print(f"\n{'='*55}")
    print(f"  STEP {step}: {msg}")
    print(f"{'='*55}")


def print_result(label, data):
    print(f"  ✓ {label}:")
    print(f"    {json.dumps(data, indent=4, default=str)}")


def run_demo():
    print("\n🏦  BANKING PLATFORM — END-TO-END DEMO\n")

    with httpx.Client(base_url=BASE_URL, timeout=15.0) as client:

        # ── Step 1: Register ────────────────────────────────
        print_step(1, "Register new user")
        r = client.post("/api/users/register", json={
            "email": "alice@demo.com",
            "full_name": "Alice Demo",
            "password": "SecurePass123!"
        })
        if r.status_code != 200:
            print(f"  ✗ Register failed: {r.status_code} — {r.text}")
            sys.exit(1)
        token_data = r.json()
        token = token_data["access_token"]
        print_result("Registered", {"user_id": token_data["user_id"], "token": token[:30] + "..."})
        auth = {"Authorization": f"Bearer {token}"}

        # ── Step 2: Create account ──────────────────────────
        print_step(2, "Create savings account with $5,000")
        r = client.post("/api/accounts/accounts", json={
            "account_type": "savings",
            "initial_deposit": 5000.0,
            "currency": "USD"
        }, headers=auth)
        if r.status_code != 200:
            print(f"  ✗ Account creation failed: {r.status_code} — {r.text}")
            sys.exit(1)
        account = r.json()
        account_id = account["account_id"]
        print_result("Account created", account)

        # ── Step 3: Check balance ───────────────────────────
        print_step(3, "Check account balance")
        r = client.get(f"/api/accounts/accounts/{account_id}/balance", headers=auth)
        print_result("Balance", r.json())

        # ── Step 4: Make a payment ──────────────────────────
        print_step(4, "Make payment of $250 to Amazon")
        r = client.post("/api/payments/pay", json={
            "from_account_id": account_id,
            "card_number": "4532015112830366",
            "card_expiry": "12/26",
            "card_cvv": "123",
            "amount": 250.00,
            "merchant": "Amazon",
            "currency": "USD"
        }, headers=auth)
        payment = r.json()
        print_result("Payment result", payment)
        if payment.get("status") == "completed":
            print("  ✓ Payment APPROVED by fraud engine")
        elif payment.get("status") == "blocked":
            print("  ✗ Payment BLOCKED by fraud engine")

        # ── Step 5: Check balance after payment ────────────
        print_step(5, "Balance after payment")
        r = client.get(f"/api/accounts/accounts/{account_id}/balance", headers=auth)
        print_result("Updated balance", r.json())

        # ── Step 6: High-risk payment (fraud test) ──────────
        print_step(6, "Attempt high-risk payment of $60,000 (should be blocked)")
        r = client.post("/api/payments/pay", json={
            "from_account_id": account_id,
            "card_number": "4532015112830366",
            "card_expiry": "12/26",
            "card_cvv": "123",
            "amount": 60000.00,
            "merchant": "Suspicious Vendor"
        }, headers=auth)
        result = r.json()
        print_result("High-risk payment result", result)
        if result.get("status") == "blocked":
            print("  ✓ FRAUD DETECTED — Payment correctly blocked!")

        # ── Step 7: Gateway health ──────────────────────────
        print_step(7, "Gateway health check (all services)")
        r = client.get("/health")
        health = r.json()
        print_result("Service health", health)

        print(f"\n{'='*55}")
        print("  DEMO COMPLETE ✓")
        print(f"{'='*55}\n")


if __name__ == "__main__":
    run_demo()
