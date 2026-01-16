# EcomDash V2 API

AI-powered Shopify analytics dashboard backend API built with FastAPI.

## Features

- Real-time dashboard statistics and revenue charts
- AI-powered insights using DeepSeek via OpenRouter
- Shopify integration for orders, products, and customers
- Background job processing with ARQ
- PostgreSQL database with async support
- Redis caching and rate limiting

## Quick Start

```bash
# Install dependencies
pip install -e .

# Set up environment variables
cp .env.example .env

# Run development server
uvicorn app.main:app --reload
```

## API Endpoints

- `GET /health` - Health check
- `GET /health/ready` - Readiness probe (includes DB check)
- `GET /api/dashboard/stats` - Dashboard statistics
- `GET /api/dashboard/revenue-chart` - Revenue chart data
- `GET /api/insights` - AI-generated insights

## Environment Variables

See `.env.example` for required configuration.

## License

MIT
