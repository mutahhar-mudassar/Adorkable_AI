#!/usr/bin/env python3
"""Simple startup script on port 8004"""
import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from backend.main import app
import uvicorn

if __name__ == "__main__":
    print("🚀 Starting Adorkable AI Backend on port 8004...")
    print("📡 API: http://127.0.0.1:8004")
    uvicorn.run(app, host="127.0.0.1", port=8004, log_level="info")
