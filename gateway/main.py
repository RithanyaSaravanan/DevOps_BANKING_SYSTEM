from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import httpx
import os

from prometheus_fastapi_instrumentator import Instrumentator

app = FastAPI(title="API Gateway", version="1.0.0")
Instrumentator().instrument(app).expose(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SERVICES = {
    "user": os.getenv("USER_SERVICE_URL", "http://user-service:8000"),
    "account": os.getenv("ACCOUNT_SERVICE_URL", "http://account-service:8000"),
    "transaction": os.getenv("TRANSACTION_SERVICE_URL", "http://transaction-service:8000"),
    "payment": os.getenv("PAYMENT_SERVICE_URL", "http://payment-service:8000"),
    "fraud": os.getenv("FRAUD_SERVICE_URL", "http://fraud-service:8000"),
}

ROUTES = {
    "/api/users": "user",
    "/api/accounts": "account",
    "/api/transactions": "transaction",
    "/api/payments": "payment",
    "/api/fraud": "fraud",
}


async def proxy_request(service_url: str, path: str, request: Request):
    async with httpx.AsyncClient(timeout=30.0) as client:
        url = f"{service_url}{path}"
        headers = dict(request.headers)
        headers.pop("host", None)
        body = await request.body()
        resp = await client.request(
            method=request.method,
            url=url,
            headers=headers,
            content=body,
            params=dict(request.query_params)
        )
        return JSONResponse(content=resp.json(), status_code=resp.status_code)


@app.get("/health")
async def health():
    status = {}
    async with httpx.AsyncClient(timeout=5.0) as client:
        for name, url in SERVICES.items():
            try:
                r = await client.get(f"{url}/health")
                status[name] = "healthy" if r.status_code == 200 else "unhealthy"
            except Exception:
                status[name] = "unreachable"
    return {"gateway": "healthy", "services": status}


@app.api_route("/api/users/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def user_proxy(path: str, request: Request):
    return await proxy_request(SERVICES["user"], f"/{path}", request)


@app.api_route("/api/accounts/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def account_proxy(path: str, request: Request):
    return await proxy_request(SERVICES["account"], f"/{path}", request)


@app.api_route("/api/transactions/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def transaction_proxy(path: str, request: Request):
    return await proxy_request(SERVICES["transaction"], f"/{path}", request)


@app.api_route("/api/payments/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def payment_proxy(path: str, request: Request):
    return await proxy_request(SERVICES["payment"], f"/{path}", request)


@app.api_route("/api/fraud/{path:path}", methods=["GET", "POST"])
async def fraud_proxy(path: str, request: Request):
    return await proxy_request(SERVICES["fraud"], f"/{path}", request)


@app.get("/")
def root():
    return {"message": "Banking Platform API Gateway", "version": "1.0.0",
            "docs": "/docs", "services": list(SERVICES.keys())}
