# Révision Audio ASD — TopGainersCryptoProject 🎧

Support de révision audio pour présenter le projet **TopGainersCryptoProject** devant le jury du Titre Professionnel ASD (Admin Sys DevOps).

## 🚀 Déploiement sur Render (1 seule app)

### Étape 1 : Base de données MongoDB (gratuit, suivi de progression)
1. Va sur [cloud.mongodb.com](https://cloud.mongodb.com)
2. Crée un compte et un cluster gratuit (M0)
3. Dans "Database Access" → Crée un utilisateur
4. Dans "Network Access" → Add IP → **Allow Access from Anywhere** (0.0.0.0/0)
5. Copie l'URL de connexion : `mongodb+srv://USER:PASS@cluster.xxxxx.mongodb.net/revision_asd`

### Étape 2 : Déployer sur Render
1. Va sur [render.com](https://render.com) → **New** → **Web Service**
2. Connecte ton repo `facto974/revision-audio-asd`
3. Configure :

| Paramètre | Valeur |
|-----------|--------|
| Name | `revision-audio-asd` |
| Root Directory | *(vide)* |
| Runtime | `Python 3` |
| Build Command | `chmod +x build.sh && ./build.sh` |
| Start Command | `cd backend && uvicorn server:app --host 0.0.0.0 --port $PORT` |

4. Environment Variables (Advanced) :
   ```
   MONGO_URL = mongodb+srv://USER:PASS@cluster.xxxxx.mongodb.net/revision_asd
   DB_NAME = revision_asd
   ```
5. Clique **Create Web Service**

Ton app sera disponible sur `https://revision-audio-asd.onrender.com`

## 📚 Contenu de révision
Le support couvre les 11 compétences du REAC ASD à travers 5 sections :
1. Introduction & Présentation du projet TopGainersCryptoProject
2. Architecture technique (Streamlit, PostgreSQL, CoinGecko, flux de données)
3. Docker, CI/CD et Déploiement (Dockerfile, Compose, GHCR, Terraform, AWS, k3s)
4. Monitoring & Supervision (Prometheus, Grafana, métriques, alertes)
5. Questions du jury & Réponses préparées

## 🔧 Installation locale
```bash
# Terminal 1 - Backend
cd backend
pip install -r requirements.txt
uvicorn server:app --reload --port 8001

# Terminal 2 - Frontend
cd frontend
yarn install
yarn start
```
→ http://localhost:3000

Bonne chance pour ton titre pro ASD ! 🚀
