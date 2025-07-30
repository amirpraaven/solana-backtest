"""Minimal app entry point for Railway deployment"""
import os
import sys
from pathlib import Path

# Add the project root to Python path
root_path = Path(__file__).parent
sys.path.insert(0, str(root_path))

print(f"Python version: {sys.version}")
print(f"Working directory: {os.getcwd()}")
print(f"Python path: {sys.path}")
print(f"PORT environment variable: {os.getenv('PORT', 'NOT SET')}")

try:
    # Try importing FastAPI first
    from fastapi import FastAPI
    print("✓ FastAPI imported successfully")
    
    # Create a minimal app for testing
    app = FastAPI(title="Solana Backtest - Minimal")
    
    @app.get("/health/simple")
    async def health_check():
        try:
            from datetime import datetime
            return {"status": "ok", "mode": "minimal", "timestamp": datetime.utcnow().isoformat()}
        except:
            return {"status": "ok", "mode": "minimal"}
    
    @app.get("/")
    async def root():
        return {"message": "Minimal app is running"}
    
    # Try importing the main app
    try:
        from src.web.app import app as main_app
        print("✓ Main app imported successfully")
        print("✓ Using full Solana Backtest API")
        app = main_app  # Use the main app if import succeeds
    except Exception as e:
        print(f"✗ Failed to import main app: {e}")
        import traceback
        print("Full traceback:")
        traceback.print_exc()
        print("! Using minimal app instead")
        
except Exception as e:
    print(f"✗ Critical error during import: {e}")
    # Create ultra-minimal app without any imports
    import json
    
    class MinimalApp:
        async def __call__(self, scope, receive, send):
            if scope['type'] == 'http':
                if scope['path'] == '/health/simple':
                    await send({
                        'type': 'http.response.start',
                        'status': 200,
                        'headers': [[b'content-type', b'application/json']],
                    })
                    await send({
                        'type': 'http.response.body',
                        'body': json.dumps({"status": "ok", "mode": "ultra-minimal"}).encode(),
                    })
                else:
                    await send({
                        'type': 'http.response.start',
                        'status': 404,
                        'headers': [[b'content-type', b'application/json']],
                    })
                    await send({
                        'type': 'http.response.body',
                        'body': json.dumps({"error": "Not found"}).encode(),
                    })
    
    app = MinimalApp()

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    print(f"Starting server on port {port}...")
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")