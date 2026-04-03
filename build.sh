#!/bin/bash
# Build script for Render - builds frontend and copies to backend

echo "📦 Installing frontend dependencies..."
cd frontend
yarn install

echo "🔨 Building frontend..."
REACT_APP_BACKEND_URL="" yarn build

echo "📁 Copying build to backend/static..."
rm -rf ../backend/static
cp -r build ../backend/static

echo "📦 Installing backend dependencies..."
cd ../backend
pip install -r requirements.txt

echo "✅ Build complete!"
