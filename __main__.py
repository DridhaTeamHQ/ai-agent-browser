"""
Entry Point - Autonomous News Agent.

Run this file to start the agent.
"""

import asyncio
import os
from dotenv import load_dotenv
from core.orchestrator import Orchestrator
from utils.logger import get_logger

# Load environment variables
load_dotenv()

def main():
    logger = get_logger("main")
    
    # Check environment
    required_vars = ["OPENAI_API_KEY", "CMS_URL", "CMS_EMAIL", "CMS_PASSWORD"]
    missing = [var for var in required_vars if not os.getenv(var)]
    
    if missing:
        logger.critical(f"❌ Missing environment variables: {', '.join(missing)}")
        return
        
    # Start Orchestrator
    try:
        orchestrator = Orchestrator()
        asyncio.run(orchestrator.run())
    except KeyboardInterrupt:
        logger.info("🛑 Manually stopped")
    except Exception as e:
        logger.critical(f"🔥 Unhandled exception: {e}", exc_info=True)

if __name__ == "__main__":
    main()
