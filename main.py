#!/usr/bin/env python3
"""Main entry point for the application"""

import os
import sys

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    import uvicorn
    from src.web.app import app
    
    port = int(os.getenv("PORT", 8000))
    
    print(f"Starting server on port {port}...")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info",
        access_log=True
    )