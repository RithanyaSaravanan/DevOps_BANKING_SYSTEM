from fastapi import FastAPI, HTTPException, Depends, Header
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, String, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime
import os, uuid, jwt, httpx, re

from prometheus_fastapi_instrumentator import Instrumentator

app = FastAPI(title="Payment Service", version="1.0.0")
Instrumentator().instrument(app).expose(app)

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://banking:banking123@localhost:5432/paymentdb")
SECRET_KEY = os.getenv("SECRET_KEY", "super-secret-key-change-in-prod")
FRAUD_SERVICE_URL = os.getenv("FRAUD_SERVICE_URL", "http://fraud-service:8000")
TRANSACTION_SERVICE_URL = os.getenv("TRANSACTION_SERVICE_URL", "http://transaction-service:8000")
ACCOUNT_SERVICE_URL = os.getenv("ACCOUNT_SERVICE_URL", "http://account-service:8000")
ALGORITHM = "HS256"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Payment(Base):
    __tablename__ = "payments"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, index=True)
    from_account_id = Column(String)
    card_last_four = Column(String)
    amount = Column(Float)
    currency = Column(String, default="USD")
    merchant = Column(String, default="")
    status = Column(String, default="pending")
    fraud_score = Column(Float, default=0.0)
    reference = Column(String, unique=True, default=lambda: str(uuid.uuid4()))
    created_at = Column(DateTime, default=datetime.utcnow)


Base.metadata.create_all(bind=engine)


class PaymentRequest(BaseModel):
    from_account_id: str
    card_number: str
    card_expiry: str
    card_cvv: str
    amount: float
    merchant: str = "Unknown"
    currency: str = "USD"


class PaymentResponse(BaseModel):
    payment_id: str
    reference: str
    status: str
    amount: float
    message: str


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing token")
    token = authorization.split(" ")[1]
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")


def validate_card(card_number: str, expiry: str, cvv: str) -> bool:
    clean = card_number.replace(" ", "").replace("-", "")
    if not re.match(r"^\d{16}$", clean):
        return False
    if not re.match(r"^\d{2}/\d{2}$", expiry):
        return False
    if not re.match(r"^\d{3,4}$", cvv):
        return False
    total, alternate = 0, False
    for digit in reversed(clean):
        n = int(digit)
        if alternate:
            n *= 2
            if n > 9:
                n -= 9
        total += n
        alternate = not alternate
    return total % 10 == 0


@app.get("/health")
def health():
    return {"status": "healthy", "service": "payment-service"}


@app.post("/pay", response_model=PaymentResponse)
async def process_payment(req: PaymentRequest, user=Depends(get_current_user), db: Session = Depends(get_db)):
    card_clean = req.card_number.replace(" ", "").replace("-", "")
    if not validate_card(req.card_number, req.card_expiry, req.card_cvv):
        raise HTTPException(status_code=400, detail="Invalid card details")

    payment = Payment(
        user_id=user["sub"],
        from_account_id=req.from_account_id,
        card_last_four=card_clean[-4:],
        amount=req.amount,
        currency=req.currency,
        merchant=req.merchant,
        status="pending"
    )
    db.add(payment)
    db.commit()

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            fraud_resp = await client.post(f"{FRAUD_SERVICE_URL}/check", json={
                "account_id": req.from_account_id,
                "amount": req.amount,
                "transaction_type": "payment",
                "transaction_ref": payment.reference
            })
            fraud_data = fraud_resp.json()
            payment.fraud_score = fraud_data.get("risk_score", 0)

            if not fraud_data.get("allowed", True):
                payment.status = "blocked"
                db.commit()
                return PaymentResponse(
                    payment_id=payment.id, reference=payment.reference,
                    status="blocked", amount=req.amount,
                    message=fraud_data.get("message", "Blocked by fraud detection")
                )
        except Exception:
            pass

        try:
            debit_resp = await client.post(
                f"{ACCOUNT_SERVICE_URL}/accounts/{req.from_account_id}/debit",
                json={"amount": req.amount, "description": f"Payment to {req.merchant}"}
            )
            if debit_resp.status_code != 200:
                payment.status = "failed"
                db.commit()
                raise HTTPException(status_code=400, detail="Insufficient funds")
        except httpx.RequestError:
            payment.status = "failed"
            db.commit()
            raise HTTPException(status_code=503, detail="Account service unavailable")

    payment.status = "completed"
    db.commit()
    db.refresh(payment)

    return PaymentResponse(
        payment_id=payment.id, reference=payment.reference,
        status="completed", amount=req.amount,
        message=f"Payment of {req.amount} {req.currency} to {req.merchant} successful"
    )


@app.get("/payments/{user_id}")
def get_payment_history(user_id: str, user=Depends(get_current_user), db: Session = Depends(get_db)):
    payments = db.query(Payment).filter(Payment.user_id == user_id).order_by(
        Payment.created_at.desc()).limit(20).all()
    return [{"id": p.id, "amount": p.amount, "merchant": p.merchant,
             "status": p.status, "created_at": p.created_at, "card_last_four": p.card_last_four} for p in payments]
