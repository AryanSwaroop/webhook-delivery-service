# Webhook Delivery Service

A robust, scalable webhook delivery service built with FastAPI, PostgreSQL, Redis, and Celery. This service provides reliable webhook delivery with automatic retries, status tracking, and comprehensive logging.

## Features

- Asynchronous webhook delivery with automatic retries
- Real-time delivery status tracking
- Comprehensive logging of delivery attempts
- Secure webhook verification
- Scalable architecture with background processing
- Full-text search capabilities
- Docker support for easy deployment

## Architecture

### Technology Stack

- **FastAPI**: Modern, fast web framework for building APIs with automatic OpenAPI documentation
- **PostgreSQL**: Robust relational database with JSON support and full-text search
- **Redis**: In-memory data store for caching and message brokering
- **Celery**: Distributed task queue for background processing
- **Docker**: Containerization for consistent deployment
- **SQLAlchemy**: SQL toolkit and ORM for database operations
- **Pydantic**: Data validation and settings management

### Architecture Decisions

1. **FastAPI** was chosen for its:
   - Native async support
   - Automatic API documentation
   - High performance
   - Type hints and validation

2. **PostgreSQL** was selected because:
   - JSONB support for flexible webhook payload storage
   - Full-text search capabilities
   - Robust transaction support
   - Excellent performance with proper indexing

3. **Redis** is used for:
   - Caching subscription data
   - Message brokering for Celery
   - Fast access to frequently used data

4. **Celery** provides:
   - Background task processing
   - Automatic retry mechanism
   - Task scheduling
   - Distributed processing capabilities

### Database Schema

The database schema consists of three main tables:

1. **subscriptions**
   - Stores webhook endpoint configurations
   - Includes full-text search vector for efficient searching
   - Indexes on name (case-insensitive) and created_at

2. **webhook_deliveries**
   - Tracks webhook delivery attempts
   - Stores payload in JSONB format
   - Includes status tracking and retry scheduling
   - Indexes on status, subscription_id, and created_at

3. **delivery_attempts**
   - Logs individual delivery attempts
   - Stores response data and error messages
   - Indexes on delivery_id and created_at

### Indexing Strategy

- **B-tree indexes** for:
  - Primary keys
  - Foreign keys
  - Timestamp-based queries
  - Status filtering

- **GIN indexes** for:
  - Full-text search on subscription names
  - JSONB payload search
  - Array operations

## Setup and Installation

### Prerequisites

- Docker and Docker Compose
- Git

### Local Development

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/webhook-service.git
   cd webhook-service
   ```

2. Create environment file:
   ```bash
   cp .env.example .env
   ```

3. Start the services:
   ```bash
   docker-compose up --build
   ```

The application will be available at http://localhost:8000

### API Documentation

The API documentation is available at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## API Usage

### Managing Subscriptions

1. Create a subscription:
   ```bash
   curl -X POST "http://localhost:8000/subscriptions/" \
        -H "Content-Type: application/json" \
        -d '{
            "name": "test-subscription",
            "target_url": "http://example.com/webhook",
            "secret_key": "testsecretkey123456789012345678901234"
        }'
   ```

2. List all subscriptions:
   ```bash
   curl "http://localhost:8000/subscriptions/"
   ```

3. Get a specific subscription:
   ```bash
   curl "http://localhost:8000/subscriptions/1"
   ```

4. Update a subscription:
   ```bash
   curl -X PUT "http://localhost:8000/subscriptions/1" \
        -H "Content-Type: application/json" \
        -d '{
            "name": "updated-subscription",
            "target_url": "http://example.com/webhook",
            "secret_key": "newsecretkey123456789012345678901234"
        }'
   ```

5. Delete a subscription:
   ```bash
   curl -X DELETE "http://localhost:8000/subscriptions/1"
   ```

### Webhook Delivery

1. Ingest a webhook:
   ```bash
   curl -X POST "http://localhost:8000/ingest/1" \
        -H "Content-Type: application/json" \
        -d '{
            "event_type": "test_event",
            "data": {"key": "value"}
        }'
   ```

2. Check delivery status:
   ```bash
   curl "http://localhost:8000/deliveries/1"
   ```

3. List subscription deliveries:
   ```bash
   curl "http://localhost:8000/subscriptions/1/deliveries"
   ```

## Deployment

The service is deployed on [Your Deployment Platform] and available at:
https://your-deployment-url.com

## Cost Estimation

Assuming deployment on AWS free tier:

1. **EC2 (t2.micro)**: $0/month (750 hours/month)
   - 1 vCPU, 1GB RAM
   - Sufficient for moderate traffic

2. **RDS (PostgreSQL)**: $0/month (750 hours/month)
   - db.t2.micro instance
   - 20GB storage

3. **ElastiCache (Redis)**: $0/month (750 hours/month)
   - cache.t2.micro instance

4. **Data Transfer**: ~$0.09/month
   - 5000 webhooks/day × 30 days = 150,000 webhooks/month
   - Average payload size: 1KB
   - Total data: ~150MB/month

**Total Estimated Cost**: ~$0.09/month

## Assumptions

1. Average webhook payload size: 1KB
2. Average delivery attempts per webhook: 1.2
3. Moderate traffic: 5000 webhooks/day
4. 99% of webhooks delivered within 3 attempts
5. Using AWS free tier resources
6. No additional monitoring or logging services
7. No SSL/TLS certificate costs (using Let's Encrypt)

## Credits

- FastAPI: https://fastapi.tiangolo.com/
- SQLAlchemy: https://www.sqlalchemy.org/
- Celery: https://docs.celeryq.dev/
- Redis: https://redis.io/
- PostgreSQL: https://www.postgresql.org/
- Docker: https://www.docker.com/

## License

MIT License - See LICENSE file for details 