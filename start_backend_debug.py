#!/usr/bin/env python3
"""
Debug startup script for Adorkable AI Backend
Logs all errors to file
"""
import sys
import os
import logging
import traceback

# Setup logging to file
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('backend_debug.log', mode='w'),
        logging.StreamHandler(sys.stdout)
    ]
)

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

logger = logging.getLogger(__name__)

try:
    logger.info("🚀 Starting Adorkable AI Backend (Debug Mode)...")
    logger.info(f"Python path: {sys.path}")
    
    # Import and run
    from backend.main import app
    import uvicorn
    
    logger.info("✅ App imported successfully")
    logger.info("📡 Starting server on http://127.0.0.1:8000")
    
    uvicorn.run(
        "backend.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        reload_dirs=[project_root],
        log_level="debug"
    )
    
except Exception as e:
    logger.error(f"❌ FAILED TO START: {type(e).__name__}: {e}")
    logger.error(traceback.format_exc())
    raise
