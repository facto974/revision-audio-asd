# Révision Audio ASD — TopGainersCryptoProject ���

Support de révision audio pour présenter le projet **TopGainersCryptoProject** devant le jury du Titre Professionnel ASD (Admin Sys DevOps).

## ��� Déploiement sur Vercel (frontend statique)

Le frontend React est déployé sur Vercel en tant que site statique. Le backend FastAPI (suivi de progression en MongoDB) doit être hébergé séparément (ex: Render, Railway, etc.) ou le suivi de progression peut être désactivé pour une démo 100% statique.

### Étape 1 : Connecter le repo à Vercel
1. Va sur [vercel.com](https://vercel.com)
2. Clique sur **Add New Project**
3. Importe ton dépôt GitHub `facto974/revision-audio-asd`
4. Dans les réglages du build, laisse les valeurs par défaut ou configure :

| Paramètre | Valeur |
|-----------|--------|
| Framework Preset | `Create React App` |
| Root Directory | `frontend` (ou laisse à la racine si vercel.json pointe vers `frontend/package.json`) |
| Build Command | `yarn build` ou `npm run build` |
| Output Directory | `build` |

5. Clique sur **Deploy**

Ton app sera disponible sur une URL de type `https://revision-audio-asd.vercel.app`

### Étape 2 : Variables d'environnement (optionnel)
Si tu utilises le backend FastAPI avec suivi de progression MongoDB, ajoute dans les **Settings → Environment Variables** de Vercel :

```
REACT_APP_BACKEND_URL = https://ton-backend.onrender.com
```

Puis redéploye.

## 📚 Contenu de révision
Le support couvre les 11 compétences du REAC ASD à travers 5 sections :
1. Introduction & Présentation du projet TopGainersCryptoProject
2. Architecture technique (Streamlit, PostgreSQL, CoinGecko, flux de données)
3. Docker, CI/CD et Déploiement (Dockerfile, Compose, GHCR, Terraform, AWS, k3s)
4. Monitoring & Supervision (Prometheus, Grafana, métriques, alertes)
5. Questions du jury & Réponses préparées

## 🔧 Installation locale
```bash
# Terminal 1 - Backend (FastAPI + MongoDB)
cd backend
pip install -r requirements.txt
uvicorn server:app --reload --port 8001

# Terminal 2 - Frontend (React)
cd frontend
yarn install
yarn start
```
→ http://localhost:3000

Bonne chance pour ton titre pro ASD ! 🚀
