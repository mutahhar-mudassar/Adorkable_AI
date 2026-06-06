#!/usr/bin/env python3
"""
Simple startup script for Adorkable AI Backend
Handles Python path correctly
"""
import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Now import and run
from backend.main import app
import uvicorn

if __name__ == "__main__":
    print("🚀 Starting Adorkable AI Backend...")
    print("📡 API will be available at: http://127.0.0.1:8000")
    print("📖 API Docs at: http://127.0.0.1:8000/docs")
    print("\n✨ Press CTRL+C to stop\n")
    
    uvicorn.run(
        "backend.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        reload_dirs=[project_root]
    )
