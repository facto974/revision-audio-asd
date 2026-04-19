#!/bin/bash
# Build script for Render - builds frontend and copies to backend

echo "📦 Installing frontend dependencies..."
cd frontend
yarn install

yarn add date-fns@^3.0.0
yarn add @babel/core@^7.0.0
yarn add react-is@^18.0.0
yarn add --dev @types/node

echo "🔨 Building frontend..."
REACT_APP_BACKEND_URL="" yarn build

echo "📁 Copying build to backend/static..."
rm -rf ../backend/static
cp -r build ../backend/static

echo "📦 Installing backend dependencies..."
cd ../backend
pip install -r requirements.txt

echo "✅ Build complete!"
