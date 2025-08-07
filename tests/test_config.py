"""
Test script to verify environment configuration
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from app.core.agent import NucleiAgent

async def test_config():
    """Test the configuration loading"""
    print("Testing environment configuration...")
    print("=" * 50)
    
    # Load environment variables
    load_dotenv()
    
    # Check critical environment variables
    print("Environment Variables:")
    print(f"LLM_PROVIDER: {os.getenv('LLM_PROVIDER', 'NOT SET')}")
    print(f"GEMINI_API_KEY: {'SET' if os.getenv('GEMINI_API_KEY') else 'NOT SET'}")
    print(f"VECTOR_DB_MODE: {os.getenv('VECTOR_DB_MODE', 'NOT SET')}")
    print(f"VECTOR_DB_PERSIST_DIRECTORY: {os.getenv('VECTOR_DB_PERSIST_DIRECTORY', 'NOT SET')}")
    print()
    
    try:
        # Initialize agent
        print("Initializing Nuclei Agent...")
        agent = NucleiAgent()
        
        print("Configuration loaded successfully!")
        print(f"LLM Provider: {agent.config['llm']['provider']}")
        print(f"LLM Model: {agent.config['llm']['model']}")
        print(f"Vector DB Mode: {agent.config['vector_db']['mode']}")
        print(f"Vector DB Directory: {agent.config['vector_db']['persist_directory']}")
        
        # Test agent status
        print("\nTesting agent status...")
        status = await agent.get_agent_status()
        print(f"Agent Status: {status}")
        
        print("\n✅ Configuration test completed successfully!")
        
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_config())