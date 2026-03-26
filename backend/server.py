from fastapi import FastAPI, APIRouter
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
import uuid
from datetime import datetime, timezone


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")


# Define Models
class StatusCheck(BaseModel):
    model_config = ConfigDict(extra="ignore")
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_name: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class StatusCheckCreate(BaseModel):
    client_name: str

class CourseSection(BaseModel):
    id: str
    title: str
    icon: str
    content: List[dict]

class UserProgress(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    section_id: str
    completed: bool = False
    last_position: int = 0
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# Course content - transformed into explanatory course format
COURSE_CONTENT = [
    {
        "id": "intro",
        "title": "Introduction & Méthode IA",
        "icon": "Brain",
        "content": [
            {
                "type": "intro",
                "text": "Bienvenue dans cette fiche de révision pour le Titre Professionnel ASD. Je vais t'expliquer chaque notion comme si on était en cours ensemble."
            },
            {
                "type": "concept",
                "title": "La philosophie de l'IA en DevOps",
                "text": "Commençons par comprendre comment utiliser l'IA de manière professionnelle. Retiens cette citation importante : L'IA n'est pas un copilote magique. C'est un junior qui code vite mais qui se trompe souvent. Ton rôle d'Admin Sys DevOps, c'est d'être le senior qui relit, comprend, teste et valide."
            },
            {
                "type": "method",
                "title": "La méthode IA en 5 étapes",
                "text": "Voici la méthode que tu dois maîtriser. Première étape : définir un objectif clair. Avant même de toucher au clavier, tu dois savoir quelle techno tu utilises, quelles sont tes contraintes, et quel résultat tu attends. C'est comme un plombier qui mesure avant de couper le tuyau."
            },
            {
                "type": "method",
                "text": "Deuxième étape : formuler le besoin correctement. Quand tu parles à l'IA, donne-lui le contexte, montre-lui ton code existant, donne un exemple d'entrée et de sortie attendue. C'est exactement comme rédiger un bon ticket Jira : titre précis, logs, version, comportement attendu."
            },
            {
                "type": "method",
                "text": "Troisième étape : récupérer le code généré et le copier dans un fichier de test. Jamais directement en production ! On ne merge pas sans review en équipe, c'est pareil ici."
            },
            {
                "type": "method",
                "text": "Quatrième étape : lire, comprendre et adapter. Tu dois être capable d'expliquer chaque bloc avec tes propres mots. Vérifie la sécurité, les performances, les versions, les contraintes métier. Tu ne signes pas un document que tu n'as pas relu."
            },
            {
                "type": "method",
                "text": "Cinquième étape : tester et corriger. Commence par les cas simples, puis les cas limites. Si ça bug, explique à l'IA ce qui se passe et itère. Un développeur sans tests, c'est comme un électricien qui n'utilise pas le multimètre."
            },
            {
                "type": "jury",
                "title": "Attention : question piège du jury",
                "text": "Le jury pourrait te demander : Vous avez utilisé l'IA, donc vous ne comprenez pas votre code ? Ta réponse : Non, j'ai utilisé l'IA comme outil d'accélération. Pour chaque bloc généré, j'ai appliqué ma méthode : lire, comprendre, adapter, tester. Je peux expliquer chaque ligne de mon Dockerfile, de mon main.tf, de mon pipeline CI/CD."
            }
        ]
    },
    {
        "id": "bloc1",
        "title": "Bloc 1 : Automatisation & IaC",
        "icon": "Server",
        "content": [
            {
                "type": "intro",
                "text": "Passons au premier bloc technique : l'Infrastructure as Code avec Terraform et Ansible. C'est fondamental pour ton titre pro."
            },
            {
                "type": "concept",
                "title": "Terraform vs Ansible : l'analogie imparable",
                "text": "Voici comment différencier ces deux outils. Terraform, c'est l'architecte qui construit les murs et pose les fondations. Il crée ton infrastructure : les instances EC2, les VPC, les Security Groups, les buckets S3. Ansible, c'est le décorateur qui arrive après et installe les meubles, configure les prises. Il installe Nginx, crée les utilisateurs, copie les fichiers de config."
            },
            {
                "type": "important",
                "text": "Retiens bien l'ordre : on fait toujours Terraform d'abord pour créer l'infrastructure, puis Ansible ensuite pour la configurer. C'est logique : on construit la maison avant de la meubler."
            },
            {
                "type": "technical",
                "title": "Caractéristiques de Terraform",
                "text": "Terraform utilise le langage HCL, avec des fichiers en point tf. Il est stateful, ce qui signifie qu'il garde un fichier terraform.tfstate qui mémorise l'état de ton infrastructure. Attention : ne jamais committer ce fichier dans Git ! En équipe, on le stocke sur S3 avec un lock DynamoDB. Les commandes clés sont : init pour initialiser, validate pour vérifier la syntaxe, plan pour prévisualiser les changements, apply pour appliquer, et destroy pour tout supprimer."
            },
            {
                "type": "technical",
                "title": "Caractéristiques d'Ansible",
                "text": "Ansible utilise YAML avec des fichiers playbook.yml. Il est idempotent : si tu rejoues le même playbook dix fois, tu obtiens le même résultat. C'est sa force. Les commandes essentielles : ansible all moins m ping pour tester la connexion, et ansible-playbook playbook.yml tiret tiret check pour faire un dry-run sans appliquer les changements."
            },
            {
                "type": "concept",
                "title": "Sécurisation SSH : le minimum syndical",
                "text": "Parlons maintenant de la sécurité SSH, un sujet que le jury adore. Quatre actions essentielles à connaître."
            },
            {
                "type": "security",
                "text": "Première action : désactiver le login root en SSH. Dans le fichier sshd_config, tu mets PermitRootLogin no. Pourquoi ? C'est le principe du moindre privilège. Si le compte root est compromis, tout est perdu."
            },
            {
                "type": "security",
                "text": "Deuxième action : utiliser uniquement des clés ED25519, pas de mots de passe. Tu mets PasswordAuthentication no. Un mot de passe peut être bruteforcé en quelques heures, une clé ED25519 c'est quasi impossible."
            },
            {
                "type": "security",
                "text": "Troisième action : configurer le Security Group avec un CIDR en slash 32. Tu mets cidr_blocks égal ton IP slash 32. Comme ça, seul toi peux atteindre le port 22. Surface d'attaque nulle."
            },
            {
                "type": "security",
                "text": "Quatrième action : installer fail2ban avec apt install fail2ban et configurer un jail SSH. Ça bannit automatiquement les IPs après N tentatives échouées."
            }
        ]
    },
    {
        "id": "bloc2",
        "title": "Bloc 2 : Docker & CI/CD",
        "icon": "Container",
        "content": [
            {
                "type": "intro",
                "text": "Deuxième bloc : Docker et la CI/CD avec GitHub Actions. C'est le coeur du DevOps moderne."
            },
            {
                "type": "concept",
                "title": "Dockerfile : la recette de cuisine",
                "text": "Un Dockerfile, c'est comme une recette de cuisine. L'instruction FROM, ce sont tes ingrédients de base. Les instructions RUN, ce sont les étapes de préparation. Et CMD, c'est la façon de servir le plat."
            },
            {
                "type": "technical",
                "title": "Explication ligne par ligne",
                "text": "Prenons chaque instruction. FROM python 3.9 tiret slim : on choisit une image de base légère. Le tiret slim signifie sans outils inutiles. Résultat : moins de failles de sécurité et une image plus petite."
            },
            {
                "type": "technical",
                "text": "RUN useradd app : on crée un utilisateur non-root. Règle d'or : ne jamais faire tourner un conteneur en root en production. C'est l'isolation des privilèges."
            },
            {
                "type": "technical",
                "text": "COPY requirements.txt point : on copie le fichier des dépendances AVANT le code source. Pourquoi ? Pour exploiter le cache des layers Docker. Si ton code change mais pas tes dépendances, Docker ne réinstalle pas tout."
            },
            {
                "type": "technical",
                "text": "RUN pip install moins r requirements.txt : on installe les librairies Python. C'est figé dans un layer, donc reproductible à chaque build."
            },
            {
                "type": "technical",
                "text": "EXPOSE 8501 : c'est juste de la documentation. Le vrai mapping de port se fait dans docker run moins p ou dans le docker-compose."
            },
            {
                "type": "technical",
                "text": "CMD entre crochets streamlit, run, app.py : c'est la commande par défaut, mais elle est surchargeable. ENTRYPOINT serait fixe. On utilise CMD pour garder de la flexibilité pendant les tests."
            },
            {
                "type": "concept",
                "title": "Pipeline GitHub Actions",
                "text": "La CI/CD, c'est comme une chaîne de montage automobile. On ne livre pas la voiture si une étape de contrôle qualité échoue. Voyons le flux."
            },
            {
                "type": "technical",
                "text": "Le trigger : on push branches main. Le pipeline se déclenche automatiquement à chaque push sur la branche main."
            },
            {
                "type": "technical",
                "text": "Checkout avec uses actions/checkout@v3 : le runner GitHub récupère ton code depuis le dépôt."
            },
            {
                "type": "technical",
                "text": "Les tests avec run pytest tests/ moins v : si un seul test échoue, le pipeline est bloqué. Rien ne part en production."
            },
            {
                "type": "technical",
                "text": "Build de l'image avec docker build moins t monapp dollar github.sha : on tag l'image avec le SHA du commit. Ça donne une traçabilité parfaite."
            },
            {
                "type": "technical",
                "text": "Push vers le registry avec docker push vers Docker Hub ou ECR : l'image est versionnée et déployable partout."
            }
        ]
    },
    {
        "id": "bloc3",
        "title": "Bloc 3 : Monitoring & Supervision",
        "icon": "Activity",
        "content": [
            {
                "type": "intro",
                "text": "Troisième bloc : le monitoring avec Prometheus et Grafana. Question quasi-certaine au jury !"
            },
            {
                "type": "concept",
                "title": "Les trois ports à connaître",
                "text": "Le jury adore poser cette question sur les ports. Port 8000 : c'est ton application Python qui expose l'endpoint /metrics via prometheus_client. Prometheus vient scraper ce port."
            },
            {
                "type": "technical",
                "text": "Port 9090 : c'est l'interface web de Prometheus qui centralise et stocke toutes les métriques collectées depuis le port 8000."
            },
            {
                "type": "technical",
                "text": "Port 3000 : c'est Grafana, le dashboard de visualisation. Il lit les données depuis Prometheus qui est configuré comme datasource."
            },
            {
                "type": "concept",
                "title": "Le mode PULL de Prometheus",
                "text": "Prometheus fonctionne en mode PULL, contrairement aux systèmes PUSH où les apps envoient leurs données. L'analogie : Prometheus est comme un facteur qui passe relever le courrier à heures fixes. Les applications n'ont pas besoin de savoir où envoyer leurs métriques, elles les exposent juste sur slash metrics."
            },
            {
                "type": "technical",
                "title": "Les 5 requêtes PromQL essentielles",
                "text": "Première requête : api_calls_total status égal success. Ça compte le total d'appels API réussis depuis le démarrage."
            },
            {
                "type": "technical",
                "text": "Deuxième requête : rate de api_calls_total status égal error sur 5 minutes. Ça donne le taux d'erreurs par seconde sur les 5 dernières minutes."
            },
            {
                "type": "technical",
                "text": "Troisième requête : rate de response_seconds_sum sur 5m divisé par rate de response_seconds_count sur 5m. Ça calcule le temps de réponse moyen, c'est ton SLI de latence."
            },
            {
                "type": "technical",
                "text": "Quatrième requête : db_records_total. Ça compte le nombre d'enregistrements en base SQLite."
            },
            {
                "type": "technical",
                "text": "Cinquième requête : up job égal monapp. Ça vérifie si l'app est scrapable. 1 égal OK, 0 égal coupée."
            },
            {
                "type": "concept",
                "title": "SLO, SLI, SLA : les définitions",
                "text": "Trois termes à ne pas confondre. SLI, c'est la mesure réelle. Exemple : temps de réponse moyen égal 120 millisecondes sur les 5 dernières minutes."
            },
            {
                "type": "technical",
                "text": "SLO, c'est l'objectif interne. Exemple : 99,5 pourcent des requêtes doivent répondre en moins de 200 millisecondes."
            },
            {
                "type": "technical",
                "text": "SLA, c'est le contrat client. Exemple : si la disponibilité est inférieure à 99 pourcent, on rembourse X pourcent de la facture."
            },
            {
                "type": "concept",
                "title": "Résolution d'incident en 5 étapes",
                "text": "Méthode à appliquer en cas d'incident en production. Étape 1 : OBSERVER. Tu utilises docker logs moins f container ou journalctl moins u nginx since 1h ago."
            },
            {
                "type": "technical",
                "text": "Étape 2 : ISOLER. Tu te poses les questions : depuis quand ? Quel composant ? Est-ce reproductible ? Tu vérifies avec df moins h, free moins h, ss moins tulnp grep PORT."
            },
            {
                "type": "technical",
                "text": "Étape 3 : HYPOTHÈSE. Tu identifies la cause probable. C'est de la réflexion, pas de commande."
            },
            {
                "type": "technical",
                "text": "Étape 4 : TESTER. Un seul changement à la fois ! Tu utilises ping moins c 4 8.8.8.8 ou curl moins v localhost 8501."
            },
            {
                "type": "technical",
                "text": "Étape 5 : CORRIGER. Tu appliques le fix et tu documentes. git commit moins m fix suivi d'un postmortem."
            }
        ]
    },
    {
        "id": "questions",
        "title": "Questions Jury : Réponses Flash",
        "icon": "HelpCircle",
        "content": [
            {
                "type": "intro",
                "text": "Dernière partie : les 10 questions types du jury avec les réponses flash. Entraîne-toi à les réciter !"
            },
            {
                "type": "qa",
                "question": "Question 1 : Terraform vs Ansible ?",
                "answer": "Terraform crée l'infrastructure, Ansible configure ce qui tourne dessus. Dans cet ordre."
            },
            {
                "type": "qa",
                "question": "Question 2 : Pourquoi un CIDR slash 32 sur SSH ?",
                "answer": "Moindre privilège réseau : seule mon IP peut atteindre le port 22."
            },
            {
                "type": "qa",
                "question": "Question 3 : Explique ton Dockerfile.",
                "answer": "FROM slim, user non-root, COPY requirements avant le code pour le cache, EXPOSE, CMD."
            },
            {
                "type": "qa",
                "question": "Question 4 : Pourquoi deux ports 8000 et 9090 ?",
                "answer": "8000 c'est l'endpoint métriques de mon app. 9090 c'est l'interface Prometheus qui scrappe ce 8000."
            },
            {
                "type": "qa",
                "question": "Question 5 : Pourquoi SQLite et pas PostgreSQL ?",
                "answer": "Pas de serveur séparé, adapté à un seul utilisateur. J'ai identifié la migration comme évolution future."
            },
            {
                "type": "qa",
                "question": "Question 6 : Kubernetes, pourquoi pas dans le projet ?",
                "answer": "Compose suffit pour un seul serveur. Kubernetes apporterait haute disponibilité et autoscaling. Identifié comme évolution."
            },
            {
                "type": "qa",
                "question": "Question 7 : Comment tu as utilisé l'IA ?",
                "answer": "Accélération plus revue critique. Chaque bloc généré : lu, compris, testé, adapté."
            },
            {
                "type": "qa",
                "question": "Question 8 : Ton app plante en prod, que fais-tu ?",
                "answer": "Observer les logs, isoler le composant, hypothèse, tester un changement, corriger plus documentation."
            },
            {
                "type": "qa",
                "question": "Question 9 : Comment sécuriser davantage ?",
                "answer": "HTTPS avec Let's Encrypt, secrets dans Vault, hardening ANSSI, fail2ban."
            },
            {
                "type": "qa",
                "question": "Question 10 : Qu'est-ce que le state Terraform ?",
                "answer": "Mémoire de Terraform. Il compare état réel versus état voulu. Ne pas committer. En équipe : S3 plus DynamoDB."
            },
            {
                "type": "conclusion",
                "title": "Message final",
                "text": "Rappelle-toi : le jury évalue ta compréhension, pas ta mémoire. Tu as les projets, tu as la logique, tu as la méthode. Explique avec tes mots pourquoi tu as fait chaque choix. Bonne chance pour ton titre pro ASD !"
            }
        ]
    }
]

# Routes
@api_router.get("/")
async def root():
    return {"message": "API ASD Audio Learning"}

@api_router.get("/course", response_model=List[CourseSection])
async def get_course():
    """Get all course sections"""
    return COURSE_CONTENT

@api_router.get("/course/{section_id}")
async def get_section(section_id: str):
    """Get a specific section by ID"""
    for section in COURSE_CONTENT:
        if section["id"] == section_id:
            return section
    return {"error": "Section not found"}

@api_router.post("/progress")
async def save_progress(progress: UserProgress):
    """Save user progress"""
    doc = progress.model_dump()
    doc['updated_at'] = doc['updated_at'].isoformat()
    
    await db.progress.update_one(
        {"section_id": progress.section_id},
        {"$set": doc},
        upsert=True
    )
    return {"status": "saved"}

@api_router.get("/progress")
async def get_progress():
    """Get all user progress"""
    progress = await db.progress.find({}, {"_id": 0}).to_list(100)
    return progress

@api_router.post("/status", response_model=StatusCheck)
async def create_status_check(input: StatusCheckCreate):
    status_dict = input.model_dump()
    status_obj = StatusCheck(**status_dict)
    
    doc = status_obj.model_dump()
    doc['timestamp'] = doc['timestamp'].isoformat()
    
    _ = await db.status_checks.insert_one(doc)
    return status_obj

@api_router.get("/status", response_model=List[StatusCheck])
async def get_status_checks():
    status_checks = await db.status_checks.find({}, {"_id": 0}).to_list(1000)
    
    for check in status_checks:
        if isinstance(check['timestamp'], str):
            check['timestamp'] = datetime.fromisoformat(check['timestamp'])
    
    return status_checks

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
