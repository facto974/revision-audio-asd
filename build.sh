#!/bin/bash
# Build script for Render - builds frontend and copies to backend
set -e  # Arrête le script en cas d'erreur

echo "📦 Installing frontend dependencies..."
cd frontend

# Installation des dépendances avec gestion des peer dependencies
npm ci || npm install --legacy-peer-deps

# Installation des dépendances critiques spécifiques
npm install date-fns@^3.0.0 @babel/core@^7.25.2 react-is@^18.2.0 typescript@^4.9.0 --save-dev

echo "🔨 Building frontend..."
REACT_APP_BACKEND_URL="" npm run build

echo "📁 Copying build to backend/static..."
rm -rf ../backend/static
mkdir -p ../backend/static
cp -r build/* ../backend/static/

echo "📦 Installing backend dependencies..."
cd ../backend
pip install -r requirements.txt --upgrade

echo "✅ Build complete!"
