# KnowledgeInjester

A Django-based knowledge ingestion and retrieval system with multi-tenant support, custom prompts, and AI-powered question answering capabilities.

## Features

- **Multi-tenant Architecture**: Isolated data and configurations per organization
- **Custom Prompts**: Organization-specific AI prompts for tailored responses
- **Knowledge Ingestion**: Web crawling, document processing, and vectorization
- **RAG (Retrieval-Augmented Generation)**: Hybrid search with citations
- **RESTful API**: Django Ninja Extra with OpenAPI documentation
- **Vector Storage**: PostgreSQL with pgvector for semantic search
- **Async Processing**: Celery for background tasks

## Prerequisites

- Python 3.10+
- PostgreSQL 12+ with pgvector extension
- Redis (for Celery)
- Git

## Quick Start

### Option 1: Automated Setup (Recommended)

```bash
git clone https://github.com/soubhratra/knowledgeinjester.git
cd knowledgeinjester
./setup.sh
```

The setup script will:
- Check Python version requirements
- Create virtual environment
- Install dependencies
- Create `.env` file from template
- Run database migrations
- Optionally create a superuser

### Option 2: Manual Setup

#### 1. Clone the Repository

```bash
git clone https://github.com/soubhratra/knowledgeinjester.git
cd knowledgeinjester
```

#### 2. Create Virtual Environment

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

#### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Environment Configuration

Create a `.env` file in the project root:

```bash
cp env.example .env
```

Edit `.env` with your configuration:

```env
# Database
DATABASE_URL=postgresql://username:password@localhost:5432/knowledgeinjester

# Redis
REDIS_URL=redis://localhost:6379/0

# OpenAI
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4o-mini

# Supabase (for vector storage)
SUPABASE_URL=your_supabase_url
SUPABASE_ANON_KEY=your_supabase_anon_key
SUPABASE_SERVICE_KEY=your_supabase_service_key

# Django
SECRET_KEY=your_secret_key_here
DEBUG=True
ENV=development
```

### 5. Database Setup

#### Install PostgreSQL and pgvector

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
sudo apt install postgresql-14-pgvector  # or appropriate version
```

**macOS (with Homebrew):**
```bash
brew install postgresql
brew install pgvector
```

**Docker (Alternative):**
```bash
docker run --name postgres-pgvector -e POSTGRES_PASSWORD=password -e POSTGRES_DB=knowledgeinjester -p 5432:5432 -d pgvector/pgvector:pg15
```

#### Create Database

```bash
# Connect to PostgreSQL
psql -U postgres

# Create database and user
CREATE DATABASE knowledgeinjester;
CREATE USER knowledgeinjester_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE knowledgeinjester TO knowledgeinjester_user;

# Enable pgvector extension
\c knowledgeinjester
CREATE EXTENSION IF NOT EXISTS vector;

\q
```

### 6. Run Migrations

```bash
python manage.py migrate
```

### 7. Create Superuser (Optional)

```bash
python manage.py createsuperuser
```

### 8. Start the Development Server

```bash
python manage.py runserver
```

The server will start at `http://localhost:8000`

## Testing the API

### 1. OpenAPI Documentation (Swagger UI)

Once the server is running, open your browser and navigate to:

**http://localhost:8000/api/docs**

This will show you the interactive Swagger UI where you can:
- View all available API endpoints
- Test API calls directly from the browser
- See request/response schemas
- Try out the `/ask` endpoint with sample data

### 2. Alternative Documentation (ReDoc)

For a different documentation view, visit:

**http://localhost:8000/redoc**

### 3. Test the Health Endpoint

First, test that the server is running:

```bash
curl http://localhost:8000/healthz
```

Expected response:
```json
{"status": "ok", "env": "development"}
```

### 4. Create Your First Organization

1. **Access Django Admin**: Go to http://localhost:8000/admin
2. **Login** with your superuser credentials
3. **Create Organization**:
   - Click "Organizations" → "Add"
   - Fill in:
     - Name: "My Test Organization"
     - Slug: "my-test-org"
     - Tenant ID: "test-tenant-123"
   - Save the organization

### 5. Set Custom Prompt (Optional)

```bash
python manage.py set_custom_prompt test-tenant-123 \
  --prompt-text "You are a helpful AI assistant for {organization_name}. Please answer questions based on the provided context." \
  --validate
```

### 6. Ingest Some Knowledge

```bash
curl -X POST http://localhost:8000/v1/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "test-tenant-123",
    "url": "https://en.wikipedia.org/wiki/Artificial_intelligence",
    "max_pages": 5
  }'
```

### 7. Test the Ask Endpoint

```bash
curl -X POST http://localhost:8000/v1/ask \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "text": "What is artificial intelligence?"}],
    "tenant_id": "test-tenant-123",
    "citations": true
  }'
```

### 8. Test via Swagger UI

1. Go to http://localhost:8000/docs
2. Find the `/v1/ask` endpoint
3. Click "Try it out"
4. Use this sample request:
   ```json
   {
     "messages": [{"role": "user", "text": "What is artificial intelligence?"}],
     "tenant_id": "test-tenant-123",
     "citations": true
   }
   ```
5. Click "Execute" to test the API

## API Documentation

### OpenAPI Documentation

Once the server is running, you can access the interactive API documentation:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI Schema**: http://localhost:8000/openapi.json

### API Endpoints

#### Health Check
```bash
curl http://localhost:8000/healthz
```

#### Ask Questions (RAG)
```bash
curl -X POST http://localhost:8000/v1/ask \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "text": "What is artificial intelligence?"}],
    "tenant_id": "your-tenant-id",
    "citations": true
  }'
```

#### Ingest Knowledge
```bash
curl -X POST http://localhost:8000/v1/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "your-tenant-id",
    "url": "https://example.com",
    "max_pages": 10
  }'
```

## Custom Prompts

### Setting Custom Prompts

Use the management command to set organization-specific prompts:

```bash
# Set prompt from text
python manage.py set_custom_prompt your-tenant-id \
  --prompt-text "You are a specialized assistant for {organization_name}..." \
  --validate

# Set prompt from file
python manage.py set_custom_prompt your-tenant-id \
  --prompt-file /path/to/prompt.txt \
  --validate

# Clear custom prompt (use defaults)
python manage.py set_custom_prompt your-tenant-id --clear
```

### Prompt Template Placeholders

- `{context}` - Retrieved context from knowledge base
- `{question}` - User's question
- `{sources}` - Formatted sources list (when citations enabled)
- `{organization_name}` - Organization name

### Safety Guidelines

All prompts (both custom and default) automatically include safety instructions that ensure the AI only responds to appropriate questions. The safety guidelines:

- Ensure questions are legally and ethically valid
- Prevent responses to vulgar, profane, or abusive language
- Require respectful and constructive questions
- Politely decline inappropriate questions with explanation

If a question violates these guidelines, the AI will respond: *"I'm sorry, but I cannot answer this question as it contains inappropriate content. Please ask a respectful and constructive question that I can help you with."*

### Content Moderation

The system uses OpenAI's Moderation API to automatically filter inappropriate content before processing:

- **Automatic Filtering**: All user questions are checked against OpenAI's moderation categories
- **Categories Monitored**: Hate, violence, sexual content, self-harm, and other inappropriate content
- **Graceful Fallback**: If moderation fails, content is allowed through to prevent service disruption
- **Configurable Thresholds**: Moderation sensitivity can be adjusted per organization if needed

The moderation service checks for:
- Hate speech and threatening language
- Violence and graphic content
- Sexual content and inappropriate material
- Self-harm related content
- Other policy violations

### Example Custom Prompt

```text
You are a medical AI assistant for {organization_name}.

Context:
{context}

Question: {question}

Instructions:
- Provide accurate, evidence-based medical information
- Always recommend consulting with healthcare professionals
- Cite sources using [1], [2], etc. when referencing medical literature

Sources:
{sources}

Remember: This information is for educational purposes only.
```

**Note:** Safety guidelines are automatically appended to all prompts, so you don't need to include them in your custom prompts.

## Testing

### Run All Tests

```bash
python manage.py test
```

### Run Specific Test Suites

```bash
# Unit tests
python -m pytest tests/unit/ -v

# Integration tests
python -m pytest tests/integration/ -v

# Custom prompt tests
python -m pytest tests/unit/test_prompt_service.py -v
```

### Test Coverage

```bash
python -m pytest --cov=apps --cov-report=html
```

## Development

### Project Structure

```
knowledgeinjester/
├── apps/
│   ├── api/                 # API endpoints and schemas
│   ├── core/                # Core utilities and settings
│   ├── crawler/             # Web crawling functionality
│   ├── extractor/           # Content extraction
│   ├── pipelines/           # LangGraph processing pipelines
│   ├── tenants/             # Multi-tenant models and management
│   └── vectorizer/          # Vector storage and search
├── tests/                   # Test suites
├── requirements.txt         # Python dependencies
├── manage.py               # Django management script
└── knowledgeinjester/      # Django project settings
```

### Adding New Organizations

1. Create organization via Django admin or API
2. Set custom prompt if needed
3. Configure Supabase credentials for the tenant
4. Start ingesting knowledge for the organization

### Background Tasks

Start Celery worker for background processing:

```bash
celery -A knowledgeinjester worker --loglevel=info
```

## Production Deployment

### Environment Variables

Set these in your production environment:

```env
DEBUG=False
SECRET_KEY=your_production_secret_key
DATABASE_URL=postgresql://user:pass@host:port/db
REDIS_URL=redis://host:port/0
OPENAI_API_KEY=your_openai_key
SUPABASE_URL=your_supabase_url
SUPABASE_ANON_KEY=your_supabase_anon_key
SUPABASE_SERVICE_KEY=your_supabase_service_key
```

### Database Migrations

```bash
python manage.py migrate
```

### Static Files

```bash
python manage.py collectstatic
```

## Troubleshooting

### Common Issues

1. **pgvector extension not found**
   - Ensure PostgreSQL has pgvector extension installed
   - Run `CREATE EXTENSION IF NOT EXISTS vector;` in your database

2. **Redis connection failed**
   - Ensure Redis is running on the configured port
   - Check REDIS_URL in your .env file

3. **OpenAI API errors**
   - Verify OPENAI_API_KEY is set correctly
   - Check API key has sufficient credits

4. **Supabase connection issues**
   - Verify SUPABASE_URL and keys are correct
   - Ensure the Supabase project is active

### Logs

Check Django logs for detailed error information:

```bash
python manage.py runserver --verbosity=2
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Run the test suite
6. Submit a pull request

## License

[Add your license information here]

## Support

For questions and support, please open an issue on GitHub or contact [your-email@example.com].
