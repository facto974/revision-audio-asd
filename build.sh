#!/bin/bash
# Build script for Render - builds frontend and copies to backend

set -e  # Arrête le script en cas d'erreur

echo "📦 Installing frontend dependencies..."
cd frontend

# Solution complète pour gérer le lockfile
if [ -f yarn.lock ]; then
    # Essayer d'abord avec le lockfile existant
    if ! yarn install --frozen-lockfile --legacy-peer-deps --non-interactive; then
        echo "⚠️ Lockfile outdated, updating..."
        yarn install --legacy-peer-deps --non-interactive
        # Sauvegarder le nouveau lockfile
        git add yarn.lock
        git commit -m "chore: update yarn.lock [skip ci]" || echo "No changes to commit"
    fi
else
    # Si pas de lockfile, faire une installation complète
    yarn install --legacy-peer-deps --non-interactive
fi

# Installer les dépendances critiques si elles manquent
if ! yarn list date-fns >/dev/null 2>&1; then
    yarn add date-fns@^3.0.0 --non-interactive
fi

if ! yarn list @babel/core >/dev/null 2>&1; then
    yarn add @babel/core@^7.25.2 --non-interactive
fi

if ! yarn list react-is >/dev/null 2>&1; then
    yarn add react-is@^18.2.0 --non-interactive
fi

if ! yarn list typescript >/dev/null 2>&1; then
    yarn add typescript@^4.9.0 --dev --non-interactive
fi

if ! yarn list @types/node >/dev/null 2>&1; then
    yarn add @types/node@latest --dev --non-interactive
fi

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
