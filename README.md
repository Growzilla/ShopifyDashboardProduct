# EcomDash V2 - Superior Shopify AI Dashboard

A production-ready, modular Shopify AI analytics dashboard rebuilt with modern architecture.

## Architecture Highlights

### Backend (FastAPI)
- **Modular Structure**: Clean separation into routers, services, repositories, schemas
- **Type-Safe**: Full Pydantic v2 models with SQLAlchemy 2.0 async
- **Production-Ready**: Structured logging, error handling, health checks
- **AI-Powered**: Insights engine with 5 core analytics modules

### Frontend (React Router 7)
- **Shopify Native**: Polaris components, App Bridge integration
- **Modern Stack**: React 18, TanStack Query, TypeScript
- **Optimized**: Code splitting, SSR-ready

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 20+
- PostgreSQL 15+
- Docker (optional)

### Option 1: Docker Compose (Recommended)

```bash
cd ecomdash-v2
cp backend/.env.example backend/.env
# Edit .env with your credentials

docker-compose up -d
```

Access:
- Frontend: http://localhost:3000
- API: http://localhost:8000
- API Docs: http://localhost:8000/docs

### Option 2: Manual Setup

**Backend:**
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
# Edit .env with your credentials

uvicorn app.main:app --reload
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

## Project Structure

```
ecomdash-v2/
├── backend/
│   ├── app/
│   │   ├── core/          # Config, database, security, logging
│   │   ├── models/        # SQLAlchemy models
│   │   ├── schemas/       # Pydantic schemas
│   │   ├── repositories/  # Data access layer
│   │   ├── services/      # Business logic
│   │   ├── routers/       # API endpoints
│   │   ├── middleware/    # Request handling
│   │   └── agents/        # AI agents
│   ├── tests/             # pytest tests
│   └── pyproject.toml
├── frontend/
│   ├── app/
│   │   ├── routes/        # Page components
│   │   ├── components/    # Reusable components
│   │   ├── services/      # API client
│   │   ├── types/         # TypeScript types
│   │   └── styles/        # Global styles
│   └── package.json
├── infra/
│   ├── docker/
│   └── ci/
└── docker-compose.yml
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/health/ready` | GET | Readiness probe |
| `/api/shops` | POST | Create/update shop |
| `/api/shops/{domain}` | GET | Get shop details |
| `/api/shops/{domain}` | PATCH | Update settings |
| `/api/insights` | GET | List insights (paginated) |
| `/api/insights/{id}/dismiss` | POST | Dismiss insight |
| `/api/dashboard/stats` | GET | Dashboard statistics |
| `/api/dashboard/summary` | GET | Full dashboard data |

## AI Insights

The system generates 5 types of insights:

1. **Under-stocked Winners** - High-velocity products with low inventory
2. **Over-stock Slow Movers** - Dead stock detection
3. **Coupon Cannibalization** - Discount overuse on popular items
4. **Traffic-Sales Mismatch** - High traffic, low conversion products
5. **Checkout Drop-off** - Declining conversion rates

## Testing

**Backend:**
```bash
cd backend
pytest -v --cov=app
```

**Frontend:**
```bash
cd frontend
npm run test
npm run test:e2e  # Playwright E2E tests
```

## Deployment

### Render.com
Use the provided `docker-compose.yml` as a blueprint or deploy services individually.

### Environment Variables
See `backend/.env.example` for all required configuration.

## Key Improvements Over V1

| Feature | V1 | V2 |
|---------|----|----|
| Backend Architecture | Monolithic 1300+ line main.py | Modular routers/services/repos |
| Type Safety | Partial | Full Pydantic v2 + SQLAlchemy 2.0 |
| Frontend | Multiple duplicate apps | Unified React Router 7 |
| Testing | None | pytest + vitest + Playwright |
| Logging | Basic print/logging | Structured JSON (structlog) |
| Error Handling | Scattered try/catch | Centralized middleware |
| Database | Raw SQLAlchemy | Repository pattern with DI |
| DevOps | Manual | Docker Compose + CI/CD ready |

## License

MIT
