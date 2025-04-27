# Webhook Delivery Service

A robust microservice-based webhook delivery system built with FastAPI.

## Architecture

The system consists of the following services:

1. **API Service**: Handles webhook ingestion and subscription management
2. **Worker Service**: Processes webhook deliveries and retries
3. **Database Service**: Stores subscriptions and delivery logs
4. **Cache Service**: Caches subscription details

## Setup

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

4. Run migrations:
```bash
alembic upgrade head
```

5. Start the services:
```bash
# Start API service
uvicorn app.main:app --reload

# Start worker service
celery -A app.worker worker --loglevel=info
```

## API Documentation

Once the service is running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Features

- Subscription management (CRUD operations)
- Webhook ingestion and queuing
- Asynchronous delivery processing
- Retry mechanism with exponential backoff
- Delivery logging and status tracking
- Log retention policy
- Caching for performance optimization 