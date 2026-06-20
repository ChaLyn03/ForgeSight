# ForgeSight Developer Docs

This folder contains the operational and architecture guides for the ForgeSight MVP.

## Guides

### [QUICKSTART.md](./QUICKSTART.md)
Start here to run the full Docker Compose stack and submit a first inspection.
- Docker Compose setup
- Health checks
- Optional baseline model registration
- Submit first inspection
- View results

### [DEVELOPER.md](./DEVELOPER.md)
Complete development guide.
- Local setup (Python/Node)
- Project structure
- API overview
- Testing
- Common tasks
- Troubleshooting

### [ARCHITECTURE.md](./ARCHITECTURE.md)
Detailed system design notes.
- Component overview
- Data flow
- Model loading & inference
- Deployment guide
- Security & performance

### [../architecture/overview.md](../architecture/overview.md)
Short architecture summary for deployment and review.

### [../deployment/PRODUCTION.md](../deployment/PRODUCTION.md)
Production deployment plan and release checklist.

## Quick Links

**First time?**
→ Start with [QUICKSTART.md](./QUICKSTART.md)

**Setting up local environment?**
→ Read [DEVELOPER.md](./DEVELOPER.md)

**Understanding the system?**
→ Read [ARCHITECTURE.md](./ARCHITECTURE.md)

## Getting Help

- **API Docs:** http://localhost:8000/docs (Swagger)
- **MLflow UI:** http://localhost:5000
- **Web App:** http://localhost:3000
- **Container status:** `docker compose ps`
- **Logs:** `docker compose logs -f api worker`

## Technology Stack

### Backend
- **Framework:** FastAPI
- **Database:** PostgreSQL
- **ORM:** SQLAlchemy
- **Async:** Dramatiq + Redis
- **ML Registry:** MLflow
- **Inference:** PyTorch + ONNX

### Frontend
- **Framework:** React 18
- **Build Tool:** Vite
- **Language:** TypeScript
- **HTTP:** Axios

### Infrastructure
- **Containerization:** Docker + Docker Compose
- **CI/CD:** GitHub Actions
- **VCS:** Git

## Common Commands

### Start Full Stack
```bash
cp .env.example .env
docker compose up --build
```

### Check Health
```bash
curl -fsS http://localhost:8000/health/ready
curl -fsS http://localhost:5000/health
docker compose ps
```

### Run Tests
```bash
make test
```

### Run Deployment Smoke
```bash
make smoke
```

### Train Baseline Model
```bash
docker compose exec api python /app/ml/train_baseline.py --tracking-uri http://mlflow:5000
```

### View Logs
```bash
docker compose logs -f api
```

## Project Structure Overview

```
ForgeSight/
├── apps/
│   ├── api/          # FastAPI backend
│   ├── web/          # React frontend
│   └── worker/       # Dramatiq worker
├── ml/               # ML training scripts
├── docs/
│   ├── developer/    # This folder
│   └── architecture/ # System diagrams
├── docker-compose.yml
└── .github/workflows/ci.yml
```

## Next Steps

1. **[Start Here](./QUICKSTART.md)** - Get it running
2. **[Deep Dive](./DEVELOPER.md)** - Learn the details
3. **[Architecture](../architecture/overview.md)** - Review runtime topology
4. **[Deploy](../deployment/PRODUCTION.md)** - Plan production

---

**Last Updated:** 2026-06-19  
**Version:** 0.1.0 (MVP)
