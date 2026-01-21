# SafetySync Analytics Platform - Setup Guide

This guide will walk you through setting up the project locally for development.

## Prerequisites

Before you begin, ensure you have the following installed:

- **Docker** and **Docker Compose** (v2.0+)
- **Python** 3.11 or higher (for local development)
- **Node.js** 18+ and npm (for frontend development)
- **Git**

## Quick Start with Docker (Recommended)

The easiest way to get started is using Docker Compose, which sets up all services automatically.

### 1. Clone the Repository

```bash
git clone https://github.com/TshegofatsoDitshego/safety-analytics.git
cd safety-analytics
```

### 2. Create Environment File

```bash
cp backend/.env.example backend/.env
```

You can use the default values for local development. The `.env` file contains database credentials and configuration settings.

### 3. Start All Services

```bash
docker-compose up -d
```

This will start:
- TimescaleDB (PostgreSQL with time-series extensions)
- Redis (for task queue and caching)
- FastAPI backend
- Celery worker (background tasks)
- Celery beat (scheduled tasks)
- React frontend

### 4. Initialize the Database

```bash
docker-compose exec api python scripts/init_db.py
```

This creates the database schema and adds sample equipment.

### 5. Generate Test Data

```bash
# Generate 7 days of historical data
docker-compose exec api python scripts/simulate_sensors.py --mode historical --days 7

# Or start a real-time stream (optional)
docker-compose exec api python scripts/simulate_sensors.py --mode realtime --duration 60
```

### 6. Access the Application

- **Frontend**: http://localhost:3000
- **API Documentation**: http://localhost:8000/docs
- **API Health Check**: http://localhost:8000/health

## Local Development Setup (Without Docker)

If you prefer to run services locally for development:

### Backend Setup

1. **Set up Python virtual environment**

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. **Install dependencies**

```bash
pip install -r requirements.txt
```

3. **Start PostgreSQL and Redis**

You'll need to install and run PostgreSQL (with TimescaleDB extension) and Redis locally, or use Docker just for these services:

```bash
docker run -d -p 5432:5432 \
  -e POSTGRES_DB=safety_analytics \
  -e POSTGRES_USER=safety_admin \
  -e POSTGRES_PASSWORD=safety_dev_2024 \
  timescale/timescaledb:latest-pg15

docker run -d -p 6379:6379 redis:7-alpine
```

4. **Update .env file**

```bash
cp .env.example .env
# Update DATABASE_URL and REDIS_URL to point to localhost
```

5. **Initialize database**

```bash
python scripts/init_db.py
```

6. **Run the API server**

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

7. **Run Celery worker (in another terminal)**

```bash
celery -A app.tasks.celery_app worker --loglevel=info
```

8. **Run Celery beat (in another terminal)**

```bash
celery -A app.tasks.celery_app beat --loglevel=info
```

### Frontend Setup

1. **Install dependencies**

```bash
cd frontend
npm install
```

2. **Start development server**

```bash
npm run dev
```

Frontend will be available at http://localhost:3000

## Running Tests

### Backend Tests

```bash
cd backend
pytest tests/ -v --cov=app
```

### With coverage report

```bash
pytest tests/ -v --cov=app --cov-report=html
# Open htmlcov/index.html in browser
```

## Common Commands

### Docker Commands

```bash
# View logs
docker-compose logs -f

# View logs for specific service
docker-compose logs -f api

# Restart services
docker-compose restart

# Stop all services
docker-compose down

# Stop and remove volumes (fresh start)
docker-compose down -v

# Rebuild images
docker-compose build --no-cache
```

### Database Commands

```bash
# Connect to database
docker-compose exec timescaledb psql -U safety_admin -d safety_analytics

# Run migrations (when added)
docker-compose exec api alembic upgrade head

# Create new migration
docker-compose exec api alembic revision --autogenerate -m "description"
```

### Monitoring

```bash
# Check Celery tasks
docker-compose exec api celery -A app.tasks.celery_app inspect active

# Check Celery scheduled tasks
docker-compose exec api celery -A app.tasks.celery_app inspect scheduled
```

## Project Structure

```
safety-analytics/
├── backend/
│   ├── app/
│   │   ├── api/              # API endpoints
│   │   │   ├── ingestion.py  # Data ingestion endpoints
│   │   │   ├── analytics.py  # Analytics endpoints
│   │   │   ├── equipment.py  # Equipment management
│   │   │   └── reports.py    # Report generation
│   │   ├── core/             # Core configuration
│   │   │   ├── config.py     # Settings management
│   │   │   └── database.py   # Database connection
│   │   ├── models/           # Database models
│   │   │   └── database.py   # SQLAlchemy models
│   │   ├── services/         # Business logic
│   │   │   ├── ingestion.py  # Data pipeline
│   │   │   └── analytics.py  # Analytics engine
│   │   ├── tasks/            # Background tasks
│   │   │   └── celery_app.py # Celery tasks
│   │   └── main.py           # FastAPI app entry
│   ├── scripts/
│   │   ├── init_db.py        # Database initialization
│   │   └── simulate_sensors.py # Data simulator
│   ├── tests/                # Test suite
│   ├── Dockerfile
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   ├── package.json
│   └── Dockerfile
├── docker-compose.yml
├── README.md
└── SETUP_GUIDE.md
```

## Troubleshooting

### Database Connection Issues

If you can't connect to the database:

1. Ensure PostgreSQL is running: `docker-compose ps timescaledb`
2. Check logs: `docker-compose logs timescaledb`
3. Verify DATABASE_URL in `.env` is correct
4. Try connecting manually: `psql postgresql://safety_admin:safety_dev_2024@localhost:5432/safety_analytics`

### Port Already in Use

If you get "port already in use" errors:

```bash
# Find what's using the port (e.g., 8000)
lsof -i :8000

# Kill the process
kill -9 <PID>

# Or change the port in docker-compose.yml
```

### Celery Tasks Not Running

1. Check if Celery worker is running: `docker-compose ps celery_worker`
2. View Celery logs: `docker-compose logs celery_worker`
3. Ensure Redis is running: `docker-compose ps redis`

### Missing Dependencies

```bash
# Rebuild Docker images
docker-compose build --no-cache

# Or reinstall Python packages
pip install -r requirements.txt --force-reinstall
```

## Next Steps

1. **Explore the API**: Visit http://localhost:8000/docs to see all available endpoints
2. **Generate More Data**: Run the simulator with different parameters
3. **Test Analytics**: Use the analytics endpoints to detect anomalies and trends
4. **Create Reports**: Generate compliance reports via the API
5. **Customize**: Modify thresholds and configurations in `.env`

## Contributing

When contributing to this project:

1. Create a feature branch: `git checkout -b feature/your-feature`
2. Write tests for new functionality
3. Ensure all tests pass: `pytest`
4. Format code: `black app/`
5. Commit with clear messages
6. Push and create a pull request

## Need Help?

- Check the [README.md](README.md) for project overview
- Review API documentation at `/docs` endpoint
- Open an issue on GitHub for bugs or questions
- Contact: tditshego70@gmail.com