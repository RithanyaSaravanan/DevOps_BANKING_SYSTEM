from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, String, Float, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime, timedelta
import os, uuid
from fastapi import Depends
from prometheus_fastapi_instrumentator import Instrumentator

app = FastAPI(title="Fraud Detection Service", version="1.0.0")
Instrumentator().instrument(app).expose(app)

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://banking:banking123@localhost:5432/frauddb")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class FraudAlert(Base):
    __tablename__ = "fraud_alerts"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    account_id = Column(String, index=True)
    transaction_ref = Column(String)
    rule_triggered = Column(String)
    risk_score = Column(Float)
    is_blocked = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


Base.metadata.create_all(bind=engine)


class FraudCheckRequest(BaseModel):
    account_id: str
    amount: float
    transaction_type: str
    destination_account_id: str = ""
    ip_address: str = ""
    transaction_ref: str = ""


class FraudCheckResponse(BaseModel):
    allowed: bool
    risk_score: float
    triggered_rules: list
    message: str


RULES = {
    "high_amount": {"threshold": 10000, "score": 40, "message": "Amount exceeds high-value threshold"},
    "very_high_amount": {"threshold": 50000, "score": 80, "message": "Amount exceeds critical threshold"},
    "self_transfer": {"score": 20, "message": "Self transfer detected"},
}


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def calculate_risk(req: FraudCheckRequest, db: Session) -> FraudCheckResponse:
    score = 0.0
    triggered = []

    if req.amount > RULES["very_high_amount"]["threshold"]:
        score += RULES["very_high_amount"]["score"]
        triggered.append(RULES["very_high_amount"]["message"])
    elif req.amount > RULES["high_amount"]["threshold"]:
        score += RULES["high_amount"]["score"]
        triggered.append(RULES["high_amount"]["message"])

    if req.account_id == req.destination_account_id and req.destination_account_id:
        score += RULES["self_transfer"]["score"]
        triggered.append(RULES["self_transfer"]["message"])

    recent_window = datetime.utcnow() - timedelta(hours=1)
    recent_count = db.query(FraudAlert).filter(
        FraudAlert.account_id == req.account_id,
        FraudAlert.created_at >= recent_window
    ).count()
    if recent_count > 5:
        score += 30
        triggered.append(f"High frequency: {recent_count} checks in last hour")

    score = min(score, 100)
    allowed = score < 70

    if triggered:
        alert = FraudAlert(
            account_id=req.account_id,
            transaction_ref=req.transaction_ref,
            rule_triggered=", ".join(triggered),
            risk_score=score,
            is_blocked=not allowed
        )
        db.add(alert)
        db.commit()

    return FraudCheckResponse(
        allowed=allowed,
        risk_score=score,
        triggered_rules=triggered,
        message="Transaction approved" if allowed else "Transaction blocked due to fraud risk"
    )


@app.get("/health")
def health():
    return {"status": "healthy", "service": "fraud-service"}


@app.post("/check", response_model=FraudCheckResponse)
def check_fraud(req: FraudCheckRequest, db: Session = Depends(get_db)):
    return calculate_risk(req, db)


@app.get("/alerts/{account_id}")
def get_alerts(account_id: str):
    db = SessionLocal()
    try:
        alerts = db.query(FraudAlert).filter(FraudAlert.account_id == account_id).order_by(
            FraudAlert.created_at.desc()).limit(10).all()
        return [{"id": a.id, "rule": a.rule_triggered, "score": a.risk_score,
                 "blocked": a.is_blocked, "created_at": a.created_at} for a in alerts]
    finally:
        db.close()
