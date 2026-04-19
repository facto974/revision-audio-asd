#!/bin/bash
# Build script for Render - builds frontend and copies to backend

set -e  # Arrête le script en cas d'erreur

echo "📦 Installing frontend dependencies..."
cd frontend

# D'abord essayer avec le lockfile existant
if ! yarn install --frozen-lockfile --legacy-peer-deps; then
    echo "⚠️ Lockfile outdated, updating dependencies..."
    yarn install --legacy-peer-deps
fi

# Installer les dépendances manquantes spécifiques
yarn add date-fns@^3.0.0
yarn add @babel/core@^7.25.2
yarn add react-is@^18.2.0
yarn add typescript@^4.9.0 --dev
yarn add @types/node@latest --dev

echo "🔨 Building frontend..."
REACT_APP_BACKEND_URL="" yarn build

echo "📁 Copying build to backend/static..."
rm -rf ../backend/static
mkdir -p ../backend/static
cp -r build/* ../backend/static/

echo "📦 Installing backend dependencies..."
cd ../backend
pip install -r requirements.txt --upgrade

echo "✅ Build complete!"
