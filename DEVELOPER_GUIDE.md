# 🚀 Developer Guide - OASM Nuclei AI Template Generator

This guide provides comprehensive instructions for setting up, developing, and contributing to the OASM Nuclei AI Template Generator project.

## 📑 Table of Contents

- [🏗️ Project Structure](#️-project-structure)
- [⚙️ Environment Setup](#️-environment-setup)
- [🐳 Docker Development](#-docker-development)
- [🔧 Manual Development Setup](#-manual-development-setup)
- [🔐 Authentication System](#-authentication-system)
- [📡 API Reference](#-api-reference)
- [🔄 Development Workflow](#-development-workflow)
- [📊 Monitoring & Debugging](#-monitoring--debugging)
- [⚙️ Configuration Reference](#️-configuration-reference)
- [🚀 Deployment](#-deployment)

## 🏗️ Project Structure

```
oasm-nuclei-gen/
├── 🐳 docker-compose.yml          # Microservices orchestration
├── 📋 Dockerfile                  # Container build configuration
├── ⚙️ .env                        # Environment variables
├── 📦 requirements.txt            # Python dependencies
│
├── 🚀 app/                        # Core application
│   ├── main.py                    # FastAPI entry point + middleware
│   ├── api/                       # API layer
│   │   ├── middlewares/           # Authentication & middleware
│   │   │   ├── __init__.py
│   │   │   └── auth.py            # Token authentication middleware
│   │   └── v1/                    # API v1 endpoints
│   │       ├── __init__.py
│   │       ├── endpoints.py       # REST API handlers
│   │       └── v1_dto.py          # Request/Response models
│   ├── core/                      # Business logic
│   │   ├── __init__.py
│   │   ├── nuclei_service.py      # Main orchestration service
│   │   ├── rag_engine.py          # ChromaDB integration
│   │   ├── nuclei_runner.py       # Template validation
│   │   └── scheduler.py           # Background scheduler
│   └── services/                  # External integrations
│       ├── __init__.py
│       └── vector_db.py           # Database abstraction
│
├── 🎯 templates/                  # AI prompt engineering
│   └── nuclei_prompts/
│       ├── system_prompt.txt      # LLM system context
│       └── user_prompt_template.txt # Generation instructions
│
├── 📚 rag_data/                   # Knowledge base
│   └── nuclei_templates/          # Nuclei templates repository
│
└── 📝 logs/                       # Application logs
    ├── app.log                   # API service logs
    └── scheduler.log             # Scheduler service logs
```

## ⚙️ Environment Setup

### 💻 System Requirements

| Component         | Version | Required |
| ----------------- | ------- | -------- |
| 🐍 Python         | 3.11+   | ✅       |
| 🐳 Docker         | 20.10+  | ✅       |
| 🐳 Docker Compose | v2.0+   | ✅       |
| 💾 RAM            | 2GB+    | ✅       |
| 💿 Storage        | 5GB+    | ✅       |

### 🔧 Environment Variables

Create and configure your `.env` file:

```bash
cp .env.example .env
```

**🏠 Core Configuration:**

```bash
# App Configuration
APP_NAME=Nuclei Template Generator
APP_VERSION=1.0.0
APP_DEBUG=false
APP_HOST=0.0.0.0
APP_PORT=8000

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
API_EXTERNAL_PORT=8000
API_WORKERS=1

# Vector Database Configuration
VECTOR_DB_HOST=chromadb
VECTOR_DB_PORT=8000
CHROMADB_HOST=chromadb
CHROMADB_PORT=8000
CHROMADB_EXTERNAL_PORT=8001
VECTOR_DB_MODE=client
VECTOR_DB_TYPE=chroma
VECTOR_DB_COLLECTION_NAME=nuclei_templates
VECTOR_DB_EMBEDDING_MODEL=all-MiniLM-L6-v2
VECTOR_DB_CHUNK_SIZE=1000
VECTOR_DB_CHUNK_OVERLAP=200

# LLM Configuration
LLM_PROVIDER=gemini                    # or 'openai'
LLM_MODEL=gemini-2.0-flash-exp         # or 'gpt-4o'
LLM_TEMPERATURE=0.3
LLM_MAX_TOKENS=4000
LLM_TIMEOUT=30

# API Keys (Required)
GEMINI_API_KEY=your_gemini_api_key_here
OPENAI_API_KEY=your_openai_api_key_here

# ChromaDB Configuration
CHROMA_SERVER_AUTHN_CREDENTIALS_FILE=
CHROMA_SERVER_AUTHN_PROVIDER=
ANONYMIZED_TELEMETRY=false
IS_PERSISTENT=true
PERSIST_DIRECTORY=/chroma/chroma

# Nuclei Configuration
NUCLEI_BINARY_PATH=nuclei
NUCLEI_TIMEOUT=30
NUCLEI_VALIDATE_ARGS=true
NUCLEI_TEMPLATES_DIR=rag_data/nuclei_templates

# RAG Configuration
RAG_MAX_RETRIEVED_DOCS=5
RAG_SIMILARITY_THRESHOLD=0.7
RAG_SEARCH_TYPE=similarity

# Logging Configuration
LOG_LEVEL=INFO
LOG_FORMAT=%(asctime)s - %(name)s - %(levelname)s - %(message)s
LOG_FILE_PATH=logs/app.log
LOG_MAX_BYTES=10485760
LOG_BACKUP_COUNT=5

# Scheduler Configuration
AUTO_UPDATE_TEMPLATE_NUCLEI=true
TIME_UPDATE_TEMPLATE=19:19

# Python Configuration
PYTHONPATH=/app
PYTHONUNBUFFERED=1
```

## 🐳 Docker Development

### 🚀 Quick Start with Docker

```bash
# 1. Clone repository
git clone https://github.com/oasm-platform/oasm-nuclei-gen.git
cd oasm-nuclei-gen

# 2. Configure environment
cp .env.example .env
# Edit .env file with your API keys

# 3. Start all services
docker-compose up -d

# 4. Check services status
docker-compose ps

# 5. View logs
docker-compose logs -f api
```

### 🛠️ Docker Commands Reference

```bash
# Start services in background
docker-compose up -d

# Start with rebuild
docker-compose up -d --build

# Stop all services
docker-compose down

# Stop and remove volumes
docker-compose down -v

# View service logs
docker-compose logs api
docker-compose logs scheduler
docker-compose logs chromadb

# Follow logs in real-time
docker-compose logs -f api

# Restart specific service
docker-compose restart api

# Execute commands in container
docker-compose exec api bash
docker-compose exec api python -c "print('Hello from container')"

# View service status
docker-compose ps
```

## 🔧 Manual Development Setup

### 📋 Step 1: Clone Repository

```bash
git clone https://github.com/oasm-platform/oasm-nuclei-gen.git
cd oasm-nuclei-gen
```

### 🐍 Step 2: Python Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate environment
# Linux/MacOS:
source venv/bin/activate
# Windows:
venv\Scripts\activate

# Upgrade pip
pip install --upgrade pip
```

### 📦 Step 3: Install Dependencies

```bash
# Install production dependencies
pip install -r requirements.txt

# For development (if requirements-dev.txt exists)
pip install -r requirements-dev.txt
```

### 🗄️ Step 4: Start ChromaDB

```bash
# Using Docker (recommended)
docker run -d \
  --name nuclei_chromadb \
  -p 8001:8000 \
  -e ANONYMIZED_TELEMETRY=false \
  -v chromadb_data:/chroma/chroma \
  chromadb/chroma:latest

# Verify ChromaDB is running
curl http://localhost:8001/api/v2/heartbeat
```

### 📚 Step 5: Initialize RAG Data

```bash
# Option 1: Clone nuclei-templates repository
git clone https://github.com/projectdiscovery/nuclei-templates.git rag_data/nuclei_templates

# Option 2: Use API endpoint (after starting the app)
curl -X PUT "http://localhost:8000/api/v1/reload_templates" \
  -H "Content-Type: application/json" \
  -H "token: your-auth-token"
```

### ▶️ Step 6: Run Services

```bash
# Terminal 1: Run API server
python -m app.main

# Terminal 2: Run scheduler (optional)
python -m app.core.scheduler
```

## 📡 API Reference

### 📋 Endpoints Overview

| Endpoint                    | Method | Description              | Auth Required |
| --------------------------- | ------ | ------------------------ | ------------- |
| `/health`                   | GET    | Health check             | ❌            |
| `/docs`                     | GET    | API documentation        | ❌            |
| `/api/v1/generate_template` | POST   | Generate Nuclei template | ✅            |
| `/api/v1/reload_templates`  | PUT    | Reload RAG templates     | ✅            |
| `/api/v1/rag_collection`    | DELETE | Clear RAG collection     | ✅            |

### 💡 API Usage Examples

#### 🩺 1. Health Check

```bash
curl http://localhost:8000/health
```

**Response:**

```json
{
  "message": "Nuclei Template Generator",
  "version": "1.0.0",
  "status": "healthy",
  "collection_name": "nuclei_templates",
  "total_documents": 7532
}
```

#### 🎯 2. Generate Template

```bash
curl -X POST http://localhost:8000/api/v1/generate_template \
  -H "Content-Type: application/json" \
  -H "token: your-auth-token" \
  -d '{
    "prompt": "Create a Nuclei template to detect SQL injection in login forms. Test both username and password parameters with POST method. Set severity to high.",
  }'
```

**Response:**

```json
{
  "success": true,
  "template_id": "sql-injection-login-form",
  "nuclei_template": "id: sql-injection-login-form\ninfo:\n  name: SQL Injection in Login Form\n  severity: high\n  author: AI-Generated\n  description: Detects SQL injection vulnerabilities in login forms\n\nrequests:\n  - method: POST\n    path:\n      - \"{{BaseURL}}/login\"\n    body: \"username={{injection}}&password=test\"\n    payloads:\n      injection:\n        - \"admin' OR '1'='1\"\n        - \"admin' UNION SELECT 1,2,3--\"\n    matchers:\n      - type: word\n        words:\n          - \"mysql_fetch\"\n          - \"ORA-01756\"\n          - \"Microsoft OLE DB\"\n        condition: or",
  "created_at": "2025-08-15T12:34:56.789Z"
}
```

#### 🔄 3. Reload Templates

```bash
curl -X PUT http://localhost:8000/api/v1/reload_templates \
  -H "Content-Type: application/json" \
  -H "token: your-auth-token"
```

#### 🗑️ 4. Clear RAG Collection

```bash
curl -X DELETE http://localhost:8000/api/v1/rag_collection \
  -H "token: your-auth-token"
```

### 🌍 Environment-Specific Configuration

**🧪 Development:**

```bash
APP_DEBUG=true
LOG_LEVEL=DEBUG
AUTO_UPDATE_TEMPLATE_NUCLEI=false
```

**🚀 Production:**

```bash
APP_DEBUG=false
LOG_LEVEL=INFO
AUTO_UPDATE_TEMPLATE_NUCLEI=true
TIME_UPDATE_TEMPLATE=02:00
```

## 📊 Monitoring & Debugging

### 📝 Logging

**📊 Log Levels:**

- `DEBUG`: Detailed development information
- `INFO`: General operational messages
- `WARNING`: Potentially harmful situations
- `ERROR`: Error events but application continues
- `CRITICAL`: Serious error events

**📂 Log Locations:**

- **API Service**: `logs/app.log`
- **Scheduler**: `logs/scheduler.log`
- **Docker**: `docker-compose logs service_name`

**👀 Viewing Logs:**

```bash
# Real-time API logs
tail -f logs/app.log

# Real-time Docker logs
docker-compose logs -f api

# Filter by log level
grep "ERROR" logs/app.log

# JSON formatted logs (if configured)
jq . logs/app.log
```

### 🩺 Health Monitoring

**🔍 Health Check Endpoint:**

```bash
curl http://localhost:8000/health
```

**🗄️ ChromaDB Health:**

```bash
curl http://localhost:8001/api/v1/heartbeat
```

**📊 Service Status:**

```bash
docker-compose ps
```

### 🐛 Debugging Common Issues

#### 🔐 1. Authentication Issues

```bash
# Check middleware is loaded
grep "TokenAuthMiddleware" logs/app.log

# Test without auth (should fail)
curl -X POST http://localhost:8000/api/v1/generate_template

# Check token validation logic
# Edit app/api/middlewares/auth.py _validate_token method
```

#### 🗄️ 2. RAG/ChromaDB Issues

```bash
# Check ChromaDB connection
curl http://localhost:8001/api/v2/heartbeat

# Check collection status
curl http://localhost:8000/health

# Reload templates
curl -X PUT http://localhost:8000/api/v1/reload_templates \
  -H "token: test-token"

# Check ChromaDB logs
docker-compose logs chromadb
```

#### 🤖 3. LLM Generation Issues

```bash
# Check API keys in logs (masked)
grep "API_KEY" logs/app.log

# Test different models
# Edit LLM_MODEL in .env

# Check generation logs
grep "generation" logs/app.log
```

#### ✅ 4. Template Validation Issues

```bash
# Check Nuclei binary
docker-compose exec api nuclei -version

# Test validation manually
docker-compose exec api nuclei -validate -t /tmp/test.yaml

# Check validation logs
grep "validation" logs/app.log
```

### ⚡ Performance Monitoring

**⏱️ Response Time Monitoring:**

```bash
# Time API requests
time curl -X POST http://localhost:8000/api/v1/generate_template \
  -H "Content-Type: application/json" \
  -H "token: test-token" \
  -d '{"prompt": "test"}'
```

**💾 Memory Usage:**

```bash
# Container memory usage
docker stats nuclei_agent_api

# System memory
free -h
```

**🗄️ Database Performance:**

```bash
# ChromaDB metrics
curl http://localhost:8001/api/v2/version
```

## ⚙️ Configuration Reference

### 🏠 Core Environment Variables

| Variable      | Default                     | Description         |
| ------------- | --------------------------- | ------------------- |
| `APP_NAME`    | `Nuclei Template Generator` | Application name    |
| `APP_VERSION` | `1.0.0`                     | Application version |
| `APP_DEBUG`   | `false`                     | Enable debug mode   |
| `APP_HOST`    | `0.0.0.0`                   | API server host     |
| `APP_PORT`    | `8000`                      | API server port     |

### 🔐 Authentication Configuration

| Variable              | Default                | Description                   |
| --------------------- | ---------------------- | ----------------------------- |
| `AUTH_ENABLED`        | `true`                 | Enable/disable authentication |
| `AUTH_EXCLUDED_PATHS` | `/health,/docs,/redoc` | Paths excluded from auth      |

### 🤖 LLM Configuration

| Variable          | Default                | Description                       |
| ----------------- | ---------------------- | --------------------------------- |
| `LLM_PROVIDER`    | `gemini`               | LLM provider (`gemini`, `openai`) |
| `LLM_MODEL`       | `gemini-2.0-flash-exp` | Model name                        |
| `LLM_TEMPERATURE` | `0.3`                  | Generation creativity (0.0-1.0)   |
| `LLM_MAX_TOKENS`  | `4000`                 | Maximum response tokens           |
| `LLM_TIMEOUT`     | `30`                   | Request timeout (seconds)         |

### 🗄️ Vector Database Configuration

| Variable                    | Default            | Description     |
| --------------------------- | ------------------ | --------------- |
| `VECTOR_DB_HOST`            | `chromadb`         | ChromaDB host   |
| `VECTOR_DB_PORT`            | `8000`             | ChromaDB port   |
| `VECTOR_DB_COLLECTION_NAME` | `nuclei_templates` | Collection name |
| `VECTOR_DB_EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | Embedding model |
| `VECTOR_DB_CHUNK_SIZE`      | `1000`             | Text chunk size |

### 🔍 RAG Configuration

| Variable                   | Default      | Description             |
| -------------------------- | ------------ | ----------------------- |
| `RAG_MAX_RETRIEVED_DOCS`   | `5`          | Context documents count |
| `RAG_SIMILARITY_THRESHOLD` | `0.7`        | Similarity threshold    |
| `RAG_SEARCH_TYPE`          | `similarity` | Search algorithm        |

### ⏰ Scheduler Configuration

| Variable                      | Default | Description         |
| ----------------------------- | ------- | ------------------- |
| `AUTO_UPDATE_TEMPLATE_NUCLEI` | `true`  | Enable auto-updates |
| `TIME_UPDATE_TEMPLATE`        | `19:19` | Update time (HH:MM) |

## 🚀 Deployment

### 🐳 Production Docker Deployment

**docker-compose.yml:**

```yaml
version: "3.8"

services:
  chromadb:
    image: chromadb/chroma:latest
    container_name: nuclei_chromadb_prod
    restart: unless-stopped
    env_file:
      - .env
    volumes:
      - chromadb_data:/chroma/chroma
    networks:
      - nuclei_network

  api:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: nuclei_agent_api_prod
    restart: unless-stopped
    env_file:
      - .env
    volumes:
      - ./logs:/app/logs
      - ./rag_data:/app/rag_data:ro
    networks:
      - nuclei_network
    depends_on:
      - chromadb
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  scheduler:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: nuclei_agent_scheduler_prod
    restart: unless-stopped
    env_file:
      - .env
    volumes:
      - ./logs:/app/logs
      - ./rag_data:/app/rag_data
    networks:
      - nuclei_network
    depends_on:
      - chromadb
    command: ["python", "-m", "app.core.scheduler"]

volumes:
  chromadb_data:
    driver: local

networks:
  nuclei_network:
    driver: bridge
```

---

This comprehensive developer guide covers all aspects of setting up, developing, and deploying the OASM Nuclei AI Template Generator. For additional help, refer to the API documentation at `/docs` or create an issue in the repository.
