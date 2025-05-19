# RAGPilot

A powerful Retrieval-Augmented Generation (RAG) platform designed to enhance Large Language Model applications with precise context retrieval and document management capabilities.

## 🚀 Features

- **Document Management**: Upload, version, tag, and organize documents for your knowledge base
- **Advanced Retrieval**: Semantic search with customizable embedding models
- **LLM Integration**: Connect to various LLM providers including OpenAI, Anthropic, and others
- **Query Optimization**: Contextual query enhancement for better results
- **Built-in Chat Interface**: User-friendly interface for interacting with your RAG system
- **Monitoring & Analytics**: Track usage patterns and performance metrics
- **Scalable Backend**: FastAPI-based backend with async support
- **Modern Frontend**: Clean, responsive UI built with Next.js

## 🏗️ System Architecture

RAGPilot follows a modern microservices architecture:

- **Backend**: Python FastAPI application with SQLModel for database interactions
- **Frontend**: Next.js application with a responsive UI
- **Database**: PostgreSQL for structured data
- **Storage**: S3-compatible storage for document files
- **Containerization**: Docker for easy deployment and scaling

## 🔧 Setup

### Prerequisites

- Python 3.10+
- Node.js 18+
- Docker and Docker Compose
- AWS account (for S3) or compatible alternative

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/STrachov/RAGPilot.git
   cd RAGPilot
   ```

2. Set up environment variables:
   ```bash
   cp src/backend/.env.example src/backend/.env
   # Edit .env file with your configuration
   ```

3. Start the application with Docker Compose:
   ```bash
   cd src
   docker-compose up -d
   ```

4. Access the application:
   - Frontend: http://localhost:3000
   - API: http://localhost:8000/docs

### Development Setup

For local development:

1. Set up the backend:
   ```bash
   cd src/backend
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   python -m app.main
   ```

2. Set up the frontend:
   ```bash
   cd src/frontend
   npm install
   npm run dev
   ```

## 📚 Usage

### Document Management

1. Navigate to the Document Management section
2. Upload documents via the UI or API
3. Apply tags and metadata for better organization
4. Manage versions and access controls

### Search & Retrieval

1. Use the search interface to query your knowledge base
2. Fine-tune retrieval parameters for better results
3. View source documents and relevance scores

### Chat Interface

1. Start a new conversation
2. Ask questions related to your document corpus
3. Explore cited sources for each response

## 🧪 Testing

Run the test suite:
```bash
cd tests
pytest
```

For specific test categories:
```bash
python run_single_test.py tests/integration/user/test_authentication.py
```

## 🔒 Security

- All API endpoints are protected with JWT authentication
- Role-based access control for different user types
- Document-level access permissions
- Encrypted storage for sensitive data

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 📧 Contact

For questions and support, please open an issue on the GitHub repository. 