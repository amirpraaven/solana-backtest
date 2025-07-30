#!/bin/sh
# Startup script for Railway deployment

echo "Starting Solana Backtest API..."
echo "PORT: ${PORT:-8000}"
echo "Environment variables configured"

# Run the application
exec uvicorn src.web.app:app --host 0.0.0.0 --port ${PORT:-8000}