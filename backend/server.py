from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List
from datetime import datetime, timezone
import uuid

# ====================== CONFIGURATION ======================
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ.get('DB_NAME', 'revision_asd')]

# ====================== FASTAPI APP ======================
app = FastAPI(
    title="Revision Audio ASD",
    version="1.0",
    default_response_class=JSONResponse   # Force le Content-Type application/json
)

api_router = APIRouter(prefix="/api")

# ====================== MODELS ======================
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


# ====================== COURSE CONTENT (complet) ======================
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
                "text": "Voici la méthode que tu dois maîtriser. Première étape : définir un objectif clair..."
            },
            {
                "type": "method",
                "text": "Deuxième étape : formuler le besoin correctement..."
            },
            {
                "type": "method",
                "text": "Troisième étape : récupérer le code généré et le copier dans un fichier de test..."
            },
            {
                "type": "method",
                "text": "Quatrième étape : lire, comprendre et adapter..."
            },
            {
                "type": "method",
                "text": "Cinquième étape : tester et corriger..."
            },
            {
                "type": "jury",
                "title": "Attention : question piège du jury",
                "text": "Le jury pourrait te demander : Vous avez utilisé l'IA, donc vous ne comprenez pas votre code ? Ta réponse : Non, j'ai utilisé l'IA comme outil d'accélération..."
            }
        ]
    },
    # Bloc 1
    {
        "id": "bloc1",
        "title": "Bloc 1 : Automatisation & IaC",
        "icon": "Server",
        "content": [ ... ]  # ← Remplace par tout ton contenu du bloc1 (Terraform, Ansible, SSH...)
    },
    # Bloc 2
    {
        "id": "bloc2",
        "title": "Bloc 2 : Docker & CI/CD",
        "icon": "Container",
        "content": [ ... ]  # ← Remplace par tout ton contenu du bloc2
    },
    # Bloc 3
    {
        "id": "bloc3",
        "title": "Bloc 3 : Monitoring & Supervision",
        "icon": "Activity",
        "content": [ ... ]  # ← Remplace par tout ton contenu du bloc3
    },
    # Questions Jury
    {
        "id": "questions",
        "title": "Questions Jury : Réponses Flash",
        "icon": "HelpCircle",
        "content": [ ... ]  # ← Remplace par tout ton dernier bloc avec les 10 questions
    }
]

# ====================== ROUTES ======================
@api_router.get("/")
async def api_root():
    return JSONResponse(content={"message": "API ASD Audio Learning - OK"})

@api_router.get("/course")
async def get_course():
    return JSONResponse(content=COURSE_CONTENT)

@api_router.get("/course/{section_id}")
async def get_section(section_id: str):
    for section in COURSE_CONTENT:
        if section["id"] == section_id:
            return JSONResponse(content=section)
    return JSONResponse(status_code=404, content={"error": "Section not found"})

@api_router.post("/progress")
async def save_progress(progress: UserProgress):
    doc = progress.model_dump()
    doc['updated_at'] = doc['updated_at'].isoformat()
    
    await db.progress.update_one(
        {"section_id": progress.section_id},
        {"$set": doc},
        upsert=True
    )
    return JSONResponse(content={"status": "saved"})

@api_router.get("/progress")
async def get_progress():
    progress = await db.progress.find({}, {"_id": 0}).to_list(100)
    return JSONResponse(content=progress)

# Routes status (optionnelles)
@api_router.post("/status")
async def create_status_check(input: StatusCheckCreate):
    status_obj = StatusCheck(client_name=input.client_name)
    doc = status_obj.model_dump()
    doc['timestamp'] = doc['timestamp'].isoformat()
    await db.status_checks.insert_one(doc)
    return JSONResponse(content=status_obj.model_dump())

@api_router.get("/status")
async def get_status_checks():
    checks = await db.status_checks.find({}, {"_id": 0}).to_list(1000)
    return JSONResponse(content=checks)


# ====================== INCLURE ROUTER + CORS ======================
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # Change en production par l'URL de ton frontend Vercel
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Route racine principale (importante sur Render)
@app.get("/")
async def root():
    return JSONResponse(content={
        "message": "Revision Audio ASD API is running ✅",
        "status": "ok",
        "course_url": "/api/course"
    })


# ====================== LOGGING & SHUTDOWN ======================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
