# RAGPilot Source Code

This directory contains the source code for the RAGPilot project.

## Directory Structure

- `/backend/`: FastAPI backend application
  - `/app/`: Main application code
    - `/api/`: API routes and endpoints
      - `/routes/`: API route definitions
    - `/core/`: Core functionality and utilities
      - `/config/`: Configuration settings
      - `/crud/`: Database operations
      - `/middleware/`: Request/response middleware
      - `/models/`: Database models
      - `/services/`: External service integrations
    - `/alembic/`: Database migration scripts
  - `Dockerfile`: Container definition for backend
  - `poetry.lock` & `pyproject.toml`: Dependency management

- `/frontend/`: Next.js frontend application
  - `/public/`: Static assets
  - `/src/`: Frontend source code
    - `/app/`: Next.js app directory
    - `/components/`: React components
    - `/icons/`: SVG icons
    - `/layout/`: Layout components
    - `/context/`: Context providers
    - `/hooks/`: Custom React hooks

- `/ssl/`: SSL certificates (for development use only)
- `docker-compose.yml`: Container orchestration
- `nginx.conf`: Nginx configuration for production deployment

## Technical Implementation

### Backend

The backend uses FastAPI with SQLModel for database interactions. Key technologies include:

- **FastAPI**: High-performance web framework
- **SQLModel**: SQL database interaction layer combining SQLAlchemy and Pydantic
- **Alembic**: Database migration management
- **JWT**: Authentication using JSON Web Tokens
- **Asyncpg**: Asynchronous PostgreSQL driver
- **S3 Client**: AWS S3 integration for document storage

### Frontend

The frontend uses Next.js with React. Key technologies include:

- **Next.js**: React framework with server-side rendering capabilities
- **Tailwind CSS**: Utility-first CSS framework for styling
- **React Context**: Global state management
- **Fetch API**: Data fetching from backend services

### Deployment

The application is containerized using Docker with the following structure:

- Backend container (Python/FastAPI)
- Frontend container (Node.js/Next.js)
- PostgreSQL container
- Nginx container (reverse proxy)

## Development Guidelines

### Backend Development

1. Follow the FastAPI project structure
2. Use async/await for database operations
3. Document all API endpoints with docstrings
4. Write tests for all API routes
5. Use Pydantic models for request/response validation

### Frontend Development

1. Use functional components with hooks
2. Implement responsive design with Tailwind CSS
3. Keep components small and focused
4. Use context for state management
5. Implement proper error handling for API requests

### API Documentation

API documentation is available at `/docs` when running the backend server. The documentation is automatically generated from the API endpoint definitions.
