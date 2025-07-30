#!/bin/bash
# Build frontend for production

set -e

echo "Building frontend for production..."

# Change to frontend directory
cd frontend

# Install dependencies
echo "Installing dependencies..."
npm install

# Build production bundle
echo "Building production bundle..."
npm run build

echo "Frontend build complete!"
echo "The build is in frontend/build/"

# The backend will automatically serve the frontend from the build directory