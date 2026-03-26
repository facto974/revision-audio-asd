# Révision Audio ASD 🎧

Application d'apprentissage audio pour le **Titre Professionnel ASD** (Admin Sys DevOps).

## Fonctionnalités

- 🎯 **5 sections de cours** : Méthode IA, IaC (Terraform/Ansible), Docker/CI-CD, Monitoring, Questions Jury
- 🔊 **Lecture audio** via Web Speech Synthesis (gratuit, navigateur)
- ⚡ **Contrôles** : Play/Pause/Stop, Vitesse 0.5x-2x, Sélection voix
- 📊 **Suivi progression** avec sauvegarde
- 🎨 **Interface claire** avec blocs colorés par type

## Installation locale

### Prérequis
- Node.js 18+
- Python 3.9+
- MongoDB

### Backend

```bash
cd backend
pip install -r requirements.txt

# Créer .env avec :
# MONGO_URL=mongodb://localhost:27017
# DB_NAME=revision_asd
# CORS_ORIGINS=*

uvicorn server:app --reload --port 8001
```

### Frontend

```bash
cd frontend
yarn install

# Créer .env avec :
# REACT_APP_BACKEND_URL=http://localhost:8001

yarn start
```

## Déploiement gratuit

| Service | Gratuit | Usage |
|---------|---------|-------|
| [Vercel](https://vercel.com) | ✅ | Frontend |
| [Render](https://render.com) | ✅ 750h/mois | Backend |
| [MongoDB Atlas](https://cloud.mongodb.com) | ✅ 512MB | Base de données |

## Structure

```
├── backend/
│   ├── server.py      # API FastAPI + contenu cours
│   └── requirements.txt
├── frontend/
│   ├── src/App.js     # Application React
│   └── src/components/ui/  # Composants Shadcn
└── memory/
    └── PRD.md         # Documentation projet
```

## Licence

MIT - Libre d'utilisation

---

Bonne chance pour ton titre pro ASD ! 🚀
