
from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
from datetime import datetime, timezone
import uuid

# ====================== CONFIGURATION ======================
ROOT_DIR = Path(__file__).parent
STATIC_DIR = ROOT_DIR / "static"
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ.get('DB_NAME', 'revision_asd')]

# ====================== FASTAPI APP ======================
app = FastAPI(
    title="Revision Audio ASD",
    version="2.0",
    default_response_class=JSONResponse
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
    audio_settings: Optional[dict] = None  # Pour les paramètres TTS (voix, vitesse, etc.)

class UserProgress(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    section_id: str
    completed: bool = False
    last_position: int = 0
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# ====================== CONTENU DE COURS OPTIMISÉ POUR L'AUDIO ======================
COURSE_CONTENT = [
    # ---- Introduction & Méthode IA ----
    {
        "id": "intro",
        "title": "Introduction & Méthode IA",
        "icon": "Brain",
        "audio_settings": {"voice": "Rachel", "speed": 0.95, "pitch": 1.0},
        "content": [
            {
                "type": "intro",
                "text": "Bienvenue dans cette application de révision audio pour le Titre Professionnel Administrateur Système DevOps. Ce document couvre les onze compétences professionnelles du REAC. Je vais t'expliquer chaque notion comme si on était en cours ensemble."
            },
            {
                "type": "concept",
                "title": "La philosophie de l'IA en DevOps",
                "text": "Retiens cette citation importante : L'IA n'est pas un copilote magique. C'est un junior qui code vite mais qui se trompe souvent. Ton rôle d'Admin Sys DevOps, c'est d'être le senior qui relit, comprend, teste et valide."
            },
            {
                "type": "method",
                "title": "La méthode IA en 5 étapes",
                "text": "Première étape : définir un objectif clair. Avant même de toucher au clavier, tu dois savoir quelle techno tu utilises, quelles sont tes contraintes, et quel résultat tu attends. C'est comme un plombier qui mesure avant de couper le tuyau."
            },
            {
                "type": "method",
                "text": "Deuxième étape : formuler le besoin correctement. Quand tu parles à l'IA, donne-lui le contexte, montre-lui ton code existant, donne un exemple d'entrée et de sortie attendue."
            },
            {
                "type": "method",
                "text": "Troisième étape : récupérer le code généré et le copier dans un fichier de test. Jamais directement en production !"
            },
            {
                "type": "method",
                "text": "Quatrième étape : lire, comprendre et adapter. Tu dois être capable d'expliquer chaque bloc avec tes propres mots."
            },
            {
                "type": "method",
                "text": "Cinquième étape : tester et corriger. Commence par les cas simples, puis les cas limites."
            },
            {
                "type": "jury",
                "title": "Question piège du jury",
                "text": "Le jury pourrait te demander : Vous avez utilisé l'IA, donc vous ne comprenez pas votre code ? Ta réponse : Non, j'ai utilisé l'IA comme outil d'accélération. Pour chaque bloc généré, j'ai appliqué ma méthode : lire, comprendre, adapter, tester. Je peux expliquer chaque ligne."
            }
        ]
    },

    # ---- CP1 : Scripts Serveurs ----
    {
        "id": "cp1",
        "title": "CP1 : Scripts Serveurs",
        "icon": "Terminal",
        "audio_settings": {"voice": "Rachel", "speed": 0.9, "pitch": 1.0},
        "content": [
            {
                "type": "intro",
                "text": "Compétence 1 : Automatiser la création de serveurs à l'aide de scripts. Cette compétence couvre la virtualisation et les différents types de scripts."
            },
            {
                "type": "concept",
                "title": "Les types de virtualisation",
                "text": "Il existe trois types de virtualisation à connaître."
            },
            {
                "type": "audio_code_explain",
                "text": "Premier type : l'Hyperviseur de Type 1, comme VMware ESXi, KVM ou Hyper-V."
            },
            {
                "type": "audio_code",
                "text": "Bare Metal"
            },
            {
                "type": "audio_code_explain",
                "text": "Il s'installe directement sur le matériel. C'est utilisé en production."
            },
            {
                "type": "audio_code_explain",
                "text": "Deuxième type : l'Hyperviseur de Type 2, comme VirtualBox ou VMware Workstation."
            },
            {
                "type": "audio_code",
                "text": "Sur OS existant"
            },
            {
                "type": "audio_code_explain",
                "text": "Il s'installe sur un système d'exploitation existant. C'est utilisé pour le développement et les tests en local."
            },
            {
                "type": "audio_code_explain",
                "text": "Troisième type : les Conteneurs, comme Docker."
            },
            {
                "type": "audio_code",
                "text": "Isolation légère"
            },
            {
                "type": "audio_code_explain",
                "text": "C'est une isolation légère qui partage le même noyau que le système hôte. Plus léger qu'une machine virtuelle complète."
            },
            {
                "type": "concept",
                "title": "Script Bash : structure de base",
                "text": "Un script Bash est une liste d'instructions shell exécutées dans l'ordre."
            },
            {
                "type": "audio_command",
                "text": "#!/bin/bash"
            },
            {
                "type": "audio_code_explain",
                "text": "La première ligne commence par le shebang, qui indique que c'est un script Bash."
            },
            {
                "type": "audio_terminal_tip",
                "text": "Astuce : Ajoutez toujours set -e en début de script pour arrêter automatiquement le script si une commande échoue."
            },
            {
                "type": "audio_code_explain",
                "text": "Un script typique d'installation serveur va d'abord mettre à jour la liste des paquets."
            },
            {
                "type": "audio_command",
                "text": "sudo apt update && sudo apt upgrade -y"
            },
            {
                "type": "audio_code_explain",
                "text": "Ensuite, il installe les services nécessaires comme Nginx, le pare-feu UFW et fail2ban."
            },
            {
                "type": "audio_command",
                "text": "sudo apt install -y nginx ufw fail2ban"
            },
            {
                "type": "audio_code_explain",
                "text": "Enfin, il active et démarre ces services."
            },
            {
                "type": "audio_command",
                "text": "sudo systemctl enable --now nginx ufw fail2ban"
            },
            {
                "type": "concept",
                "title": "Script Python pour l'automatisation",
                "text": "Python peut aussi automatiser l'administration système. On utilise le module subprocess pour exécuter des commandes système."
            },
            {
                "type": "audio_code",
                "text": "import subprocess\nsubprocess.run([\"sudo\", \"apt\", \"update\"], check=True)"
            },
            {
                "type": "audio_code_explain",
                "text": "L'avantage de Python : une meilleure gestion des erreurs, des conditions, et un code plus lisible pour des automatisations complexes."
            }
        ]
    },

    # ---- CP2 : Terraform & Ansible ----
    {
        "id": "cp2",
        "title": "CP2 : Terraform & Ansible",
        "icon": "Server",
        "audio_settings": {"voice": "Rachel", "speed": 0.9, "pitch": 1.0},
        "content": [
            {
                "type": "intro",
                "text": "Compétence 2 : Automatiser le déploiement d'une infrastructure avec Terraform et Ansible. C'est fondamental pour ton titre pro."
            },
            {
                "type": "audio_analogy",
                "text": "Terraform, c'est l'architecte qui construit les murs et pose les fondations. Ansible, c'est le décorateur qui arrive après et installe les meubles, configure les prises."
            },
            {
                "type": "audio_code_explain",
                "text": "Terraform crée ton infrastructure : les instances EC2, les VPC, les Security Groups, les buckets S3."
            },
            {
                "type": "audio_code_explain",
                "text": "Ansible, lui, installe Nginx, crée les utilisateurs, copie les fichiers de configuration."
            },
            {
                "type": "audio_code_explain",
                "text": "L'ordre est important : on fait toujours Terraform d'abord pour créer l'infrastructure, puis Ansible ensuite pour la configurer."
            },
            {
                "type": "concept",
                "title": "Caractéristiques de Terraform",
                "text": "Terraform utilise le langage HCL, avec des fichiers point TF."
            },
            {
                "type": "audio_file",
                "text": "resource \"aws_instance\" \"web\" {\n  ami           = \"ami-0c55b159cbfafe1f0\"\n  instance_type = \"t2.micro\"\n}"
            },
            {
                "type": "audio_code_explain",
                "text": "Il est stateful, ce qui signifie qu'il garde un fichier d'état qui mémorise l'état de ton infrastructure."
            },
            {
                "type": "audio_terminal_tip",
                "text": "Règle d'or : ne jamais committer le fichier d'état de Terraform dans Git ! En équipe, stocke-le sur S3 avec un verrou DynamoDB."
            },
            {
                "type": "method",
                "title": "Commandes Terraform essentielles",
                "text": "Les commandes clés à retenir :"
            },
            {
                "type": "audio_command",
                "text": "terraform init"
            },
            {
                "type": "audio_code_explain",
                "text": "Pour initialiser et télécharger les providers."
            },
            {
                "type": "audio_command",
                "text": "terraform validate"
            },
            {
                "type": "audio_code_explain",
                "text": "Pour vérifier la syntaxe."
            },
            {
                "type": "audio_command",
                "text": "terraform plan"
            },
            {
                "type": "audio_code_explain",
                "text": "Pour prévisualiser les changements, c'est un dry-run."
            },
            {
                "type": "audio_command",
                "text": "terraform apply"
            },
            {
                "type": "audio_code_explain",
                "text": "Pour appliquer et créer l'infrastructure."
            },
            {
                "type": "concept",
                "title": "Caractéristiques d'Ansible",
                "text": "Ansible utilise YAML avec des fichiers playbook. Il est idempotent : si tu rejoues le même playbook dix fois, tu obtiens le même résultat."
            },
            {
                "type": "audio_file",
                "text": "---\n- hosts: webservers\n  tasks:\n    - name: Install Nginx\n      apt:\n        name: nginx\n        state: present"
            },
            {
                "type": "audio_code_explain",
                "text": "Ce playbook installe Nginx sur tous les serveurs du groupe webservers."
            },
            {
                "type": "method",
                "title": "Commandes Ansible essentielles",
                "text": "Les commandes essentielles :"
            },
            {
                "type": "audio_command",
                "text": "ansible all -m ping"
            },
            {
                "type": "audio_code_explain",
                "text": "Pour tester la connectivité vers tous les serveurs."
            },
            {
                "type": "audio_command",
                "text": "ansible-playbook playbook.yml --check"
            },
            {
                "type": "audio_code_explain",
                "text": "Pour faire un dry-run, une simulation sans appliquer les changements."
            }
        ]
    },

    # ---- CP3 : Sécurisation Infrastructure ----
    {
        "id": "cp3",
        "title": "CP3 : Sécurisation Infrastructure",
        "icon": "Shield",
        "audio_settings": {"voice": "Rachel", "speed": 0.9, "pitch": 1.0},
        "content": [
            {
                "type": "intro",
                "text": "Compétence 3 : Sécuriser l'infrastructure. Un sujet que le jury adore. Quatre actions essentielles à connaître pour SSH."
            },
            {
                "type": "security",
                "title": "Action 1 : Désactiver le login root",
                "text": "Première action de sécurité SSH : désactiver le login root."
            },
            {
                "type": "audio_file",
                "text": "PermitRootLogin no"
            },
            {
                "type": "audio_code_explain",
                "text": "Dans le fichier de configuration SSH, tu mets PermitRootLogin à no. Pourquoi ? C'est le principe du moindre privilège. Si le compte root est compromis, tout est perdu."
            },
            {
                "type": "security",
                "title": "Action 2 : Clés SSH uniquement",
                "text": "Deuxième action : utiliser uniquement des clés ED25519, pas de mots de passe."
            },
            {
                "type": "audio_command",
                "text": "PasswordAuthentication no"
            },
            {
                "type": "audio_code_explain",
                "text": "Un mot de passe peut être bruteforcé en quelques heures, une clé ED25519 c'est quasi impossible. Tu génères la paire de clés avec ssh-keygen et tu copies la clé publique sur le serveur."
            },
            {
                "type": "audio_command",
                "text": "ssh-keygen -t ed25519"
            },
            {
                "type": "audio_command",
                "text": "ssh-copy-id user@server"
            },
            {
                "type": "security",
                "title": "Action 3 : Restreindre l'accès réseau",
                "text": "Troisième action : configurer le Security Group AWS avec un CIDR en slash 32."
            },
            {
                "type": "audio_code",
                "text": "192.168.1.100/32"
            },
            {
                "type": "audio_code_explain",
                "text": "Tu mets uniquement ton IP avec un masque slash 32. Comme ça, seul toi peux atteindre le port 22. Surface d'attaque nulle."
            },
            {
                "type": "security",
                "title": "Action 4 : Installer fail2ban",
                "text": "Quatrième action : installer fail2ban et configurer une jail SSH."
            },
            {
                "type": "audio_command",
                "text": "sudo apt install -y fail2ban"
            },
            {
                "type": "audio_code_explain",
                "text": "Ça bannit automatiquement les IP après N tentatives de connexion échouées. C'est une protection supplémentaire contre le brute force."
            },
            {
                "type": "concept",
                "title": "Configuration du pare-feu UFW",
                "text": "UFW, le pare-feu simplifié d'Ubuntu. La stratégie : bloquer tout par défaut en entrée, autoriser tout en sortie."
            },
            {
                "type": "audio_command",
                "text": "sudo ufw default deny incoming && sudo ufw default allow outgoing"
            },
            {
                "type": "audio_code_explain",
                "text": "Puis ouvrir uniquement les ports nécessaires : 22 pour SSH, 80 pour HTTP, 443 pour HTTPS."
            },
            {
                "type": "audio_command",
                "text": "sudo ufw allow 22 && sudo ufw allow 80 && sudo ufw allow 443"
            },
            {
                "type": "audio_command",
                "text": "sudo ufw enable"
            },
            {
                "type": "audio_code_explain",
                "text": "Enfin, activer le pare-feu."
            },
            {
                "type": "jury",
                "title": "Question jury : HTTPS",
                "text": "Question probable du jury : vous n'avez pas configuré HTTPS ? Ta réponse : En production j'utiliserais Let's Encrypt avec Certbot ou AWS Certificate Manager. Le reverse proxy Nginx redirigerait automatiquement le HTTP vers HTTPS."
            }
        ]
    },

    # ---- CP4 : Production Cloud ----
    {
        "id": "cp4",
        "title": "CP4 : Production Cloud",
        "icon": "Cloud",
        "audio_settings": {"voice": "Rachel", "speed": 0.9, "pitch": 1.0},
        "content": [
            {
                "type": "intro",
                "text": "Compétence 4 : Mettre l'infrastructure en production dans le cloud. Comprendre les modèles de service et les composants AWS."
            },
            {
                "type": "concept",
                "title": "Les trois modèles de service cloud",
                "text": "IaaS, Infrastructure as a Service : tu gères l'OS, le runtime et l'application. Le provider gère le matériel et le réseau."
            },
            {
                "type": "audio_code",
                "text": "Exemple : EC2 sur AWS"
            },
            {
                "type": "concept",
                "text": "PaaS, Platform as a Service : tu gères uniquement l'application et les données."
            },
            {
                "type": "audio_code",
                "text": "Exemple : Heroku ou AWS Elastic Beanstalk"
            },
            {
                "type": "concept",
                "text": "SaaS, Software as a Service : tu gères uniquement la configuration utilisateur."
            },
            {
                "type": "audio_code",
                "text": "Exemples : Gmail, Office 365, Salesforce"
            },
            {
                "type": "concept",
                "title": "Composants AWS de ton projet",
                "text": "VPC avec un réseau en 10.0.0.0/16 : c'est ton réseau virtuel isolé."
            },
            {
                "type": "audio_code",
                "text": "10.0.0.0/16"
            },
            {
                "type": "concept",
                "text": "Subnet public en 10.0.1.0/24 : c'est le sous-réseau accessible depuis Internet."
            },
            {
                "type": "audio_code",
                "text": "10.0.1.0/24"
            },
            {
                "type": "audio_code_explain",
                "text": "Security Group : c'est le pare-feu avec SSH restreint et HTTP/HTTPS ouvert."
            },
            {
                "type": "audio_code",
                "text": "Instance EC2 de type t2.micro : c'est ton serveur web, éligible au Free Tier AWS."
            },
            {
                "type": "audio_code",
                "text": "Bucket S3 : c'est le stockage pour les fichiers statiques."
            },
            {
                "type": "audio_code",
                "text": "Internet Gateway : c'est la connexion du VPC vers Internet."
            },
            {
                "type": "jury",
                "title": "Question jury : pourquoi t2.micro",
                "text": "Le jury pourrait demander : Pourquoi t2.micro ? Ta réponse : C'est l'instance éligible au Free Tier AWS, suffisante pour un serveur web statique en contexte de formation. En production je dimensionnerais selon la charge prévue."
            }
        ]
    },

    # ---- CP5 : CI/CD & Tests ----
    {
        "id": "cp5",
        "title": "CP5 : CI/CD & Tests",
        "icon": "GitBranch",
        "audio_settings": {"voice": "Rachel", "speed": 0.9, "pitch": 1.0},
        "content": [
            {
                "type": "intro",
                "text": "Compétence 5 : Préparer un environnement de test. La démarche CI/CD et la méthodologie Agile."
            },
            {
                "type": "concept",
                "title": "CI/CD expliqué simplement",
                "text": "CI, Intégration Continue : chaque commit déclenche automatiquement le build et les tests."
            },
            {
                "type": "audio_code_explain",
                "text": "CD, Déploiement Continu : si les tests passent, le déploiement se fait automatiquement."
            },
            {
                "type": "audio_code_explain",
                "text": "Ton pipeline : push sur la branche main, vérification du style Python, tests avec pytest, build de l'image Docker, puis déploiement."
            },
            {
                "type": "technical",
                "title": "Pipeline GitHub Actions",
                "text": "La CI/CD c'est comme une chaîne de montage automobile."
            },
            {
                "type": "audio_code_explain",
                "text": "On ne livre pas la voiture si une étape de contrôle qualité échoue."
            },
            {
                "type": "audio_file",
                "text": "name: CI/CD Pipeline\non:\n  push:\n    branches: [ main ]\njobs:\n  test:\n    runs-on: ubuntu-latest\n    steps:\n      - uses: actions/checkout@v2\n      - name: Run tests\n        run: pytest"
            },
            {
                "type": "audio_code_explain",
                "text": "Le trigger se déclenche sur push vers main. Le job checkout récupère le code. Ensuite les tests avec pytest."
            },
            {
                "type": "audio_code_explain",
                "text": "Si tout passe, on build l'image Docker avec le SHA du commit comme tag pour la traçabilité."
            },
            {
                "type": "audio_command",
                "text": "docker build -t myapp:${{ github.sha }} ."
            },
            {
                "type": "audio_code_explain",
                "text": "Enfin on push vers le registry."
            },
            {
                "type": "concept",
                "title": "Vocabulaire Agile Scrum",
                "text": "Sprint : itération courte de une à quatre semaines. Backlog : liste des fonctionnalités à développer, priorisée. User Story : besoin exprimé du point de vue de l'utilisateur."
            },
            {
                "type": "audio_code",
                "text": "Definition of Done : critères pour qu'une tâche soit considérée comme terminée."
            },
            {
                "type": "method",
                "title": "Les environnements du pipeline",
                "text": "La chaîne des environnements : DEV en local sur WSL2, puis TEST avec pytest, puis Staging pour la validation, puis Production."
            },
            {
                "type": "audio_code_explain",
                "text": "Règle importante : chaque environnement doit être identique au suivant. Docker garantit ça : même image égale même comportement partout."
            }
        ]
    },

    # ---- CP6 : Stockage des Données ----
    {
        "id": "cp6",
        "title": "CP6 : Stockage des Données",
        "icon": "Database",
        "audio_settings": {"voice": "Rachel", "speed": 0.9, "pitch": 1.0},
        "content": [
            {
                "type": "intro",
                "text": "Compétence 6 : Gérer le stockage des données. SQLite, les types de stockage et les bonnes pratiques de sauvegarde."
            },
            {
                "type": "concept",
                "title": "SQLite dans ton projet",
                "text": "SQLite est une base de données fichier, sans serveur séparé. Choix justifié pour un projet solo ou à faible charge."
            },
            {
                "type": "jury",
                "title": "Question jury : Pourquoi SQLite ?",
                "text": "Question probable du jury : Pourquoi SQLite et pas PostgreSQL ? Ta réponse : Pas de serveur séparé à gérer, adapté à un seul utilisateur. J'ai identifié la migration vers PostgreSQL comme évolution si le projet prend de l'ampleur."
            },
            {
                "type": "concept",
                "title": "Les trois types de stockage",
                "text": "Stockage bloc, comme AWS EBS ou SAN : utilisé pour le système d'exploitation et les bases de données."
            },
            {
                "type": "audio_code_explain",
                "text": "C'est comme un disque dur classique."
            },
            {
                "type": "audio_code",
                "text": "Stockage fichier : NFS ou AWS EFS"
            },
            {
                "type": "audio_code_explain",
                "text": "Utilisé pour le partage entre serveurs."
            },
            {
                "type": "audio_code",
                "text": "Stockage objet : AWS S3"
            },
            {
                "type": "audio_code_explain",
                "text": "Utilisé pour les fichiers statiques, les backups et les logs."
            },
            {
                "type": "method",
                "title": "Sauvegarde des données",
                "text": "Pour SQLite, la sauvegarde la plus simple est une copie du fichier de base de données avec un horodatage."
            },
            {
                "type": "audio_command",
                "text": "cp database.sqlite database_$(date +%Y%m%d).sqlite"
            },
            {
                "type": "audio_code_explain",
                "text": "En production, on pousse cette sauvegarde vers S3 pour la redondance."
            },
            {
                "type": "audio_terminal_tip",
                "text": "Règle d'or : tester régulièrement la restauration des sauvegardes."
            }
        ]
    },

    # ---- CP7 : Docker & Containers ----
    {
        "id": "cp7",
        "title": "CP7 : Docker & Containers",
        "icon": "Container",
        "audio_settings": {"voice": "Rachel", "speed": 0.9, "pitch": 1.0},
        "content": [
            {
                "type": "intro",
                "text": "Compétence 7 : Gérer des containers. Docker est au cœur du DevOps moderne. Tu dois pouvoir expliquer ton Dockerfile ligne par ligne."
            },
            {
                "type": "audio_analogy",
                "text": "Un Dockerfile, c'est comme une recette de cuisine. Chaque instruction est une étape pour préparer ton plat final : l'image Docker."
            },
            {
                "type": "audio_code_explain",
                "text": "La première ligne commence toujours par FROM. C'est ici qu'on choisit l'image de base."
            },
            {
                "type": "audio_code",
                "text": "FROM python:3.9-slim"
            },
            {
                "type": "audio_code_explain",
                "text": "Ici, on utilise l’image officielle Python en version 3.9 avec le tag slim. Le suffixe slim signifie qu’elle est allégée : pas d’outils inutiles, donc moins de failles de sécurité et un téléchargement plus rapide."
            },
            {
                "type": "audio_code",
                "text": "RUN useradd -m app"
            },
            {
                "type": "audio_code_explain",
                "text": "RUN exécute une commande pendant la construction. Ici, on crée un utilisateur app avec un répertoire home. C’est une bonne pratique pour éviter de tourner en root."
            },
            {
                "type": "audio_terminal_tip",
                "text": "Astuce sécurité : Toujours créer un utilisateur non-root dans vos conteneurs !"
            },
            {
                "type": "audio_code",
                "text": "COPY requirements.txt /app/"
            },
            {
                "type": "audio_code_explain",
                "text": "COPY copie un fichier de votre machine vers le conteneur. Ici, on copie requirements.txt dans le dossier /app/."
            },
            {
                "type": "audio_code",
                "text": "RUN pip install -r /app/requirements.txt"
            },
            {
                "type": "audio_code_explain",
                "text": "On installe ensuite les dépendances Python listées dans requirements.txt. L’ordre est important : on copie d’abord le fichier requirements.txt, puis on installe les dépendances. Comme ça, Docker peut réutiliser son cache si seulement le code change."
            },
            {
                "type": "audio_command",
                "text": "docker build -t myapp:latest ."
            },
            {
                "type": "audio_code_explain",
                "text": "Pour construire l’image, on utilise docker build. L’option -t permet de taguer l’image avec un nom et une version. Le point final indique le contexte de build."
            },
            {
                "type": "audio_command",
                "text": "docker run -d --name mycontainer myapp:latest"
            },
            {
                "type": "audio_code_explain",
                "text": "Pour lancer le conteneur, on utilise docker run. L’option -d le lance en arrière-plan, et --name lui donne un nom explicite."
            },
            {
                "type": "method",
                "title": "Commandes Docker essentielles",
                "text": "Voici les commandes à connaître :"
            },
            {
                "type": "audio_command",
                "text": "docker build -t monimage ."
            },
            {
                "type": "audio_command",
                "text": "docker run -d monimage"
            },
            {
                "type": "audio_command",
                "text": "docker ps"
            },
            {
                "type": "audio_command",
                "text": "docker logs -f moncontainer"
            },
            {
                "type": "audio_command",
                "text": "docker exec -it moncontainer bash"
            },
            {
                "type": "concept",
                "title": "Docker Compose",
                "text": "Docker Compose orchestre plusieurs conteneurs. Tu définis tes services, les ports, les volumes pour la persistance, les variables d'environnement."
            },
            {
                "type": "audio_file",
                "text": "version: '3'\nservices:\n  web:\n    image: nginx\n    ports:\n      - \"80:80\"\n    volumes:\n      - ./html:/usr/share/nginx/html"
            },
            {
                "type": "audio_code_explain",
                "text": "Un seul fichier YAML pour tout décrire."
            },
            {
                "type": "audio_command",
                "text": "docker-compose up -d"
            },
            {
                "type": "audio_code_explain",
                "text": "Pour tout lancer."
            },
            {
                "type": "audio_command",
                "text": "docker-compose down"
            },
            {
                "type": "audio_code_explain",
                "text": "Pour tout arrêter."
            }
        ]
    },

    # ---- CP8 : Kubernetes ----
    {
        "id": "cp8",
        "title": "CP8 : Kubernetes",
        "icon": "Layers",
        "audio_settings": {"voice": "Rachel", "speed": 0.9, "pitch": 1.0},
        "content": [
            {
                "type": "intro",
                "text": "Compétence 8 : Automatiser la mise en production avec Kubernetes. Même si Kubernetes n'est pas dans ton projet, tu dois pouvoir l'expliquer conceptuellement."
            },
            {
                "type": "concept",
                "title": "Architecture Kubernetes",
                "text": "Kubernetes a deux parties. Le Control Plane, c'est le cerveau du cluster."
            },
            {
                "type": "audio_code",
                "text": "API Server, etcd, Scheduler"
            },
            {
                "type": "audio_code_explain",
                "text": "Il gère l'état désiré. L'API Server est le point d’entrée de toutes les commandes. etcd stocke l'état du cluster. Le Scheduler décide sur quel nœud placer les Pods."
            },
            {
                "type": "audio_code_explain",
                "text": "Les Worker Nodes sont les machines qui font tourner les Pods."
            },
            {
                "type": "audio_code",
                "text": "kubelet"
            },
            {
                "type": "audio_code_explain",
                "text": "Le kubelet est l'agent sur chaque node, il applique les instructions."
            },
            {
                "type": "audio_code",
                "text": "Pod"
            },
            {
                "type": "audio_code_explain",
                "text": "Un Pod est la plus petite unité Kubernetes, il contient un ou plusieurs conteneurs."
            },
            {
                "type": "technical",
                "title": "Deployment et Service",
                "text": "Un Deployment gère les Pods : réplication, rolling update, rollback."
            },
            {
                "type": "audio_code",
                "text": "Service"
            },
            {
                "type": "audio_code_explain",
                "text": "Un Service expose les Pods sur le réseau avec une IP stable. C'est comme un load balancer interne."
            },
            {
                "type": "jury",
                "title": "Question jury : pourquoi pas Kubernetes",
                "text": "Le jury pourrait demander : Pourquoi Kubernetes n'est pas dans votre projet ? Ta réponse : Docker Compose couvre mes besoins actuels sur un seul serveur. Kubernetes apporterait haute disponibilité avec les replicas, rolling updates sans downtime, autoscaling selon la charge, et gestion multi-nœuds. Je l'ai identifié comme évolution naturelle pour la production."
            },
            {
                "type": "method",
                "title": "Commandes kubectl essentielles",
                "text": "Les commandes à connaître :"
            },
            {
                "type": "audio_command",
                "text": "kubectl apply -f deployment.yaml"
            },
            {
                "type": "audio_code_explain",
                "text": "Pour déployer un fichier YAML."
            },
            {
                "type": "audio_command",
                "text": "kubectl get pods"
            },
            {
                "type": "audio_command",
                "text": "kubectl logs -f monpod"
            },
            {
                "type": "audio_command",
                "text": "kubectl exec -it monpod -- bash"
            },
            {
                "type": "audio_command",
                "text": "kubectl rollout undo deployment/mondeployment"
            },
            {
                "type": "audio_code_explain",
                "text": "Pour faire un rollback."
            },
            {
                "type": "audio_command",
                "text": "kubectl scale deployment/mondeployment --replicas=3"
            }
        ]
    },

    # ---- CP9 : Métriques & SLO ----
    {
        "id": "cp9",
        "title": "CP9 : Métriques & SLO",
        "icon": "BarChart",
        "audio_settings": {"voice": "Rachel", "speed": 0.9, "pitch": 1.0},
        "content": [
            {
                "type": "intro",
                "text": "Compétence 9 : Définir et mettre en place des statistiques de services. SLI, SLO, SLA et tes métriques Prometheus."
            },
            {
                "type": "concept",
                "title": "SLI, SLO, SLA expliqués",
                "text": "SLI, Service Level Indicator : c'est la mesure réelle."
            },
            {
                "type": "audio_code",
                "text": "Exemple : taux de succès API = 98%"
            },
            {
                "type": "audio_code",
                "text": "SLO, Service Level Objective : c'est l'objectif interne."
            },
            {
                "type": "audio_code_explain",
                "text": "Exemple : on vise 99,5% de succès."
            },
            {
                "type": "audio_code",
                "text": "SLA, Service Level Agreement : c'est le contrat client."
            },
            {
                "type": "audio_code_explain",
                "text": "Exemple : remboursement si disponibilité inférieure à 99%."
            },
            {
                "type": "technical",
                "title": "Error Budget",
                "text": "L'Error Budget c'est la marge d'erreur autorisée."
            },
            {
                "type": "audio_code",
                "text": "SLO = 99,5% → 0,5% d'erreur tolérée"
            },
            {
                "type": "audio_code_explain",
                "text": "Ça représente environ 3 heures 30 de downtime par mois. Tant que tu restes dans ce budget, tu peux prendre des risques et innover."
            },
            {
                "type": "concept",
                "title": "Tes métriques Prometheus",
                "text": "Dans ton projet, tu exposes des métriques via prometheus_client sur le port 8000."
            },
            {
                "type": "audio_code",
                "text": "app_requests_total"
            },
            {
                "type": "audio_code_explain",
                "text": "Compte le nombre total de requêtes."
            },
            {
                "type": "audio_code",
                "text": "api_calls_total{status=\"success\"}"
            },
            {
                "type": "audio_code_explain",
                "text": "Compte les appels API réussis."
            },
            {
                "type": "audio_code",
                "text": "api_response_seconds"
            },
            {
                "type": "audio_code_explain",
                "text": "Mesure le temps de réponse."
            },
            {
                "type": "method",
                "title": "Indicateurs système à surveiller",
                "text": "Les seuils à surveiller :"
            },
            {
                "type": "audio_code",
                "text": "CPU > 80% pendant 5min → alerte"
            },
            {
                "type": "audio_code",
                "text": "RAM > 85% utilisée → alerte"
            },
            {
                "type": "audio_code",
                "text": "Disque > 85% utilisé → alerte"
            },
            {
                "type": "audio_code",
                "text": "Load average > nombre de CPUs → alerte"
            }
        ]
    },

    # ---- CP10 : Monitoring Prometheus ----
    {
        "id": "cp10",
        "title": "CP10 : Monitoring Prometheus",
        "icon": "Activity",
        "audio_settings": {"voice": "Rachel", "speed": 0.9, "pitch": 1.0},
        "content": [
            {
                "type": "intro",
                "text": "Compétence 10 : Exploiter une solution de supervision. Prometheus et Grafana. Question quasi-certaine au jury !"
            },
            {
                "type": "concept",
                "title": "Les trois ports à connaître",
                "text": "Le jury adore cette question sur les ports."
            },
            {
                "type": "audio_code",
                "text": "Port 8000"
            },
            {
                "type": "audio_code_explain",
                "text": "C'est ton application Python qui expose l'endpoint /metrics via prometheus_client. Prometheus vient scraper ce port."
            },
            {
                "type": "audio_code",
                "text": "Port 9090"
            },
            {
                "type": "audio_code_explain",
                "text": "C'est l'interface web de Prometheus qui centralise et stocke les métriques."
            },
            {
                "type": "audio_code",
                "text": "Port 3000"
            },
            {
                "type": "audio_code_explain",
                "text": "C'est Grafana, le dashboard de visualisation."
            },
            {
                "type": "jury",
                "title": "Question jury : deux ports",
                "text": "Pourquoi deux ports 8000 et 9090 ? Ta réponse : Port 8000 est exposé par mon application Python via prometheus_client. C'est l'endpoint que Prometheus scrape pour collecter les métriques. Port 9090 c'est l'interface de Prometheus lui-même, qui centralise, stocke et rend interrogeables les métriques collectées depuis le 8000."
            },
            {
                "type": "concept",
                "title": "Le mode PULL de Prometheus",
                "text": "Prometheus fonctionne en mode PULL, il va chercher les métriques."
            },
            {
                "type": "audio_analogy",
                "text": "Prometheus est comme un facteur qui passe relever le courrier à heures fixes. Les applications n'ont pas besoin de savoir où envoyer, elles exposent juste leurs métriques sur /metrics."
            },
            {
                "type": "method",
                "title": "Requêtes PromQL essentielles",
                "text": "Cinq requêtes à connaître."
            },
            {
                "type": "audio_code",
                "text": "api_calls_total{status=\"success\"}"
            },
            {
                "type": "audio_code_explain",
                "text": "Compteur d'appels réussis."
            },
            {
                "type": "audio_code",
                "text": "rate(api_calls_total{status=\"error\"}[5m])"
            },
            {
                "type": "audio_code_explain",
                "text": "Taux d'erreurs par seconde sur 5 minutes."
            },
            {
                "type": "audio_code",
                "text": "avg(api_response_seconds)"
            },
            {
                "type": "audio_code_explain",
                "text": "Temps de réponse moyen."
            },
            {
                "type": "audio_code",
                "text": "db_records_total"
            },
            {
                "type": "audio_code_explain",
                "text": "Nombre d'enregistrements en base."
            },
            {
                "type": "audio_code",
                "text": "up{job=\"monapp\"}"
            },
            {
                "type": "audio_code_explain",
                "text": "Vérifie si l'application est accessible."
            },
            {
                "type": "concept",
                "title": "SNMP et Syslog",
                "text": "SNMP, Simple Network Management Protocol : supervise les équipements réseau comme les switches et routeurs."
            },
            {
                "type": "audio_code_explain",
                "text": "Syslog : protocole de centralisation des logs système."
            },
            {
                "type": "audio_code_explain",
                "text": "Prometheus fait pour les métriques applicatives ce que SNMP fait pour le réseau."
            }
        ]
    },

    # ---- CP11 : Anglais Professionnel ----
    {
        "id": "cp11",
        "title": "CP11 : Anglais Professionnel",
        "icon": "Globe",
        "audio_settings": {"voice": "Rachel", "speed": 0.95, "pitch": 1.0},
        "content": [
            {
                "type": "intro",
                "text": "Compétence 11 : Échanger sur des réseaux professionnels en anglais. Les communautés à connaître et le vocabulaire technique."
            },
            {
                "type": "concept",
                "title": "Communautés professionnelles",
                "text": "Voici les communautés à suivre :"
            },
            {
                "type": "audio_code",
                "text": "Stack Overflow"
            },
            {
                "type": "audio_code_explain",
                "text": "Pour résoudre des bugs et chercher des solutions."
            },
            {
                "type": "audio_code",
                "text": "Server Fault"
            },
            {
                "type": "audio_code_explain",
                "text": "Pour les questions système et réseau."
            },
            {
                "type": "audio_code",
                "text": "GitHub Discussions"
            },
            {
                "type": "audio_code_explain",
                "text": "Pour les projets open source."
            },
            {
                "type": "method",
                "title": "Vocabulaire anglais technique",
                "text": "Quelques termes clés à connaître :"
            },
            {
                "type": "audio_code",
                "text": "Deployment → déploiement"
            },
            {
                "type": "audio_code",
                "text": "Troubleshoot → diagnostiquer"
            },
            {
                "type": "audio_code",
                "text": "Workaround → contournement"
            },
            {
                "type": "audio_code",
                "text": "Deprecated → obsolète"
            },
            {
                "type": "technical",
                "title": "Structure d'une bonne question technique",
                "text": "Pour poser une question sur un forum anglophone, structure en 5 points : Environment, Problem, What you tried, Error message, Question."
            }
        ]
    },

    # ---- Compétences Transversales ----
    {
        "id": "transversal",
        "title": "Compétences Transversales",
        "icon": "Wrench",
        "audio_settings": {"voice": "Rachel", "speed": 0.9, "pitch": 1.0},
        "content": [
            {
                "type": "intro",
                "text": "Compétences transversales : la résolution de problèmes et l'apprentissage continu. Méthodes à maîtriser pour le jury."
            },
            {
                "type": "method",
                "title": "Résolution d'incident en 5 étapes",
                "text": "Première étape : OBSERVER. Que se passe-t-il ? Consulte les logs, les métriques, les messages d'erreur."
            },
            {
                "type": "method",
                "text": "Deuxième étape : ISOLER. Depuis quand ? Quel composant ? Est-ce reproductible ?"
            },
            {
                "type": "method",
                "text": "Troisième étape : HYPOTHÈSE. Quelle est la cause probable ?"
            },
            {
                "type": "method",
                "text": "Quatrième étape : TESTER. Vérifie l'hypothèse avec un seul changement à la fois."
            },
            {
                "type": "method",
                "text": "Cinquième étape : CORRIGER. Applique la correction et documente l'incident pour que ça ne se reproduise pas."
            },
            {
                "type": "concept",
                "title": "Outils de diagnostic",
                "text": "Les outils à connaître :"
            },
            {
                "type": "audio_command",
                "text": "journalctl -u nginx"
            },
            {
                "type": "audio_code_explain",
                "text": "Pour les logs des services système."
            },
            {
                "type": "audio_command",
                "text": "docker logs moncontainer"
            },
            {
                "type": "audio_code_explain",
                "text": "Pour les logs d'un conteneur Docker."
            },
            {
                "type": "audio_command",
                "text": "df -h"
            },
            {
                "type": "audio_code_explain",
                "text": "Pour l'espace disque."
            },
            {
                "type": "audio_command",
                "text": "free -h"
            },
            {
                "type": "audio_code_explain",
                "text": "Pour la mémoire."
            },
            {
                "type": "concept",
                "title": "Sources de veille technologique",
                "text": "Les sources à suivre : Documentation officielle AWS, HashiCorp, kubernetes.io, ANSSI, CNCF, Reddit r/devops."
            }
        ]
    },

    # ---- Questions Jury ----
    {
        "id": "questions",
        "title": "Questions Jury : Réponses Flash",
        "icon": "HelpCircle",
        "audio_settings": {"voice": "Rachel", "speed": 0.95, "pitch": 1.0},
        "content": [
            {
                "type": "intro",
                "text": "Les 10 questions types du jury avec les réponses flash. Entraîne-toi à les réciter avec tes propres mots !"
            },
            {
                "type": "qa",
                "question": "Présentez votre projet en 2 minutes",
                "answer": "Application web qui affiche les cryptos les plus performantes sur 24h. Elle interroge l'API CoinGecko, stocke en SQLite, affiche via Streamlit. Conteneurisée avec Docker, déployée via CI/CD GitHub Actions, surveillée par Prometheus."
            },
            {
                "type": "qa",
                "question": "Terraform vs Ansible ?",
                "answer": "Terraform provisionne l'infrastructure, il crée la VM, le réseau, le pare-feu sur AWS. Ansible configure ce qui tourne dessus : il installe Nginx, crée les utilisateurs. Terraform d'abord, Ansible ensuite."
            },
            {
                "type": "qa",
                "question": "Pourquoi un CIDR slash 32 sur SSH ?",
                "answer": "Moindre privilège réseau : seule mon IP peut atteindre le port 22. Si j'ouvre à 0.0.0.0/0, n'importe qui peut tenter du brute force."
            },
            {
                "type": "qa",
                "question": "Explique ton Dockerfile",
                "answer": "FROM slim pour image légère. Utilisateur non-root par sécurité. COPY requirements avant le code pour le cache Docker. EXPOSE pour documenter. CMD pour la commande de démarrage."
            },
            {
                "type": "qa",
                "question": "Pourquoi deux ports 8000 et 9090 ?",
                "answer": "8000 c'est l'endpoint métriques de mon application exposé via prometheus_client. 9090 c'est l'interface Prometheus qui scrappe ce 8000 et stocke les métriques."
            },
            {
                "type": "qa",
                "question": "Pourquoi SQLite et pas PostgreSQL ?",
                "answer": "Pas de serveur séparé à gérer, adapté à un seul utilisateur. J'ai identifié la migration vers PostgreSQL comme évolution si la charge augmente."
            },
            {
                "type": "qa",
                "question": "Kubernetes, pourquoi pas dans le projet ?",
                "answer": "Docker Compose suffit pour un seul serveur et un seul utilisateur. Kubernetes apporterait haute disponibilité, rolling updates, autoscaling. Identifié comme évolution naturelle pour la production."
            },
            {
                "type": "qa",
                "question": "Comment tu as utilisé l'IA ?",
                "answer": "Comme outil d'accélération, pas comme solution magique. Pour chaque bloc généré : lu, vérifié sur des sources fiables, compris, testé, adapté. Je peux expliquer chaque ligne."
            },
            {
                "type": "qa",
                "question": "Ton app plante en prod, que fais-tu ?",
                "answer": "D'abord observer les logs avec docker logs. Vérifier les métriques Prometheus. Identifier depuis quand et quel composant. Hypothèse, tester un changement à la fois. Corriger et documenter l'incident."
            },
            {
                "type": "qa",
                "question": "Comment sécuriser davantage ?",
                "answer": "Ajouter HTTPS avec Let's Encrypt et Certbot. Stocker les secrets dans HashiCorp Vault plutôt qu'en fichier env. Appliquer les recommandations ANSSI de hardening Linux. Renforcer fail2ban."
            },
            {
                "type": "conclusion",
                "title": "Message final",
                "text": "Rappelle-toi : le jury évalue ta compréhension, pas ta mémoire. Tu as les projets, tu as la logique, tu as la méthode. Explique avec tes propres mots pourquoi tu as fait chaque choix. Bonne chance pour ton titre pro ASD, Romain !"
            }
        ]
    }
]

# ====================== ROUTES ======================
@api_router.get("/")
async def api_root():
    return JSONResponse(content={"message": "API ASD Audio Learning v2 - OK"})

@api_router.get("/course")
async def get_course():
    return JSONResponse(content=COURSE_CONTENT)

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

app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(level=logging.INFO)

# ====================== SERVE FRONTEND ======================
STATIC_FILES_DIR = STATIC_DIR / "static"
if STATIC_DIR.exists() and (STATIC_DIR / "index.html").exists():
    if STATIC_FILES_DIR.exists():
        app.mount("/static", StaticFiles(directory=str(STATIC_FILES_DIR)), name="static")

    @app.get("/")
    async def serve_root():
        return FileResponse(STATIC_DIR / "index.html")

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        if full_path.startswith("api"):
            return JSONResponse({"error": "Not found"}, status_code=404)

        file_path = STATIC_DIR / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)

        return FileResponse(STATIC_DIR / "index.html")
else:
    @app.get("/")
    async def root():
        return JSONResponse(content={
            "message": "Revision Audio ASD API v2 is running",
            "status": "ok",
            "sections_count": len(COURSE_CONTENT),
            "note": "Frontend not found. Ensure backend/static/ contains the build."
        })

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
