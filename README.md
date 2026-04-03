# Révision Audio ASD 🎧

Application d'apprentissage audio pour le **Titre Professionnel ASD** (Admin Sys DevOps).

## 🚀 Déploiement sur Render (1 seule app)

### Étape 1 : Base de données MongoDB (gratuit)

1. Va sur [cloud.mongodb.com](https://cloud.mongodb.com)
2. Crée un compte et un cluster gratuit (M0)
3. Dans "Database Access" → Crée un utilisateur
4. Dans "Network Access" → Add IP → **"Allow Access from Anywhere"** (0.0.0.0/0)
5. Clique "Connect" → "Connect your application" → Copie l'URL

Format : `mongodb+srv://USERNAME:PASSWORD@cluster.xxxxx.mongodb.net/revision_asd`

### Étape 2 : Déployer sur Render

1. Va sur [render.com](https://render.com) → **New** → **Web Service**
2. Connecte ton repo GitHub `facto974/revision-audio-asd`
3. Configure :

| Paramètre | Valeur |
|-----------|--------|
| **Name** | `revision-audio-asd` |
| **Root Directory** | *(laisser vide)* |
| **Runtime** | `Python 3` |
| **Build Command** | `chmod +x build.sh && ./build.sh` |
| **Start Command** | `cd backend && uvicorn server:app --host 0.0.0.0 --port $PORT` |

4. **Environment Variables** (bouton "Advanced") :
   ```
   MONGO_URL = mongodb+srv://USERNAME:PASSWORD@cluster.xxxxx.mongodb.net/revision_asd
   DB_NAME = revision_asd
   ```

5. Clique **Create Web Service**

### ✅ C'est prêt !

Ton app sera disponible sur `https://revision-audio-asd.onrender.com`

---

## Fonctionnalités

- 🎯 **5 sections de cours** : Méthode IA, IaC, Docker/CI-CD, Monitoring, Questions Jury
- 🔊 **Lecture audio** gratuite (Web Speech Synthesis)
- ⚡ **Contrôles** : Play/Pause/Stop, Vitesse 0.5x-2x, Voix française
- 📊 **Suivi progression** sauvegardé

---

## Installation locale

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

---

Bonne chance pour ton titre pro ASD ! 🚀
