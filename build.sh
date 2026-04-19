#!/bin/bash
# Build script for Render - builds React frontend (with CRACO) and copies to Django static
set -e  # Stop on any error

echo "📦 Installing frontend dependencies..."

cd frontend

# Use Yarn since your project is configured for it (better consistency)
yarn install --frozen-lockfile

echo "🔨 Building frontend..."
# Clear REACT_APP_BACKEND_URL or set it if needed for production
REACT_APP_BACKEND_URL="" yarn build

echo "📁 Copying build output to backend/static..."
rm -rf ../backend/static
mkdir -p ../backend/static
cp -r build/* ../backend/static/

echo "📦 Installing backend dependencies..."
cd ../backend
pip install -r requirements.txt --upgrade

echo "✅ Build completed successfully!"
