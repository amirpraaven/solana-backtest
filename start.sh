#!/bin/bash

# Railway startup script
echo "Starting Solana Backtest API..."

# Set Python path
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Log environment
echo "PORT: ${PORT:-8000}"
echo "ENVIRONMENT: ${ENVIRONMENT:-production}"

# Start the application
exec uvicorn src.web.app:app --host 0.0.0.0 --port ${PORT:-8000} --log-level info