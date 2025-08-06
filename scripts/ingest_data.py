"""
Data ingestion script for loading Nuclei templates into vector database
"""
import asyncio
import argparse
import logging
import sys
from pathlib import Path
from typing import List, Optional
import yaml

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from app.services.vector_db import VectorDBService
from app.core.rag_engine import RAGEngine


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def load_config(config_path: Optional[Path] = None) -> dict:
    if not config_path:
        config_path = Path("config/config.yaml")
    
    if config_path.exists():
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    else:
        logger.error(f"Configuration file not found: {config_path}")
        return {}


async def ingest_nuclei_templates(
    templates_dir: Path,
    config: dict,
    force_reload: bool = False
) -> int:
    logger.info(f"Starting template ingestion from: {templates_dir}")
    
    # Initialize vector database service
    vector_db_service = VectorDBService(config.get("vector_db", {}))
    await vector_db_service.initialize()
    
    # Check if collection already has data
    stats = await vector_db_service.get_collection_stats()
    existing_count = stats.get("total_documents", 0)
    
    if existing_count > 0 and not force_reload:
        logger.info(f"Vector database already contains {existing_count} documents")
        user_input = input("Do you want to reload all templates? (y/N): ")
        if user_input.lower() != 'y':
            logger.info("Skipping ingestion")
            return existing_count
        else:
            logger.info("Clearing existing collection...")
            await vector_db_service.delete_collection()
            await vector_db_service.initialize()
    elif force_reload and existing_count > 0:
        logger.info(f"Force reload enabled. Clearing existing {existing_count} documents...")
        await vector_db_service.delete_collection()
        await vector_db_service.initialize()
    
    # Load templates
    count = await vector_db_service.bulk_load_templates(templates_dir)
    
    logger.info(f"Ingestion completed. Total templates loaded: {count}")
    return count


async def validate_templates_directory(templates_dir: Path) -> bool:
    if not templates_dir.exists():
        logger.error(f"Templates directory not found: {templates_dir}")
        return False
    
    # Count YAML files
    yaml_files = list(templates_dir.rglob("*.yaml")) + list(templates_dir.rglob("*.yml"))
    
    if not yaml_files:
        logger.error(f"No YAML files found in: {templates_dir}")
        return False
    
    logger.info(f"Found {len(yaml_files)} YAML files in templates directory")
    
    # Validate a few sample templates
    sample_files = yaml_files[:5]  # Check first 5 files
    valid_count = 0
    
    for template_file in sample_files:
        try:
            with open(template_file, 'r', encoding='utf-8') as f:
                template_data = yaml.safe_load(f.read())
                
            # Check if it's a valid Nuclei template structure
            if isinstance(template_data, dict) and 'id' in template_data and 'info' in template_data:
                valid_count += 1
            else:
                logger.warning(f"Invalid template structure in: {template_file}")
                
        except Exception as e:
            logger.warning(f"Error reading template {template_file}: {e}")
    
    if valid_count == 0:
        logger.error("No valid Nuclei templates found in sample files")
        return False
    
    logger.info(f"Validated {valid_count}/{len(sample_files)} sample templates")
    return True


async def setup_sample_templates(rag_data_dir: Path):
    nuclei_templates_dir = rag_data_dir / "nuclei-templates"
    
    if nuclei_templates_dir.exists():
        logger.info("Nuclei templates directory already exists")
        return
    
    logger.info("Setting up sample templates directory...")
    nuclei_templates_dir.mkdir(parents=True, exist_ok=True)
    
    # Create sample templates
    sample_templates = [
        {
            "filename": "sql-injection-login.yaml",
            "content": """id: sql-injection-login

info:
  name: SQL Injection in Login Form
  author: ai-agent
  severity: high
  description: Detects SQL injection vulnerabilities in login forms
  tags:
    - sqli
    - login
    - injection

http:
  - method: POST
    path:
      - "{{BaseURL}}/login"
      - "{{BaseURL}}/admin/login"
    
    headers:
      Content-Type: application/x-www-form-urlencoded
    
    body: |
      username=admin' OR '1'='1' -- &password=test
    
    matchers:
      - type: word
        words:
          - "welcome"
          - "dashboard"
          - "admin panel"
        condition: or
      
      - type: status
        status:
          - 200
          - 302
"""
        },
        {
            "filename": "xss-reflected.yaml",
            "content": """id: xss-reflected

info:
  name: Reflected Cross-Site Scripting
  author: ai-agent  
  severity: medium
  description: Detects reflected XSS vulnerabilities
  tags:
    - xss
    - reflected
    - injection

http:
  - method: GET
    path:
      - "{{BaseURL}}/search?q=<script>alert('xss')</script>"
      - "{{BaseURL}}/page?name=<img src=x onerror=alert('xss')>"
    
    matchers:
      - type: word
        words:
          - "<script>alert('xss')</script>"
          - "<img src=x onerror=alert('xss')>"
        part: body
        condition: or
"""
        }
    ]
    
    for template in sample_templates:
        template_path = nuclei_templates_dir / template["filename"]
        with open(template_path, 'w', encoding='utf-8') as f:
            f.write(template["content"])
    
    logger.info(f"Created {len(sample_templates)} sample templates")


async def main():
    parser = argparse.ArgumentParser(description="Ingest Nuclei templates into vector database")
    parser.add_argument(
        "--templates-dir", 
        type=Path,
        default=Path("rag_data/nuclei-templates"),
        help="Path to Nuclei templates directory"
    )
    parser.add_argument(
        "--config", 
        type=Path,
        help="Path to configuration file"
    )
    parser.add_argument(
        "--force-reload", 
        action="store_true",
        help="Force reload all templates (clear existing data)"
    )
    parser.add_argument(
        "--setup-samples", 
        action="store_true",
        help="Setup sample templates if directory doesn't exist"
    )
    
    args = parser.parse_args()
    
    try:
        # Load configuration
        config = await load_config(args.config)
        if not config:
            logger.error("Failed to load configuration")
            return 1
        
        # Setup samples if requested
        if args.setup_samples:
            await setup_sample_templates(Path("rag_data"))
        
        # Validate templates directory
        if not await validate_templates_directory(args.templates_dir):
            logger.error("Templates directory validation failed")
            return 1
        
        # Ingest templates
        count = await ingest_nuclei_templates(
            templates_dir=args.templates_dir,
            config=config,
            force_reload=args.force_reload
        )
        
        if count > 0:
            logger.info(f"Successfully ingested {count} templates")
            return 0
        else:
            logger.error("No templates were ingested")
            return 1
            
    except Exception as e:
        logger.error(f"Ingestion failed: {e}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
