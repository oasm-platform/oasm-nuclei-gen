#!/bin/bash

# Nuclei AI Agent Template Generator - Startup Script
# This script initializes and runs the Nuclei AI Agent application

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="$PROJECT_ROOT/venv"
LOG_DIR="$PROJECT_ROOT/logs"
RAG_DATA_DIR="$PROJECT_ROOT/rag_data"

# Functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

# Check if Python is available
check_python() {
    if command -v python3 &> /dev/null; then
        PYTHON_CMD="python3"
    elif command -v python &> /dev/null; then
        PYTHON_CMD="python"
    else
        log_error "Python is not installed or not in PATH"
        exit 1
    fi
    
    log_info "Using Python: $PYTHON_CMD"
}

# Create virtual environment if it doesn't exist
setup_venv() {
    if [ ! -d "$VENV_DIR" ]; then
        log_step "Creating virtual environment..."
        $PYTHON_CMD -m venv "$VENV_DIR"
    fi
    
    log_step "Activating virtual environment..."
    source "$VENV_DIR/bin/activate"
    
    # Upgrade pip
    pip install --upgrade pip
}

# Install dependencies
install_dependencies() {
    log_step "Installing Python dependencies..."
    if [ -f "$PROJECT_ROOT/requirements.txt" ]; then
        pip install -r "$PROJECT_ROOT/requirements.txt"
    else
        log_error "requirements.txt not found!"
        exit 1
    fi
}

# Check if Nuclei is installed
check_nuclei() {
    if command -v nuclei &> /dev/null; then
        NUCLEI_VERSION=$(nuclei -version 2>&1 | head -1)
        log_info "Nuclei found: $NUCLEI_VERSION"
    else
        log_warn "Nuclei not found in PATH. Please install Nuclei:"
        echo "  - Go: go install -v github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest"
        echo "  - Binary: Download from https://github.com/projectdiscovery/nuclei/releases"
        echo "  - Package manager: apt install nuclei / brew install nuclei"
        read -p "Continue without Nuclei? (y/N): " -r
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
}

# Create necessary directories
create_directories() {
    log_step "Creating necessary directories..."
    mkdir -p "$LOG_DIR"
    mkdir -p "$RAG_DATA_DIR"
    mkdir -p "$PROJECT_ROOT/chroma_db"
}

# Setup configuration files
setup_config() {
    log_step "Checking configuration files..."
    
    # Check if config files exist
    if [ ! -f "$PROJECT_ROOT/config/config.yaml" ]; then
        log_error "config/config.yaml not found!"
        exit 1
    fi
    
    if [ ! -f "$PROJECT_ROOT/config/secrets.yaml" ]; then
        log_warn "config/secrets.yaml not found. You need to configure API keys."
        echo "Please copy config/secrets.yaml.example to config/secrets.yaml and fill in your API keys."
    fi
}

# Initialize RAG data
init_rag_data() {
    log_step "Checking RAG data..."
    
    if [ ! -d "$RAG_DATA_DIR/nuclei-templates" ] || [ -z "$(ls -A "$RAG_DATA_DIR/nuclei-templates" 2>/dev/null)" ]; then
        log_warn "No Nuclei templates found for RAG. Setting up sample templates..."
        
        cd "$PROJECT_ROOT"
        $PYTHON_CMD scripts/ingest_data.py --setup-samples
        
        log_info "Sample templates created. For production, consider downloading official templates:"
        echo "  git clone https://github.com/projectdiscovery/nuclei-templates.git $RAG_DATA_DIR/nuclei-templates"
    else
        log_info "RAG templates directory exists"
    fi
}

# Load templates into vector database
load_templates() {
    log_step "Loading templates into vector database..."
    
    cd "$PROJECT_ROOT"
    $PYTHON_CMD scripts/ingest_data.py --templates-dir "$RAG_DATA_DIR/nuclei-templates"
}

# Start the application
start_app() {
    log_step "Starting Nuclei AI Agent..."
    
    cd "$PROJECT_ROOT"
    
    # Set environment variables
    export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"
    
    # Start the FastAPI server
    log_info "Server starting at http://localhost:8000"
    log_info "API documentation available at http://localhost:8000/docs"
    log_info "Press Ctrl+C to stop the server"
    
    $PYTHON_CMD -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
}

# Show help
show_help() {
    echo "Nuclei AI Agent Template Generator - Startup Script"
    echo ""
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --help, -h          Show this help message"
    echo "  --setup-only        Only setup environment, don't start the server"
    echo "  --skip-deps         Skip dependency installation"
    echo "  --skip-rag          Skip RAG data initialization"
    echo "  --dev               Start in development mode with auto-reload"
    echo ""
    echo "Environment Setup:"
    echo "  1. Creates Python virtual environment"
    echo "  2. Installs dependencies from requirements.txt"
    echo "  3. Checks for Nuclei installation"
    echo "  4. Creates necessary directories"
    echo "  5. Initializes RAG data"
    echo "  6. Loads templates into vector database"
    echo "  7. Starts the FastAPI server"
}

# Main function
main() {
    local setup_only=false
    local skip_deps=false
    local skip_rag=false
    local dev_mode=false
    
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --help|-h)
                show_help
                exit 0
                ;;
            --setup-only)
                setup_only=true
                shift
                ;;
            --skip-deps)
                skip_deps=true
                shift
                ;;
            --skip-rag)
                skip_rag=true
                shift
                ;;
            --dev)
                dev_mode=true
                shift
                ;;
            *)
                log_error "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done
    
    log_info "Starting Nuclei AI Agent Template Generator setup..."
    log_info "Project root: $PROJECT_ROOT"
    
    # Change to project directory
    cd "$PROJECT_ROOT"
    
    # Setup steps
    check_python
    setup_venv
    
    if [ "$skip_deps" = false ]; then
        install_dependencies
    fi
    
    check_nuclei
    create_directories
    setup_config
    
    if [ "$skip_rag" = false ]; then
        init_rag_data
        load_templates
    fi
    
    if [ "$setup_only" = false ]; then
        start_app
    else
        log_info "Setup completed. Run without --setup-only to start the server."
    fi
}

# Run main function
main "$@"