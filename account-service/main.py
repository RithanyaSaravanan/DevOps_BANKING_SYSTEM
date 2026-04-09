from fastapi import FastAPI, HTTPException, Depends, Header
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, String, Float, DateTime, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime
import os, uuid, jwt

from prometheus_fastapi_instrumentator import Instrumentator

app = FastAPI(title="Account Service", version="1.0.0")
Instrumentator().instrument(app).expose(app)

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://banking:banking123@localhost:5432/accountdb")
SECRET_KEY = os.getenv("SECRET_KEY", "super-secret-key-change-in-prod")
ALGORITHM = "HS256"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Account(Base):
    __tablename__ = "accounts"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, index=True, nullable=False)
    account_number = Column(String, unique=True, nullable=False)
    account_type = Column(String, default="savings")
    balance = Column(Float, default=0.0)
    currency = Column(String, default="USD")
    is_active = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)


Base.metadata.create_all(bind=engine)


class CreateAccountRequest(BaseModel):
    account_type: str = "savings"
    initial_deposit: float = 0.0
    currency: str = "USD"


class DebitCreditRequest(BaseModel):
    amount: float
    description: str = ""


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
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")


def generate_account_number():
    import random
    return "ACC" + "".join([str(random.randint(0, 9)) for _ in range(10)])


@app.get("/health")
def health():
    return {"status": "healthy", "service": "account-service"}


@app.post("/accounts")
def create_account(req: CreateAccountRequest, user=Depends(get_current_user), db: Session = Depends(get_db)):
    account = Account(
        user_id=user["sub"],
        account_number=generate_account_number(),
        account_type=req.account_type,
        balance=req.initial_deposit,
        currency=req.currency
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    return {"account_id": account.id, "account_number": account.account_number, "balance": account.balance}


@app.get("/accounts")
def list_accounts(user=Depends(get_current_user), db: Session = Depends(get_db)):
    accounts = db.query(Account).filter(Account.user_id == user["sub"]).all()
    return [{"id": a.id, "account_number": a.account_number, "type": a.account_type,
             "balance": a.balance, "currency": a.currency} for a in accounts]


@app.get("/accounts/{account_id}/balance")
def get_balance(account_id: str, user=Depends(get_current_user), db: Session = Depends(get_db)):
    account = db.query(Account).filter(Account.id == account_id, Account.user_id == user["sub"]).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    return {"account_id": account_id, "balance": account.balance, "currency": account.currency}


@app.post("/accounts/{account_id}/debit")
def debit_account(account_id: str, req: DebitCreditRequest, db: Session = Depends(get_db)):
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    if account.balance < req.amount:
        raise HTTPException(status_code=400, detail="Insufficient funds")
    account.balance -= req.amount
    db.commit()
    return {"success": True, "new_balance": account.balance}


@app.post("/accounts/{account_id}/credit")
def credit_account(account_id: str, req: DebitCreditRequest, db: Session = Depends(get_db)):
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    account.balance += req.amount
    db.commit()
    return {"success": True, "new_balance": account.balance}


@app.get("/accounts/{account_id}/verify")
def verify_account(account_id: str, db: Session = Depends(get_db)):
    account = db.query(Account).filter(Account.id == account_id, Account.is_active == 1).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found or inactive")
    return {"valid": True, "account_id": account.id, "balance": account.balance}
