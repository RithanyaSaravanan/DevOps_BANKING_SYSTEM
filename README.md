# 🏦 Cloud-Native Digital Banking & Payment Gateway Platform

A production-grade microservices banking platform with CI/CD, Kubernetes, Canary deployments, and monitoring.

---

## 🧩 Architecture

```
Client → API Gateway (port 8000)
              ├── user-service        (register, login, JWT)
              ├── account-service     (accounts, balances)
              ├── transaction-service (transfers, history)
              ├── payment-service     (card payments) → fraud-service
              └── fraud-service       (rule-based risk scoring)
```

Each service has its own PostgreSQL database (database-per-service pattern).

---

## 🚀 Quick Start (Docker Compose)

### Prerequisites
- Docker Desktop (or Docker + Docker Compose)
- Python 3.10+ (for running tests/demo scripts)

### 1. Clone and start
```bash
git clone <your-repo>
cd banking-platform
docker compose up --build
```

### 2. Verify all services are healthy
```bash
curl http://localhost:8000/health
```

### 3. Run the end-to-end demo
```bash
pip install httpx
python scripts/demo_flow.py
```

### 4. Open API docs
| Service            | URL                             |
|--------------------|---------------------------------|
| Gateway            | http://localhost:8000/docs      |
| User Service       | http://localhost:8001/docs      |
| Account Service    | http://localhost:8002/docs      |
| Transaction Service| http://localhost:8003/docs      |
| Fraud Service      | http://localhost:8004/docs      |
| Payment Service    | http://localhost:8005/docs      |
| Prometheus         | http://localhost:9090           |
| Grafana            | http://localhost:3000 (admin/admin123) |

---

## 🔑 Key API Flows

### Register & Login
```bash
# Register
curl -X POST http://localhost:8000/api/users/register \
  -H "Content-Type: application/json" \
  -d '{"email":"alice@bank.com","full_name":"Alice","password":"Pass123!"}'

# Login
curl -X POST http://localhost:8000/api/users/login \
  -H "Content-Type: application/json" \
  -d '{"email":"alice@bank.com","password":"Pass123!"}'
```

### Create Account & Make Payment
```bash
TOKEN="<jwt_token_from_login>"

# Create account
curl -X POST http://localhost:8000/api/accounts/accounts \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"account_type":"savings","initial_deposit":5000}'

# Make payment (use Luhn-valid test card: 4532015112830366)
curl -X POST http://localhost:8000/api/payments/pay \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "from_account_id":"<account_id>",
    "card_number":"4532015112830366",
    "card_expiry":"12/26",
    "card_cvv":"123",
    "amount":250.00,
    "merchant":"Amazon"
  }'
```

---

## 🧪 Testing

### Unit tests
```bash
pip install pytest fastapi httpx sqlalchemy passlib pyjwt psycopg2-binary
pytest user-service/tests/ -v
pytest payment-service/tests/ -v
pytest fraud-service/tests/ -v
```

### Load tests
```bash
pip install locust
locust -f scripts/locustfile.py --host=http://localhost:8000
# Open http://localhost:8089
```

---

## ☸️ Kubernetes Deployment

### Prerequisites
- kubectl configured
- Kubernetes cluster (minikube / k3s / EKS / GKE)
- Docker images pushed to DockerHub

### 1. Update image names
Edit all `image:` fields in `k8s/base/*.yaml` to point to your DockerHub images:
```
your-dockerhub/user-service:latest
your-dockerhub/payment-service:v1
...
```

### 2. Deploy
```bash
chmod +x scripts/deploy.sh
./scripts/deploy.sh banking
```

### 3. Canary deployment
```bash
# Deploy payment-service v2 (10% traffic)
kubectl apply -f k8s/canary/payment-canary.yaml -n banking

# Monitor in Grafana, then promote
kubectl scale deployment payment-service-v2 --replicas=9 -n banking
kubectl scale deployment payment-service-v1 --replicas=1 -n banking

# Full promotion
kubectl scale deployment payment-service-v2 --replicas=2 -n banking
kubectl delete deployment payment-service-v1 -n banking
```

---

## 🔁 CI/CD Pipeline (Jenkins)

The `jenkins/Jenkinsfile` defines these stages:

```
Checkout → Unit Tests → Security Scan (Trivy) → Build Images →
Scan Images → Push to DockerHub → Deploy to K8s → Verify Rollout
```

### Jenkins Setup
1. Install plugins: Docker Pipeline, Kubernetes CLI, Git
2. Add credentials:
   - `dockerhub-credentials` (Username/Password)
   - `kubeconfig` (Secret File — your `~/.kube/config`)
3. Create a Pipeline job pointing to `jenkins/Jenkinsfile`

---

## 📊 Monitoring

### Prometheus
- Scrapes all 6 services every 15s
- Access: http://localhost:9090

### Grafana
- Pre-configured Prometheus datasource
- Login: admin / admin123
- Create dashboards for:
  - `http_requests_total` — request rates per service
  - `http_request_duration_seconds` — latency percentiles
  - Payment success/failure rates
  - Pod CPU/memory

---

## 🔐 Security

- **JWT Auth**: All endpoints protected; tokens validated at gateway + service level
- **Card validation**: Luhn algorithm check before processing
- **Fraud detection**: Rule-based engine scores every transaction
- **Trivy**: Container vulnerability scanning in CI pipeline
- **K8s Secrets**: DB credentials and JWT secret stored as Kubernetes Secrets

---

## 📁 Project Structure

```
banking-platform/
├── user-service/           FastAPI — registration & JWT login
├── account-service/        FastAPI — account CRUD & balance
├── transaction-service/    FastAPI — fund transfers
├── payment-service/        FastAPI — card payment processing
├── fraud-service/          FastAPI — rule-based fraud detection
├── gateway/                FastAPI — reverse proxy API gateway
├── k8s/
│   ├── base/               Deployments, Services, HPA, Secrets
│   └── canary/             Canary deployment for payment-service v2
├── jenkins/
│   └── Jenkinsfile         Full CI/CD pipeline
├── monitoring/
│   ├── prometheus/         prometheus.yml scrape config
│   └── grafana/            Datasource provisioning
├── scripts/
│   ├── demo_flow.py        End-to-end demo script
│   ├── locustfile.py       Load testing
│   └── deploy.sh           K8s deploy helper
└── docker-compose.yml      Full local environment
```

---

## 💬 Interview Explanation

> "I built a cloud-native digital banking and payment gateway platform using microservices architecture. Each service — user, account, transaction, payment, and fraud — is independently deployable, containerized with Docker, and deployed to Kubernetes. I implemented a CI/CD pipeline in Jenkins that runs unit tests, Trivy security scans, builds and pushes Docker images, then deploys to Kubernetes with rollout verification. I used a Canary deployment strategy for the payment service — routing 10% of traffic to v2 while monitoring Grafana dashboards before promoting. The fraud service uses rule-based scoring to block high-risk transactions in real time before they hit the payment flow."
