from fastapi import FastAPI, HTTPException, Depends, Header
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, String, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime
import os, uuid, jwt, httpx

from prometheus_fastapi_instrumentator import Instrumentator

app = FastAPI(title="Transaction Service", version="1.0.0")
Instrumentator().instrument(app).expose(app)

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://banking:banking123@localhost:5432/transactiondb")
SECRET_KEY = os.getenv("SECRET_KEY", "super-secret-key-change-in-prod")
ACCOUNT_SERVICE_URL = os.getenv("ACCOUNT_SERVICE_URL", "http://account-service:8000")
ALGORITHM = "HS256"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    from_account_id = Column(String, index=True)
    to_account_id = Column(String, index=True)
    amount = Column(Float, nullable=False)
    currency = Column(String, default="USD")
    transaction_type = Column(String, nullable=False)
    status = Column(String, default="pending")
    description = Column(String, default="")
    reference_id = Column(String, unique=True, default=lambda: str(uuid.uuid4()))
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)


Base.metadata.create_all(bind=engine)


class FundTransferRequest(BaseModel):
    from_account_id: str
    to_account_id: str
    amount: float
    description: str = "Fund transfer"
    currency: str = "USD"


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


@app.get("/health")
def health():
    return {"status": "healthy", "service": "transaction-service"}


@app.post("/transfer")
async def transfer_funds(req: FundTransferRequest, user=Depends(get_current_user), db: Session = Depends(get_db)):
    if req.amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")

    txn = Transaction(
        from_account_id=req.from_account_id,
        to_account_id=req.to_account_id,
        amount=req.amount,
        currency=req.currency,
        transaction_type="transfer",
        status="pending",
        description=req.description
    )
    db.add(txn)
    db.commit()

    async with httpx.AsyncClient() as client:
        try:
            debit_resp = await client.post(
                f"{ACCOUNT_SERVICE_URL}/accounts/{req.from_account_id}/debit",
                json={"amount": req.amount, "description": req.description}
            )
            if debit_resp.status_code != 200:
                txn.status = "failed"
                db.commit()
                raise HTTPException(status_code=400, detail=debit_resp.json().get("detail", "Debit failed"))

            credit_resp = await client.post(
                f"{ACCOUNT_SERVICE_URL}/accounts/{req.to_account_id}/credit",
                json={"amount": req.amount, "description": req.description}
            )
            if credit_resp.status_code != 200:
                await client.post(
                    f"{ACCOUNT_SERVICE_URL}/accounts/{req.from_account_id}/credit",
                    json={"amount": req.amount, "description": "Reversal"}
                )
                txn.status = "failed"
                db.commit()
                raise HTTPException(status_code=400, detail="Credit failed, debit reversed")

        except httpx.RequestError as e:
            txn.status = "failed"
            db.commit()
            raise HTTPException(status_code=503, detail=f"Service unavailable: {str(e)}")

    txn.status = "completed"
    txn.completed_at = datetime.utcnow()
    db.commit()
    db.refresh(txn)
    return {"transaction_id": txn.id, "reference_id": txn.reference_id, "status": txn.status, "amount": txn.amount}


@app.get("/history/{account_id}")
def get_history(account_id: str, limit: int = 20, user=Depends(get_current_user), db: Session = Depends(get_db)):
    from sqlalchemy import or_
    txns = db.query(Transaction).filter(
        or_(Transaction.from_account_id == account_id, Transaction.to_account_id == account_id)
    ).order_by(Transaction.created_at.desc()).limit(limit).all()
    return [{"id": t.id, "type": t.transaction_type, "amount": t.amount,
             "status": t.status, "created_at": t.created_at, "description": t.description} for t in txns]


@app.post("/record")
def record_transaction(from_account_id: str, to_account_id: str, amount: float,
                        txn_type: str, status: str, db: Session = Depends(get_db)):
    txn = Transaction(
        from_account_id=from_account_id, to_account_id=to_account_id,
        amount=amount, transaction_type=txn_type, status=status
    )
    db.add(txn)
    db.commit()
    db.refresh(txn)
    return {"transaction_id": txn.id, "status": txn.status}
