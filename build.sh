#!/bin/bash
set -e

echo "=== Building Solana Backtest System ==="

# Install Python dependencies
echo "Installing Python dependencies..."
pip install -r requirements.txt

# Build frontend
echo "Building frontend..."
cd frontend

# Copy .env if it exists
if [ -f .env ]; then
    echo "Using frontend .env file"
else
    echo "No frontend .env file found"
fi

# Install frontend dependencies
npm install

# Build frontend
npm run build

cd ..

echo "=== Build complete ==="