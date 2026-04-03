# Révision Audio ASD 🎧

Application d'apprentissage audio pour le **Titre Professionnel ASD** (Admin Sys DevOps).

## 🚀 Déploiement sur Render

### Étape 1 : Base de données MongoDB (gratuit)

1. Va sur [cloud.mongodb.com](https://cloud.mongodb.com)
2. Crée un compte et un cluster gratuit (M0)
3. Dans "Database Access" → Crée un utilisateur
4. Dans "Network Access" → Add IP → "Allow Access from Anywhere"
5. Récupère l'URL de connexion (bouton "Connect" → "Connect your application")

URL format : `mongodb+srv://USERNAME:PASSWORD@cluster.xxxxx.mongodb.net/revision_asd`

### Étape 2 : Déployer le Backend

1. [render.com](https://render.com) → New → **Web Service**
2. Connect ton repo GitHub `facto974/revision-audio-asd`
3. Configure :
   - **Name** : `revision-asd-api`
   - **Root Directory** : `backend`
   - **Runtime** : `Python 3`
   - **Build Command** : `pip install -r requirements.txt`
   - **Start Command** : `uvicorn server:app --host 0.0.0.0 --port $PORT`

4. **Environment Variables** (bouton "Advanced") :
   ```
   MONGO_URL = mongodb+srv://USERNAME:PASSWORD@cluster.xxxxx.mongodb.net/revision_asd
   DB_NAME = revision_asd
   CORS_ORIGINS = *
   ```

5. **Create Web Service** → Attends que ça déploie (~2-3 min)
6. Note l'URL du backend (ex: `https://revision-asd-api.onrender.com`)

### Étape 3 : Déployer le Frontend

1. [render.com](https://render.com) → New → **Web Service**
2. Connect le même repo GitHub
3. Configure :
   - **Name** : `revision-asd-frontend`
   - **Root Directory** : `frontend`
   - **Runtime** : `Node`
   - **Build Command** : `yarn install && yarn build`
   - **Start Command** : `npx serve -s build -l $PORT`

4. **Environment Variables** :
   ```
   REACT_APP_BACKEND_URL = https://revision-asd-api.onrender.com
   ```
   ⚠️ Remplace par l'URL de TON backend de l'étape 2

5. **Create Web Service**

---

## ✅ C'est prêt !

Ton application sera disponible sur l'URL du frontend (ex: `https://revision-asd-frontend.onrender.com`)

---

## Fonctionnalités

- 🎯 **5 sections de cours** : Méthode IA, IaC, Docker/CI-CD, Monitoring, Questions Jury
- 🔊 **Lecture audio** gratuite (Web Speech Synthesis)
- ⚡ **Contrôles** : Play/Pause/Stop, Vitesse 0.5x-2x, Voix française
- 📊 **Suivi progression** sauvegardé

---

## Installation locale

```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn server:app --reload --port 8001

# Frontend (autre terminal)
cd frontend
yarn install
yarn start
```

→ http://localhost:3000

---

Bonne chance pour ton titre pro ASD ! 🚀
