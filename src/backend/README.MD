# RAGPilot Backend

The FastAPI-based backend service for the RAGPilot application.

## Overview

This backend implements a high-performance API using FastAPI with the following features:

- Asynchronous database operations using SQLModel and asyncpg
- JWT-based authentication system
- Document management and retrieval system
- Role-based access control
- Alembic migrations for database versioning
- Dependency injection for services

## Tech Stack

- **FastAPI**: Web framework
- **SQLModel**: ORM for database interactions
- **Alembic**: Database migrations
- **Pydantic**: Data validation
- **PostgreSQL**: Database
- **JWT**: Authentication
- **Poetry**: Dependency management

## Installation

### Prerequisites

- Python 3.10+
- PostgreSQL
- Docker and Docker Compose

### Setup Steps

1. Enter the backend folder:
   ```bash
   cd src/backend
   ```

2. Check PostgreSQL port in `.env` file:
   ```
   POSTGRES_PORT=5432
   ```

3. Install Poetry (dependency manager):
   ```bash
   pip install poetry
   ```

4. Install dependencies:
   ```bash
   poetry install
   ```

5. Start PostgreSQL and other dependencies:
   ```bash
   docker-compose up -d
   ```

6. Run database migrations:
   ```bash
   poetry run alembic upgrade head
   ```

7. Check and update the superuser credentials in the `.env` file:
   ```
   FIRST_SUPERUSER_EMAIL=admin@example.com
   FIRST_SUPERUSER_PASSWORD=changeme
   ```

8. Initialize the database with initial data:
   ```bash
   poetry run python -m app.initial_data
   ```

9. Start the application:
   ```bash
   poetry run python -m app.main
   ```

## Development

### Running in Development Mode

For development with auto-reload:

```bash
poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Environment Variables

Key environment variables:

- `POSTGRES_USER`: Database username
- `POSTGRES_PASSWORD`: Database password
- `POSTGRES_HOST`: Database host
- `POSTGRES_PORT`: Database port
- `POSTGRES_DB`: Database name
- `SECRET_KEY`: JWT secret key
- `ALGORITHM`: JWT algorithm (default: HS256)
- `ACCESS_TOKEN_EXPIRE_MINUTES`: Token expiration time

See the `.env.example` file for all available configuration options.

## Testing

Run tests using pytest:

```bash
poetry run pytest
```

For specific test categories:

```bash
poetry run pytest tests/api/test_users.py -v
```

## API Documentation

When the application is running, the API documentation is available at:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Database Migrations

Create a new migration after model changes:

```bash
poetry run alembic revision --autogenerate -m "description of changes"
```

Apply migrations:

```bash
poetry run alembic upgrade head
```

## Troubleshooting

### Database Connection Issues

Ensure PostgreSQL is running:

```bash
docker ps | grep postgres
```

Check the database connection settings in the `.env` file.

### Authentication Issues

If you're having issues with authentication, ensure:

1. The `SECRET_KEY` is properly set in the `.env` file
2. The superuser was correctly initialized
3. The token expiration time is reasonable
