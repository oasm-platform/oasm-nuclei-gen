# Nuclei AI Agent Template Generator (OASM AI Agent Gen Template Nuclei)

![Nuclei AI Agent](https://img.shields.io/badge/Nuclei-AI%20Agent-blue?style=for-the-badge&logo=ai)
![LangChain](https://img.shields.io/badge/LangChain-Powered-green?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3.8+-blue?style=for-the-badge&logo=python)

## 📖 Project Description

The Nuclei AI Agent Template Generator is an AI system that automates the creation and validation of Nuclei templates for cybersecurity testing purposes. This project leverages advanced AI technology with LangChain and RAG (Retrieval Augmented Generation) to generate high-quality templates based on knowledge from existing template databases.

### 🎯 Key Features

- **Automated Nuclei Template Generation**: Uses AI to create templates based on vulnerability descriptions
- **Automatic Validation**: Integrates `nuclei --validate` to check template validity
- **RAG Engine**: Searches and references from existing template database
- **RESTful API**: Provides easy-to-use interface
- **Detailed Logging**: Monitors the entire template generation process

## 📋 Reference Documentation

- **Presentation Slides**: [AI Agent Gen Template Nuclei](https://www.canva.com/design/DAGvRL9BIz0/B1F-Rg6qyltfKrNVrzrrBg/edit?utm_content=DAGvRL9BIz0&utm_campaign=designshare&utm_medium=link2&utm_source=sharebutton)
- **Detailed Workflow**: [Work Flow AI Agent Gen Template Nuclei](docs/work-flow.md)

## 🏗️ Project Structure

```
nuclei-ai-agent/
├── app/
│   ├── main.py                    # Entry point of the application (Flask/FastAPI)
│   ├── core/
│   │   ├── agent.py               # Logic of AI Agent (LangChain)
│   │   ├── rag_engine.py          # Retrieval Augmented Generation (RAG)
│   │   └── nuclei_runner.py       # Logic calling nuclei --validate
│   ├── api/
│   │   └── v1/
│   │       └── endpoints.py       # API endpoints (/generate_template)
│   ├── models/
│   │   ├── __init__.py
│   │   └── template.py            # Pydantic models for Nuclei template
│   └── services/
│       └── vector_db.py           # Connect and interact with vector database
├── templates/
│   └── nuclei_prompts/            # Prompt templates for LLM
│       ├── system_prompt.txt
│       └── user_prompt_template.txt
├── rag_data/
│   └── nuclei_templates/          # Template nuclei for RAG
│       ├── cve-2023-1234.yaml     # Template CVE
│       └── exposed-database.yaml  # Template Exposed Database
├── scripts/
│   └── (deprecated)                # Scripts moved to API endpoints
├── config/
│   ├── config.yaml                # Global configuration
│   └── secrets.yaml               # API keys (sensitive data)
├── logs/
│   ├── app.log                    # Application log
│   └── nuclei.log                 # Nuclei validation log
├── tests/
│   ├── test_agent.py
│   ├── test_nuclei_runner.py
│   └── test_api.py
├── .gitignore
├── requirements.txt
└── README.md
```

## 🚀 Installation and Setup

### System Requirements

- Python 3.8+
- Nuclei CLI tool
- Vector Database (ChromaDB/Pinecone/FAISS)
- OpenAI API key or local LLM
- Docker & Docker Compose (for containerized deployment)

## 🐳 Quick Start with Docker (Recommended)

The easiest way to get started is using Docker Compose with ChromaDB:

### Prerequisites

- Docker and Docker Compose installed
- At least 2GB RAM available

### 1. Clone and Setup

```bash
git clone https://github.com/your-username/nuclei-ai-agent.git
cd nuclei-ai-agent

# Copy environment file
cp .env.example .env
```

### 2. Configure Environment

Edit `.env` file:

```bash
# API Keys (optional - uses free local embedding model by default)
OPENAI_API_KEY=your_openai_api_key_here
GEMINI_API_KEY=your_gemini_api_key_here
```

### 3. Start Services

```bash
# Start ChromaDB and application
docker-compose up -d

# Check services are running
docker-compose ps
```

### 4. Load Templates

```bash
# Use the new API endpoint to update RAG data (recommended)
curl -X POST "http://localhost:8000/api/v1/update_rag_data" \
  -H "Content-Type: application/json" \
  -d '{"force_update": true}'

# Or manually download templates (optional)
# git clone https://github.com/projectdiscovery/nuclei-templates.git rag_data/nuclei_templates
```

### 5. Test API

```bash
curl http://localhost:8000/health
```

**🎉 That's it! Your Nuclei AI Agent is now running with ChromaDB.**

📖 **For detailed Docker setup instructions, see [DOCKER_SETUP_GUIDE.md](DOCKER_SETUP_GUIDE.md)**

---

## 🔧 Manual Installation (Alternative)

### Step 1: Clone repository

```bash
git clone https://github.com/your-username/nuclei-ai-agent.git
cd nuclei-ai-agent
```

### Step 2: Install dependencies

```bash
pip install -r requirements.txt
```

### Step 3: Install Nuclei

```bash
# Using Go
go install -v github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest

# Hoặc sử dụng package manager
# Ubuntu/Debian
apt install nuclei

# macOS
brew install nuclei
```

### Step 4: Configuration

1. Copy the configuration sample file:

```bash
cp config/config.example.yaml config/config.yaml
cp config/secrets.example.yaml config/secrets.yaml
```

2. Edit `config/secrets.yaml`:

```yaml
openai:
  api_key: "your-openai-api-key-here"

vector_db:
  connection_string: "your-vector-db-connection"
```

### Step 5: Initialize RAG data

```bash
# Use the new API endpoint to update RAG data (recommended)
curl -X POST "http://localhost:8000/api/v1/update_rag_data" \
  -H "Content-Type: application/json" \
  -d '{"force_update": true}'

# Or manually:
# git clone https://github.com/projectdiscovery/nuclei-templates.git rag_data/nuclei_templates
```

### Step 6: Run the application

```bash
# Using script
chmod +x scripts/run_agent.sh
./scripts/run_agent.sh

# Or run directly
python -m app.main
```

## 🎮 Usage

### API Endpoints

#### 1. Generate Nuclei Template

```bash
POST /api/v1/generate_template

{
  "vulnerability_description": "SQL Injection in login form",
  "target_info": {
    "url": "https://example.com/login",
    "method": "POST",
    "parameters": ["username", "password"]
  },
  "severity": "high"
}
```

#### 2. Validate Template

```bash
POST /api/v1/validate_template

{
  "template_content": "yaml_content_here"
}
```

#### 3. Update RAG Data (New)

```bash
POST /api/v1/update_rag_data

{
  "vector_db": {
    "collection_name": "nuclei_templates",
    "embedding_model": "all-MiniLM-L6-v2"
  },
  "force_update": true
}
```

This endpoint replaces the old `ingest_data.py` script and provides:
- Automatic clearing of existing RAG data
- Download of latest Nuclei templates from GitHub
- Loading templates into the vector database
- Configuration updates via API

#### 4. Clear RAG Collection

```bash
DELETE /api/v1/rag_collection
```

#### 5. Reload Templates

```bash
POST /api/v1/reload_templates
```

#### 6. Get RAG Statistics

```bash
GET /api/v1/rag_stats
```

#### 7. Search Templates

```bash
POST /api/v1/search_templates

{
  "query": "sql injection",
  "max_results": 5,
  "similarity_threshold": 0.7
}
```

### Python Usage Example

```python
import requests

# Generate template
response = requests.post('http://localhost:8000/api/v1/generate_template', json={
    "vulnerability_description": "XSS vulnerability in search parameter",
    "target_info": {
        "url": "https://target.com/search?q={{payload}}",
        "method": "GET"
    },
    "severity": "medium"
})

template = response.json()
print(template['generated_template'])

# Update RAG data with latest templates
update_response = requests.post('http://localhost:8000/api/v1/update_rag_data', json={
    "force_update": True
})

print(f"Templates loaded: {update_response.json()['templates_loaded']}")
```

### Command Line Interface

```bash
# Run agent from command line
python -m app.core.agent --description "SSTI vulnerability" --url "https://example.com/template"
```

## 🧠 AI Agent Architecture

### Workflow Overview

1. **Input Processing**: Receives vulnerability description from user
2. **RAG Retrieval**: Searches for similar templates from vector database
3. **Template Generation**: Uses LLM to generate new template
4. **Validation**: Runs `nuclei --validate` for verification
5. **Refinement**: Improves template if validation fails
6. **Output**: Returns complete template

### Core Components

- **LangChain Agent**: Orchestrates workflow and uses tools
- **RAG Engine**: ChromaDB/FAISS for storing and searching embeddings
- **Nuclei Runner**: Wrapper to run nuclei CLI
- **Template Parser**: Parse and validate YAML templates

## 🔧 Advanced Configuration

### Vector Database

```yaml
# config/config.yaml
vector_db:
  type: "chromadb" # chromadb, pinecone, faiss
  persist_directory: "./chroma_db"
  collection_name: "nuclei_templates"
  embedding_model: "text-embedding-ada-002"
```

### LLM Configuration

```yaml
llm:
  provider: "openai" # openai, huggingface, local
  model: "gpt-4"
  temperature: 0.7
  max_tokens: 2000
```

### Nuclei Settings

```yaml
nuclei:
  binary_path: "/usr/local/bin/nuclei"
  timeout: 30
  validate_args: ["--validate", "--verbose"]
```

## 🧪 Testing

Run test suite:

```bash
# Run all tests
python -m pytest tests/

# Run specific test
python -m pytest tests/test_agent.py -v

# Test with coverage
python -m pytest --cov=app tests/
```

## 📊 Monitoring and Logging

### Log levels

- **DEBUG**: Detailed processing information
- **INFO**: General information
- **WARNING**: Validation warnings
- **ERROR**: Errors during template generation

### Log files

- `logs/app.log`: Application log
- `logs/nuclei.log`: Output from nuclei validation
- `logs/rag.log`: Log from RAG engine

## 🤝 Contributing

1. Fork repository
2. Create feature branch: `git checkout -b feature/amazing-feature`
3. Commit changes: `git commit -m 'Add amazing feature'`
4. Push branch: `git push origin feature/amazing-feature`
5. Create Pull Request

### Development guidelines

- Follow PEP 8 for Python code
- Write tests for new features
- Update documentation when necessary
- Use type hints

## 🛡️ Security

⚠️ **Warning**: This project is designed for legal penetration testing purposes only. Users must comply with laws and regulations and only use it on authorized systems.

### Best practices

- Do not commit API keys into git
- Use environment variables for sensitive data
- Audit template before using
- Limit API access permissions

## 📝 Changelog

### v1.0.0 (2024-01-xx)

- Initial release
- Basic AI agent with LangChain
- RAG integration with ChromaDB
- Basic API endpoints
- Nuclei validation integration

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙋‍♂️ Support

- 📧 Email: support@example.com
- 🐛 Issues: [GitHub Issues](https://github.com/your-username/nuclei-ai-agent/issues)
- 📖 Documentation: [Wiki](https://github.com/your-username/nuclei-ai-agent/wiki)
- 💬 Discord: [Community Server](https://discord.gg/your-server)

## 🏆 Credits

- [Nuclei](https://github.com/projectdiscovery/nuclei) - Vulnerability scanner
- [LangChain](https://github.com/langchain-ai/langchain) - AI framework
- [ChromaDB](https://github.com/chroma-core/chroma) - Vector database
- [FastAPI](https://github.com/tiangolo/fastapi) - Web framework

---

⭐ If this project is useful, please give us a star on GitHub!

**Made with ❤️ for the cybersecurity community**
