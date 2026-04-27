from fastapi import FastAPI, APIRouter, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import re
import io
import tempfile
import pyttsx3
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
import uuid
import json as _json

# ====================== CONFIGURATION ======================
ROOT_DIR = Path(__file__).parent
STATIC_DIR = ROOT_DIR / "static"
load_dotenv(ROOT_DIR / '.env')

# Constantes
ITEMS_PER_PAGE = 5  # Nombre d'éléments par page

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
    audio_settings: Optional[dict] = None

class UserProgress(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    section_id: str
    completed: bool = False
    last_position: int = 0
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class PaginatedResponse(BaseModel):
    data: List[Dict[str, Any]]
    page: int
    total_pages: int
    total_items: int

# ====================== FONCTIONS TTS ======================
def _init_tts_engine() -> pyttsx3.Engine:
    engine = pyttsx3.init()
    voices = engine.getProperty('voices')
    try:
        french_voice = next(
            v for v in voices
            if 'french' in v.name.lower() or 'fr' in (v.languages or [])
        )
        engine.setProperty('voice', french_voice.id)
    except StopIteration:
        pass
    engine.setProperty('rate', 150)
    return engine

def _render_tts(engine: pyttsx3.Engine, text: str, rate: int = 150) -> bytes:
    engine.setProperty('rate', rate)
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp_path = tmp.name
    engine.save_to_file(text, tmp_path)
    engine.runAndWait()
    with open(tmp_path, "rb") as f:
        data = f.read()
    os.unlink(tmp_path)
    return data

SPELL_OUT = {
    "apt": "A-P-T", "ssh": "S-S-H", "tls": "T-L-S", "ssl": "S-S-L",
    "ci": "C-I", "cd": "C-D", "cpu": "C-P-U", "ram": "R-A-M",
    "vpc": "V-P-C", "aws": "A-W-S", "ec2": "E-C-2", "s3": "S-3",
    "nfs": "N-F-S", "efs": "E-F-S", "ebs": "E-B-S", "hcl": "H-C-L",
    "dns": "D-N-S", "snmp": "S-N-M-P", "iam": "I-A-M", "rbac": "R-B-A-C",
    "yaml": "YAML", "json": "JSON", "ip": "I-P", "os": "O-S",
    "vm": "V-M", "url": "U-R-L", "api": "A-P-I",
    "sli": "S-L-I", "slo": "S-L-O", "sla": "S-L-A",
    "tty": "T-T-Y", "kvm": "K-V-M",
    # Ajouts pour TopGainersCrypto
    "sqlite": "S-Q-Lite", "ci/cd": "C-I C-D", "tts": "T-T-S",
    "promql": "PromQL", "qcm": "Q-C-M",
}

TECH_SYMBOLS = {
    "/": " slash ", "-": " tiret ", "_": " underscore ", ":": " deux-points ",
    "=": " égal ", ".": " point ", "@": " arobase ", "#": " dièse ",
    "*": " étoile ", "&": " et ", "|": " pipe ", ">": " supérieur ",
    "<": " inférieur ", "~": " tilde ", "`": " backtick ", "$": " dollar ",
    "%": " pourcent ", "+": " plus ", "\\": " antislash ",
    "!": " point d'exclamation ", "{": " accolade ouvrante ", "}": " accolade fermante ",
    "[": " crochet ouvrant ", "]": " crochet fermant ",
    "(": " parenthèse ouvrante ", ")": " parenthèse fermante ",
    '"': " guillemet ", "'": " apostrophe ",
}

KNOWN_PATTERNS = [
    (r'(\w+):(\d+\.\d+(?:\.\d+)?)-?(\w+)?', lambda m: (
        f"{m.group(1)} version {m.group(2)}" + (f" {m.group(3)}" if m.group(3) else "")
    )),
    (r'(\d+\.\d+\.\d+\.\d+)/(\d+)', lambda m: (
        " point ".join(m.group(1).split(".")) + f" sur {m.group(2)}"
    )),
    (r'\s-([a-zA-Z]+)', lambda m: f" option {m.group(1)} "),
    (r'--(\w+)(?:=(\S+))?', lambda m: (
        f" option {m.group(1)}" + (f" égal {m.group(2)}" if m.group(2) else "")
    )),
    (r'\$\{\{\s*(\S+)\s*\}\}', lambda m: f" variable {m.group(1)} "),
]

def _apply_spell_out(token: str) -> str:
    lower = token.lower().rstrip(".,;:")
    if lower in SPELL_OUT:
        suffix = token[len(lower):]
        return SPELL_OUT[lower] + suffix
    return token

def format_command_for_tts(command: str) -> str:
    processed = command.strip()
    for pattern, replacement in KNOWN_PATTERNS:
        processed = re.sub(pattern, replacement, processed)
    tokens = processed.split()
    readable_tokens = [_apply_spell_out(t) for t in tokens]
    readable = ", ".join(readable_tokens)
    return f"Commande terminal. {readable}. Fin de commande."

def format_code_for_tts(code: str) -> str:
    lines = [l.strip() for l in code.strip().splitlines() if l.strip()]
    readable_lines = []
    for line in lines:
        processed = line
        for pattern, replacement in KNOWN_PATTERNS:
            processed = re.sub(pattern, replacement, processed)
        vocalised = ""
        for ch in processed:
            vocalised += TECH_SYMBOLS.get(ch, ch)
        vocalised = re.sub(r'\s{2,}', ' ', vocalised).strip()
        readable_lines.append(vocalised)
    body = ". Ligne suivante. ".join(readable_lines)
    return f"Extrait de code. {body}. Fin de l'extrait."

def format_yaml_for_tts(yaml_text: str) -> str:
    lines = yaml_text.strip().splitlines()
    readable_parts = ["Fichier de configuration."]
    for line in lines:
        if not line.strip() or line.strip().startswith("#"):
            continue
        indent = len(line) - len(line.lstrip())
        stripped = line.strip()
        if ":" in stripped:
            parts = stripped.split(":", 1)
            key = parts[0].strip()
            value = parts[1].strip() if len(parts) > 1 else ""
            depth = indent // 2
            prefix = ["Clé principale", "Sous-clé", "Paramètre"][min(depth, 2)]
            key_readable = _apply_spell_out(key)
            if value:
                value_readable = _apply_spell_out(value.strip('"\''))
                readable_parts.append(f"{prefix} {key_readable}, valeur {value_readable}.")
            else:
                readable_parts.append(f"{prefix} {key_readable}.")
        elif stripped.startswith("-"):
            item = stripped.lstrip("- ").strip()
            readable_parts.append(f"Élément de liste: {_apply_spell_out(item)}.")
        else:
            readable_parts.append(_apply_spell_out(stripped) + ".")
    readable_parts.append("Fin du fichier de configuration.")
    return " ".join(readable_parts)

def _is_command(text: str) -> bool:
    command_starters = [
        "docker", "kubectl", "terraform", "ansible", "ansible-playbook",
        "sudo", "apt", "pip", "npm", "git", "ssh", "cp", "mv", "rm",
        "df", "free", "ss", "ping", "journalctl", "systemctl",
        "python", "bash", "cat", "echo", "curl", "wget", "#!/", "docker-compose",
    ]
    return any(text.strip().lower().startswith(s) for s in command_starters)

def _is_yaml_block(text: str) -> bool:
    return "\n" in text and (":" in text or "- " in text)

def generate_audio_for_item(engine: pyttsx3.Engine, item: dict) -> bytes:
    item_type = item.get("type", "")
    text = item.get("text", "").strip()
    if item_type == "audio_command" or (item_type == "technical" and _is_command(text)):
        return _render_tts(engine, format_command_for_tts(text), rate=130)
    elif item_type == "audio_code":
        if _is_yaml_block(text):
            return _render_tts(engine, format_yaml_for_tts(text), rate=130)
        elif _is_command(text):
            return _render_tts(engine, format_command_for_tts(text), rate=130)
        else:
            return _render_tts(engine, format_code_for_tts(text), rate=130)
    elif item_type == "audio_file":
        if _is_yaml_block(text):
            return _render_tts(engine, format_yaml_for_tts(text), rate=125)
        else:
            return _render_tts(engine, format_code_for_tts(text), rate=125)
    elif item_type == "qa":
        spoken = f"Question du jury. {item.get('question', '')}. Réponse. {item.get('answer', '')}."
        return _render_tts(engine, spoken, rate=145)
    # ── NOUVEAU : QCM avec question, options et explication ──────────────────
    elif item_type == "qcm":
        question = item.get("question", "")
        options = item.get("options", [])
        correct_idx = item.get("correct", 0)
        explanation = item.get("explanation", "")
        opts_spoken = ". ".join(
            f"Option {chr(65 + i)}: {opt}" for i, opt in enumerate(options)
        )
        correct_letter = chr(65 + correct_idx)
        spoken = (
            f"Question à choix multiples. {question}. "
            f"Les options sont: {opts_spoken}. "
            f"La bonne réponse est l'option {correct_letter}. "
            f"Explication: {explanation}."
        )
        return _render_tts(engine, spoken, rate=142)
    # ── NOUVEAU : Question de jury ouverte (titre + réponse modèle) ──────────
    elif item_type == "jury_open":
        title = item.get("title", "")
        model_answer = item.get("model_answer", "")
        spoken = (
            f"Question de jury. {title}. "
            f"Réponse modèle : {model_answer}."
        )
        return _render_tts(engine, spoken, rate=145)
    # ── FIN NOUVEAUX TYPES ───────────────────────────────────────────────────
    elif item_type == "jury":
        spoken = f"Attention, question piège du jury. {item.get('title', '')}. {text}"
        return _render_tts(engine, spoken, rate=148)
    elif item_type == "security":
        title = item.get("title", "")
        return _render_tts(engine, f"Point sécurité. {title}. {text}", rate=148)
    elif item_type in ("audio_code_explain", "audio_terminal_tip", "audio_analogy", "method", "concept", "conclusion"):
        title = item.get("title", "")
        prefix = f"{title}. " if title else ""
        return _render_tts(engine, prefix + text, rate=150)
    else:
        title = item.get("title", "")
        prefix = f"{title}. " if title else ""
        return _render_tts(engine, prefix + text, rate=150)

# ====================== CONTENU DE COURS ======================
COURSE_CONTENT = [
    {
        "id": "intro", "title": "Introduction & Méthode IA", "icon": "Brain",
        "content": [
            {"type": "intro", "text": "Bienvenue dans cette fiche de révision pour le Titre Professionnel Administrateur Système DevOps. Ce document couvre les onze compétences professionnelles du REAC. Je vais t'expliquer chaque notion comme si on était en cours ensemble."},
            {"type": "concept", "title": "La philosophie de l'IA en DevOps", "text": "L'IA n'est pas un copilote magique. C'est un junior qui code vite mais qui se trompe souvent. Ton rôle d'Admin Sys DevOps, c'est d'être le senior qui relit, comprend, teste et valide. L'IA est un outil, pas une solution magique. L'humain est le garant de la qualité et de la compréhension."},
            {"type": "method", "title": "La méthode IA en 5 étapes", "text": "Voici la méthode que tu dois maîtriser. Première étape : définir un objectif clair. Avant même de toucher au clavier, tu dois savoir quelle techno tu utilises, quelles sont tes contraintes, et quel résultat tu attends. C'est comme un plombier qui mesure avant de couper le tuyau."},
            {"type": "method", "text": "Deuxième étape : formuler le besoin correctement. Quand tu parles à l'IA, donne-lui le contexte, montre-lui ton code existant, donne un exemple d'entrée et de sortie attendue. C'est exactement comme rédiger un bon ticket Jira : titre précis, logs, version, comportement attendu."},
            {"type": "method", "text": "Troisième étape : récupérer le code généré et le copier dans un fichier de test. Jamais directement en production ! On ne merge pas sans review en équipe, c'est pareil ici."},
            {"type": "method", "text": "Quatrième étape : lire, comprendre et adapter. Tu dois être capable d'expliquer chaque bloc avec tes propres mots. Vérifie la sécurité, les performances, les versions, les contraintes métier."},
            {"type": "method", "text": "Cinquième étape : tester et corriger. Commence par les cas simples, puis les cas limites. Si ça bug, explique à l'IA ce qui se passe et itère. Un développeur sans tests, c'est comme un électricien qui n'utilise pas le multimètre."},
            {"type": "jury", "title": "Question piège du jury", "text": "Le jury pourrait te demander : Vous avez utilisé l'IA, donc vous ne comprenez pas votre code ? Ta réponse : Non, j'ai utilisé l'IA comme outil d'accélération. Pour chaque bloc généré, j'ai appliqué ma méthode : lire, comprendre, adapter, tester. Je peux expliquer chaque ligne de mon Dockerfile, de mon fichier Terraform, de mon pipeline CI/CD."},
        ],
    },
    {
        "id": "cp1", "title": "CP1 : Scripts Serveurs", "icon": "Terminal",
        "content": [
            {"type": "intro", "text": "Compétence 1 : Automatiser la création de serveurs à l'aide de scripts. Cette compétence couvre la virtualisation et les différents types de scripts."},
            {"type": "concept", "title": "Les types de virtualisation", "text": "Il existe trois types de virtualisation à connaître. Premier type : l'Hyperviseur de Type 1, comme VMware ESXi, KVM ou Hyper-V. Il s'installe directement sur le matériel. C'est utilisé en production."},
            {"type": "technical", "text": "Deuxième type : l'Hyperviseur de Type 2, comme VirtualBox ou VMware Workstation. Il s'installe sur un système d'exploitation existant. C'est utilisé pour le développement et les tests en local."},
            {"type": "technical", "text": "Troisième type : les Conteneurs, comme Docker. C'est une isolation légère qui partage le même noyau que le système hôte. Plus léger qu'une machine virtuelle complète."},
            {"type": "concept", "title": "Script Bash : structure de base", "text": "Un script Bash est une liste d'instructions shell exécutées dans l'ordre. Il sert à automatiser des actions manuelles dans un terminal. La première ligne est le shebang, qui indique l'interpréteur à utiliser."},
            {"type": "audio_command", "text": "#!/bin/bash"},
            {"type": "audio_terminal_tip", "text": "Astuce : Ajoute souvent set -e pour arrêter automatiquement le script si une commande échoue."},
            {"type": "technical", "title": "Exemple de script Bash d'installation", "text": "Un script typique d'installation serveur va d'abord mettre à jour la liste des paquets, puis installer les services nécessaires comme Nginx, le pare-feu UFW et fail2ban. Ensuite il active et démarre ces services."},
            {"type": "audio_command", "text": "sudo apt update && sudo apt upgrade -y"},
            {"type": "audio_command", "text": "sudo apt install -y nginx ufw fail2ban"},
            {"type": "audio_command", "text": "sudo systemctl enable --now nginx ufw fail2ban"},
            {"type": "concept", "title": "Script Python pour l'automatisation", "text": "Python peut aussi automatiser l'administration système. On utilise le module subprocess pour exécuter des commandes système."},
            {"type": "audio_code", "text": "import subprocess\nsubprocess.run([\"sudo\", \"apt\", \"update\"], check=True)"},
        ],
    },
    {
        "id": "cp2", "title": "CP2 : Terraform & Ansible", "icon": "Server",
        "content": [
            {"type": "intro", "text": "Compétence 2 : Automatiser le déploiement d'une infrastructure avec Terraform et Ansible. C'est fondamental pour ton titre pro."},
            {"type": "concept", "title": "Terraform vs Ansible : l'analogie imparable", "text": "Terraform, c'est l'architecte qui construit les murs et pose les fondations. Il crée ton infrastructure : les instances EC2, les VPC, les Security Groups, les buckets S3."},
            {"type": "technical", "text": "Ansible, c'est le décorateur qui arrive après et installe les meubles. Il installe Nginx, crée les utilisateurs, copie les fichiers de configuration. L'ordre est important : Terraform d'abord, Ansible ensuite."},
            {"type": "concept", "title": "Caractéristiques de Terraform", "text": "Terraform utilise le langage HCL, avec des fichiers point TF. Il est stateful, ce qui signifie qu'il garde un fichier d'état qui mémorise l'état de ton infrastructure."},
            {"type": "audio_terminal_tip", "text": "Règle d'or : ne jamais committer le fichier terraform.tfstate dans Git ! En équipe, on le stocke sur S3 avec un verrou DynamoDB."},
            {"type": "method", "title": "Commandes Terraform essentielles", "text": "init pour initialiser. validate pour vérifier la syntaxe. plan pour prévisualiser sans modifier. apply pour créer. destroy pour supprimer. output pour afficher les valeurs de sortie."},
            {"type": "audio_command", "text": "terraform init"},
            {"type": "audio_command", "text": "terraform validate"},
            {"type": "audio_command", "text": "terraform plan"},
            {"type": "audio_command", "text": "terraform apply"},
            {"type": "audio_command", "text": "terraform destroy"},
            {"type": "audio_command", "text": "terraform output"},
            {"type": "concept", "title": "Caractéristiques d'Ansible", "text": "Ansible utilise YAML avec des fichiers playbook. Il est idempotent : si tu rejoues le même playbook dix fois, tu obtiens le même résultat. Pas besoin d'agent sur les serveurs cibles, tout passe par SSH."},
            {"type": "audio_file", "text": "---\n- hosts: webservers\n  tasks:\n    - name: Install Nginx\n      apt:\n        name: nginx\n        state: present"},
            {"type": "audio_command", "text": "ansible all -m ping"},
            {"type": "audio_command", "text": "ansible-playbook playbook.yml --check"},
        ],
    },
    {
        "id": "cp3", "title": "CP3 : Sécurisation Infrastructure", "icon": "Shield",
        "content": [
            {"type": "intro", "text": "Compétence 3 : Sécuriser l'infrastructure. Un sujet que le jury adore. Quatre actions essentielles à connaître pour SSH."},
            {"type": "security", "title": "Action 1 : Désactiver le login root", "text": "Dans le fichier de configuration SSH, tu mets PermitRootLogin à no. Pourquoi ? C'est le principe du moindre privilège. Si le compte root est compromis, tout est perdu."},
            {"type": "audio_code", "text": "PermitRootLogin no"},
            {"type": "security", "title": "Action 2 : Clés SSH uniquement, pas de mot de passe", "text": "On désactive l'authentification par mot de passe et on n'autorise que les clés SSH. Une clé SSH ne peut pas être brute-forcée comme un mot de passe."},
            {"type": "audio_code", "text": "PasswordAuthentication no"},
            {"type": "security", "title": "Action 3 : Restreindre l'accès SSH par IP", "text": "Dans le Security Group AWS, on restreint le port 22 à ta seule adresse IP avec un CIDR slash 32. Si on ouvre à 0.0.0.0/0, n'importe qui peut tenter du brute force depuis Internet."},
            {"type": "audio_code", "text": "0.0.0.0/0"},
            {"type": "audio_code_explain", "text": "Ce CIDR zéro sur zéro signifie tout Internet. C'est à éviter absolument pour le port SSH."},
            {"type": "security", "title": "Action 4 : fail2ban contre le brute force", "text": "fail2ban surveille les tentatives de connexion échouées et bannit automatiquement les adresses IP suspectes. C'est ta dernière ligne de défense."},
            {"type": "jury", "title": "Question jury : pourquoi slash 32 sur SSH", "text": "Pourquoi un CIDR slash 32 sur SSH ? Ta réponse : Moindre privilège réseau. Seule mon IP peut atteindre le port 22. Si j'ouvre à 0.0.0.0 slash 0, n'importe qui peut tenter du brute force."},
        ],
    },
    {
        "id": "cp4", "title": "CP4 : Production Cloud", "icon": "Cloud",
        "content": [
            {"type": "intro", "text": "Compétence 4 : Mettre l'infrastructure en production dans le cloud. Comprendre les modèles de service et les composants AWS."},
            {"type": "concept", "title": "IaaS — Infrastructure as a Service", "text": "Tu gères l'OS, le runtime et l'application. Le provider gère le matériel et le réseau. Exemple : EC2 sur AWS. C'est ce que tu utilises dans ton projet."},
            {"type": "technical", "text": "PaaS — Platform as a Service : tu gères uniquement l'application et les données. Exemples : Heroku ou AWS Elastic Beanstalk."},
            {"type": "technical", "text": "SaaS — Software as a Service : tu gères uniquement la configuration utilisateur. Exemples : Gmail, Office 365, Salesforce."},
            {"type": "concept", "title": "Composants AWS du projet", "text": "Voici les composants que tu as déployés. Première brique : le VPC, ton réseau virtuel isolé."},
            {"type": "technical", "text": "Security Group : c'est le pare-feu virtuel AWS. SSH restreint à ton IP, HTTP et HTTPS ouverts au public. Internet Gateway : c'est la passerelle qui connecte ton VPC vers Internet. Instance EC2 de type t2.micro : ton serveur web, éligible au Free Tier AWS. Bucket S3 : le stockage pour tes fichiers statiques et tes backups."},
            {"type": "audio_code", "text": "10.0.0.0/16"},
            {"type": "audio_code_explain", "text": "Ce réseau en slash 16 te donne 65 536 adresses IP disponibles dans ton espace réseau privé."},
            {"type": "audio_code", "text": "10.0.1.0/24"},
            {"type": "audio_code_explain", "text": "Le subnet public en slash 24 te donne 256 adresses. C'est le sous-réseau accessible depuis Internet."},
            {"type": "jury", "title": "Question jury : pourquoi t2.micro", "text": "Pourquoi t2.micro ? C'est l'instance éligible au Free Tier AWS, suffisante pour un serveur web statique en contexte de formation. En production je dimensionnerais selon la charge avec AWS Cost Explorer."},
        ],
    },
    {
        "id": "cp5", "title": "CP5 : CI/CD & Tests", "icon": "GitBranch",
        "content": [
            {"type": "intro", "text": "Compétence 5 : Préparer un environnement de test. La démarche CI/CD et la méthodologie Agile."},
            {"type": "concept", "title": "CI/CD expliqué simplement", "text": "CI, Intégration Continue : chaque commit déclenche automatiquement le build et les tests. CD, Déploiement Continu : si les tests passent, le déploiement se fait automatiquement. C'est comme une chaîne de montage automobile."},
            {"type": "audio_code_explain", "text": "Ton pipeline complet : push sur la branche main, vérification du style Python avec flake8, tests avec pytest, build de l'image Docker taguée avec le SHA du commit, puis déploiement."},
            {"type": "technical", "title": "Pipeline GitHub Actions", "text": "Le trigger se déclenche sur push vers main. Le job tourne sur un runner ubuntu-latest. Il checkout le code, lance pytest, build l'image Docker taguée avec le SHA du commit, puis déploie."},
            {"type": "audio_file", "text": "name: CI/CD Pipeline\non:\n  push:\n    branches: [ main ]\njobs:\n  test:\n    runs-on: ubuntu-latest\n    steps:\n      - uses: actions/checkout@v2\n      - name: Run tests\n        run: pytest"},
            {"type": "audio_command", "text": "docker build -t myapp:${{ github.sha }} ."},
            {"type": "audio_code_explain", "text": "On utilise le SHA du commit comme tag Docker. Ça garantit la traçabilité : on sait exactement quel commit correspond à quelle image en production."},
            {"type": "concept", "title": "Vocabulaire Agile Scrum", "text": "Sprint : itération de une à quatre semaines. Backlog : liste des fonctionnalités priorisée. User Story : besoin exprimé du point de vue de l'utilisateur. Definition of Done : critères pour qu'une tâche soit terminée."},
            {"type": "method", "title": "Les environnements du pipeline", "text": "DEV en local sur WSL2, puis TEST avec pytest, puis Staging pour la validation métier, puis Production. Règle : chaque environnement doit être identique au suivant. Docker garantit ça."},
        ],
    },
    {
        "id": "cp6", "title": "CP6 : Stockage des Données", "icon": "Database",
        "content": [
            {"type": "intro", "text": "Compétence 6 : Gérer le stockage des données. SQLite, les types de stockage et les bonnes pratiques de sauvegarde."},
            {"type": "concept", "title": "SQLite dans ton projet", "text": "SQLite est une base de données fichier, sans serveur séparé. Choix justifié pour un projet solo ou à faible charge. Zéro configuration, zéro administration."},
            {"type": "jury", "title": "Question jury : Pourquoi SQLite ?", "text": "Pas de serveur séparé à gérer, adapté à un seul utilisateur. J'ai identifié la migration vers PostgreSQL comme évolution si le projet prend de l'ampleur et nécessite de la concurrence en écriture."},
            {"type": "concept", "title": "Les trois types de stockage", "text": "Stockage bloc comme AWS EBS : utilisé pour l'OS et les bases de données. Stockage fichier comme NFS ou AWS EFS : partage entre plusieurs serveurs. Stockage objet comme AWS S3 : fichiers statiques, backups, logs. Le moins cher et le plus scalable."},
            {"type": "audio_command", "text": "cp database.sqlite database_$(date +%Y%m%d).sqlite"},
            {"type": "audio_code_explain", "text": "La commande date avec le format année mois jour crée un nom de fichier unique à chaque sauvegarde. En production, on pousse ensuite vers S3 pour la redondance géographique."},
            {"type": "audio_terminal_tip", "text": "Règle d'or : tester régulièrement la restauration des sauvegardes. Une sauvegarde non testée n'est pas une sauvegarde."},
        ],
    },
    {
        "id": "cp7", "title": "CP7 : Docker & Containers", "icon": "Container",
        "content": [
            {"type": "intro", "text": "Compétence 7 : Gérer des containers. Docker est au cœur du DevOps moderne. Tu dois pouvoir expliquer ton Dockerfile ligne par ligne."},
            {"type": "audio_analogy", "text": "Un Dockerfile, c'est comme une recette de cuisine. FROM c'est tes ingrédients de base. RUN c'est les étapes de préparation. CMD c'est comment servir le plat."},
            {"type": "audio_code", "text": "FROM python:3.9-slim"},
            {"type": "audio_code_explain", "text": "FROM slim pour une image légère. Moins de failles de sécurité potentielles et une image plus petite à télécharger."},
            {"type": "audio_code", "text": "RUN useradd app"},
            {"type": "audio_code_explain", "text": "On crée un utilisateur non-root. Règle absolue : ne jamais faire tourner un conteneur en root en production."},
            {"type": "audio_code", "text": "COPY requirements.txt /app/"},
            {"type": "audio_code_explain", "text": "On copie requirements.txt avant le code source pour exploiter le cache des layers Docker. Si ton code change mais pas tes dépendances, Docker ne réinstalle pas tout."},
            {"type": "audio_code", "text": "COPY . /app/"},
            {"type": "audio_code", "text": "RUN pip install -r /app/requirements.txt"},
            {"type": "audio_code", "text": "EXPOSE 8501"},
            {"type": "audio_code_explain", "text": "EXPOSE 8501 : c'est de la documentation pour les développeurs. Le vrai mapping de port se fait au lancement avec docker run -p. EXPOSE seul n'ouvre rien."},
            {"type": "audio_code", "text": "CMD [\"python\", \"app.py\"]"},
            {"type": "audio_code_explain", "text": "CMD en tableau JSON : c'est la commande par défaut, surchargeable au lancement. Différent de ENTRYPOINT qui est fixe et non surchargeable."},
            {"type": "method", "title": "Commandes Docker essentielles", "text": "Les commandes à maîtriser absolument."},
            {"type": "audio_command", "text": "docker build -t myapp ."},
            {"type": "audio_command", "text": "docker run -d myapp"},
            {"type": "audio_command", "text": "docker ps"},
            {"type": "audio_command", "text": "docker logs -f mycontainer"},
            {"type": "audio_command", "text": "docker exec -it mycontainer bash"},
            {"type": "audio_command", "text": "docker stats"},
            {"type": "concept", "title": "Docker Compose", "text": "Docker Compose orchestre plusieurs containers. Tu définis tes services, les ports, les volumes pour la persistance, les variables d'environnement. Un seul fichier YAML pour tout décrire."},
            {"type": "audio_file", "text": "version: '3'\nservices:\n  web:\n    image: nginx\n    ports:\n      - \"80:80\"\n    volumes:\n      - ./html:/usr/share/nginx/html"},
            {"type": "audio_command", "text": "docker-compose up -d"},
            {"type": "audio_command", "text": "docker-compose down"},
        ],
    },
    {
        "id": "cp8", "title": "CP8 : Kubernetes", "icon": "Layers",
        "content": [
            {"type": "intro", "text": "Compétence 8 : Automatiser la mise en production avec Kubernetes. Même si Kubernetes n'est pas dans ton projet, tu dois pouvoir l'expliquer conceptuellement."},
            {"type": "concept", "title": "Architecture Kubernetes", "text": "Le Control Plane : le cerveau du cluster. API Server : point d'entrée de toutes les commandes. etcd : stocke l'état du cluster. Scheduler : décide sur quel noeud placer les Pods."},
            {"type": "audio_code_explain", "text": "Les Worker Nodes font tourner les Pods. Le kubelet est l'agent sur chaque node. Un Pod est la plus petite unité Kubernetes, il contient un ou plusieurs containers."},
            {"type": "technical", "title": "Deployment et Service", "text": "Un Deployment gère les Pods : réplication, rolling update, rollback automatique. Un Service expose les Pods sur le réseau avec une IP stable. C'est comme un load balancer interne."},
            {"type": "jury", "title": "Question jury : pourquoi pas Kubernetes", "text": "Pourquoi Kubernetes n'est pas dans votre projet ? Docker Compose couvre mes besoins actuels sur un seul serveur. Kubernetes apporterait haute disponibilité avec les replicas, rolling updates sans downtime, autoscaling, gestion multi-noeuds. Identifié comme évolution naturelle pour la production."},
            {"type": "method", "title": "Commandes kubectl essentielles", "text": "Les commandes kubectl à connaître."},
            {"type": "audio_command", "text": "kubectl apply -f deployment.yaml"},
            {"type": "audio_command", "text": "kubectl get pods"},
            {"type": "audio_command", "text": "kubectl logs -f monpod"},
            {"type": "audio_command", "text": "kubectl exec -it monpod -- bash"},
            {"type": "audio_command", "text": "kubectl rollout undo deployment/mondeployment"},
            {"type": "audio_command", "text": "kubectl scale deployment/mondeployment --replicas=3"},
        ],
    },
    {
        "id": "cp9", "title": "CP9 : Métriques & SLO", "icon": "BarChart",
        "content": [
            {"type": "intro", "text": "Compétence 9 : Définir et mettre en place des statistiques de services. SLI, SLO, SLA et tes métriques Prometheus."},
            {"type": "concept", "title": "SLI, SLO, SLA expliqués", "text": "SLI, Service Level Indicator : c'est la mesure réelle observée. Exemple : taux de succès API égal 98 pourcent. SLO, Service Level Objective : c'est l'objectif interne. Exemple : on vise 99,5 pourcent de succès. SLA, Service Level Agreement : c'est le contrat signé avec le client. Exemple : remboursement si disponibilité inférieure à 99 pourcent."},
            {"type": "technical", "title": "Error Budget", "text": "L'Error Budget c'est la marge d'erreur autorisée. Si ton SLO est de 99,5 pourcent, tu as 0,5 pourcent d'erreur tolérée. Ça représente environ 3 heures 30 de downtime par mois. Tant que tu restes dans ce budget, tu peux prendre des risques et innover."},
            {"type": "concept", "title": "Tes métriques Prometheus", "text": "Dans ton projet, tu exposes des métriques via prometheus_client sur le port 8000."},
            {"type": "audio_code", "text": "app_requests_total"},
            {"type": "audio_code_explain", "text": "Compteur du nombre total de requêtes reçues par l'application."},
            {"type": "audio_code", "text": "api_calls_total{status=\"success\"}"},
            {"type": "audio_code_explain", "text": "Compteur des appels API réussis, filtré par le label status égal success."},
            {"type": "audio_code", "text": "api_response_seconds"},
            {"type": "audio_code_explain", "text": "Histogramme du temps de réponse en secondes. Permet de calculer les percentiles P50, P90, P99."},
            {"type": "method", "title": "Seuils d'alerte à retenir", "text": "CPU supérieur à 80 pourcent pendant 5 minutes. RAM supérieure à 85 pourcent. Disque supérieur à 85 pourcent. Load average supérieur au nombre de CPUs."},
        ],
    },
    {
        "id": "cp10", "title": "CP10 : Monitoring Prometheus", "icon": "Activity",
        "content": [
            {"type": "intro", "text": "Compétence 10 : Exploiter une solution de supervision. Prometheus et Grafana. Question quasi-certaine au jury !"},
            {"type": "concept", "title": "Les trois ports à connaître par cœur", "text": "Port 8000 : ton application Python expose ses métriques sur l'endpoint slash metrics via prometheus_client. C'est Prometheus qui vient scraper ce port. Port 9090 : l'interface web de Prometheus. Port 3000 : Grafana, le dashboard de visualisation."},
            {"type": "jury", "title": "Question jury : pourquoi deux ports", "text": "Pourquoi deux ports 8000 et 9090 ? Port 8000 est exposé par mon application Python via prometheus_client. C'est l'endpoint que Prometheus scrape toutes les 15 secondes. Port 9090, c'est l'interface de Prometheus lui-même, qui centralise et stocke les métriques."},
            {"type": "audio_analogy", "text": "Prometheus est comme un facteur qui passe relever le courrier à heures fixes. Les applications n'ont pas besoin de savoir où envoyer, elles exposent juste leurs métriques sur /metrics. C'est le mode PULL, opposé au mode PUSH où l'application envoie elle-même les données."},
            {"type": "method", "title": "Requêtes PromQL essentielles", "text": "Cinq requêtes à connaître pour le jury."},
            {"type": "audio_code", "text": "api_calls_total{status=\"success\"}"},
            {"type": "audio_code_explain", "text": "Compteur total des appels réussis depuis le démarrage."},
            {"type": "audio_code", "text": "rate(api_calls_total{status=\"error\"}[5m])"},
            {"type": "audio_code_explain", "text": "Taux d'erreurs par seconde calculé sur une fenêtre glissante de 5 minutes. Idéal pour les alertes."},
            {"type": "audio_code", "text": "avg(api_response_seconds)"},
            {"type": "audio_code_explain", "text": "Temps de réponse moyen. Si ce chiffre monte, il y a peut-être un problème de performance."},
            {"type": "audio_code", "text": "up{job=\"monapp\"}"},
            {"type": "audio_code_explain", "text": "Retourne 1 si l'application est accessible, 0 si elle est down. C'est le check de disponibilité de base."},
            {"type": "concept", "title": "SNMP et Syslog", "text": "SNMP, Simple Network Management Protocol : supervise les équipements réseau comme les switches et routeurs. Syslog : protocole de centralisation des logs système. Prometheus fait pour les métriques applicatives ce que SNMP fait pour le matériel réseau."},
        ],
    },
    {
        "id": "cp11", "title": "CP11 : Anglais Professionnel", "icon": "Globe",
        "content": [
            {"type": "intro", "text": "Compétence 11 : Échanger sur des réseaux professionnels en anglais. Les communautés à connaître et le vocabulaire technique."},
            {"type": "concept", "title": "Communautés professionnelles", "text": "Stack Overflow pour résoudre des bugs. Server Fault pour les questions système et réseau. GitHub Discussions pour les projets open source. HashiCorp Forum pour Terraform. Reddit r/devops pour la veille. CNCF Slack pour la communauté Kubernetes."},
            {"type": "method", "title": "Vocabulaire anglais technique essentiel", "text": "Deployment : déploiement. Troubleshoot : diagnostiquer un problème. Workaround : contournement temporaire. Deprecated : obsolète. Throughput : débit de données. Overhead : surcharge de ressources. Upstream : le projet source d'origine. Rolling update : mise à jour progressive sans downtime."},
            {"type": "technical", "title": "Structure d'une question technique en anglais", "text": "Environment : ton OS et la version de l'outil. Problem : ce que tu observes. What you tried : ce que tu as déjà essayé. Error message : le message d'erreur exact. Question : ta question précise et concise."},
        ],
    },
    {
        "id": "transversal", "title": "Compétences Transversales", "icon": "Wrench",
        "content": [
            {"type": "intro", "text": "Compétences transversales : la résolution de problèmes et l'apprentissage continu."},
            {"type": "method", "title": "Étape 1 — OBSERVER", "text": "Que se passe-t-il ? Consulte les logs, les métriques, les messages d'erreur. Ne saute pas directement aux conclusions."},
            {"type": "method", "title": "Étape 2 — ISOLER", "text": "Depuis quand ? Quel composant est affecté ? Est-ce reproductible ? Quel est le périmètre de l'incident ?"},
            {"type": "method", "title": "Étape 3 — HYPOTHÈSE", "text": "Formule une cause probable basée sur les observations. Note-la avant d'agir."},
            {"type": "method", "title": "Étape 4 — TESTER", "text": "Vérifie l'hypothèse avec un seul changement à la fois. Sinon tu ne sauras pas ce qui a résolu le problème."},
            {"type": "method", "title": "Étape 5 — CORRIGER", "text": "Applique la correction définitive et documente l'incident dans un post-mortem pour que ça ne se reproduise pas."},
            {"type": "concept", "title": "Outils de diagnostic système", "text": "Les commandes de diagnostic à maîtriser."},
            {"type": "audio_command", "text": "journalctl -u nginx"},
            {"type": "audio_code_explain", "text": "Logs du service nginx via systemd."},
            {"type": "audio_command", "text": "docker logs moncontainer"},
            {"type": "audio_code_explain", "text": "Logs d'un conteneur Docker."},
            {"type": "audio_command", "text": "df -h"},
            {"type": "audio_code_explain", "text": "Espace disque disponible en format lisible."},
            {"type": "audio_command", "text": "free -h"},
            {"type": "audio_code_explain", "text": "Mémoire RAM disponible et utilisée."},
            {"type": "audio_command", "text": "ss -tuln"},
            {"type": "audio_code_explain", "text": "Ports en écoute sur le serveur. Très utile pour vérifier qu'un service est bien démarré."},
            {"type": "audio_command", "text": "ping 8.8.8.8"},
            {"type": "audio_code_explain", "text": "Test de connectivité réseau vers le DNS Google."},
            {"type": "concept", "title": "Sources de veille technologique", "text": "Documentation officielle AWS, HashiCorp pour Terraform et Vault, kubernetes.io pour Kubernetes. Le site de l'ANSSI pour les alertes et guides de sécurité. Le blog CNCF pour les tendances cloud native. Reddit r/devops pour les retours d'expérience de la communauté."},
        ],
    },
    {
        "id": "questions", "title": "Questions Jury : Réponses Flash", "icon": "HelpCircle",
        "content": [
            {"type": "intro", "text": "Les 10 questions types du jury avec les réponses flash. Entraîne-toi à les réciter avec tes propres mots !"},
            {"type": "qa", "question": "Présentez votre projet en 2 minutes", "answer": "TopGainersCrypto est une application web qui affiche les 10 crypto-monnaies les plus performantes sur 24h. Collecte : l'API CoinGecko fournit les prix en temps réel via HTTP JSON. Stockage : SQLite sauvegarde l'historique et sert de fallback si l'API est indisponible. Affichage : Streamlit génère l'interface web en Python pur, sans HTML ni JavaScript, avec rafraîchissement automatique toutes les 5 minutes et export CSV. Conteneurisation : Docker empaquète l'app dans une image python:3.9-slim avec un utilisateur non-root, Docker Compose orchestre l'ensemble. CI/CD : GitHub Actions lance 11 tests unitaires à chaque push — si tout passe, le build Docker se déclenche automatiquement. Monitoring : prometheus_client expose 5 métriques sur le port 8000, Prometheus les collecte et les rend interrogeables sur le port 9090 en PromQL. Déploiement public : Streamlit Community Cloud pour l'interface, Docker en local pour le développement et le monitoring."},
            {"type": "qa", "question": "Terraform vs Ansible ?", "answer": "Terraform provisionne l'infrastructure, il crée la VM, le réseau, le pare-feu sur AWS. Ansible configure ce qui tourne dessus, il installe Nginx, crée les utilisateurs. Terraform d'abord, Ansible ensuite."},
            {"type": "qa", "question": "Pourquoi un CIDR slash 32 sur SSH ?", "answer": "Moindre privilège réseau : seule mon IP peut atteindre le port 22. Si j'ouvre à 0.0.0.0 slash 0, n'importe qui peut tenter du brute force."},
            {"type": "qa", "question": "Explique ton Dockerfile", "answer": "FROM slim pour image légère. Utilisateur non-root par sécurité. COPY requirements avant le code pour le cache Docker. EXPOSE pour documenter le port. CMD pour la commande de démarrage."},
            {"type": "qa", "question": "Pourquoi deux ports 8000 et 9090 ?", "answer": "8000 c'est l'endpoint métriques de mon application exposé via prometheus_client. 9090 c'est l'interface Prometheus qui scrappe ce 8000 et stocke les métriques pour les rendre interrogeables."},
            {"type": "qa", "question": "Pourquoi SQLite et pas PostgreSQL ?", "answer": "Pas de serveur séparé à gérer, adapté à un seul utilisateur. J'ai identifié la migration vers PostgreSQL comme évolution si la charge augmente et nécessite de la concurrence en écriture."},
            {"type": "qa", "question": "Kubernetes, pourquoi pas dans le projet ?", "answer": "Docker Compose suffit pour un seul serveur et un seul utilisateur. Kubernetes apporterait haute disponibilité, rolling updates, autoscaling. Identifié comme évolution naturelle pour la production."},
            {"type": "qa", "question": "Comment tu as utilisé l'IA ?", "answer": "Comme outil d'accélération, pas comme solution magique. Pour chaque bloc généré : lu, vérifié sur des sources fiables, compris, testé, adapté. Je peux expliquer chaque ligne."},
            {"type": "qa", "question": "Ton app plante en prod, que fais-tu ?", "answer": "D'abord observer les logs avec docker logs. Vérifier les métriques Prometheus. Identifier depuis quand et quel composant. Formuler une hypothèse, tester un changement à la fois. Corriger et documenter dans un post-mortem."},
            {"type": "qa", "question": "Comment sécuriser davantage ?", "answer": "Ajouter HTTPS avec Let's Encrypt et Certbot. Stocker les secrets dans HashiCorp Vault. Appliquer les recommandations ANSSI de hardening Linux. Renforcer fail2ban et activer les audits avec auditd."},
            {"type": "conclusion", "title": "Message final", "text": "Rappelle-toi : le jury évalue ta compréhension, pas ta mémoire. Tu as les projets, tu as la logique, tu as la méthode. Explique avec tes propres mots pourquoi tu as fait chaque choix. Bonne chance pour ton titre pro ASD, Romain !"},
        ],
    },

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION PROJET : QCM TOPGAINERSCRYPTO — ENTRAÎNEMENT THÉORIQUE & PRATIQUE
    # Ajoutée pour la soutenance Executive Bachelor ASD de Romain RECULIN
    # ══════════════════════════════════════════════════════════════════════════
    {
        "id": "topgainers_qcm",
        "title": "Projet : QCM TopGainersCrypto",
        "icon": "ClipboardCheck",
        "content": [
            {
                "type": "intro",
                "text": (
                    "Entraînement QCM spécifique au projet TopGainersCrypto. "
                    "20 questions théoriques et pratiques couvrant toutes les compétences évaluées : "
                    "Python, Streamlit, SQLite, Docker, CI/CD GitHub Actions, Prometheus et sécurité. "
                    "Chaque question est suivie de la bonne réponse et d'une explication détaillée."
                ),
            },
            {
                "type": "project_overview",
                "title": "Présentation rapide du projet TopGainersCrypto",
                "text": (
                    "TopGainersCrypto est une **application web** développée en Python avec **Streamlit**, "
                    "conçue pour afficher en temps réel les **10 crypto-monnaies les plus performantes sur 24h**. "
                    "Elle s'appuie sur l'**API CoinGecko** pour récupérer les données de marché, "
                    "les stocke localement dans une base **SQLite** pour un historique et un fallback, "
                    "et les affiche via une interface simple et intuitive.\n\n"
            
                    "**Architecture technique :**\n"
                    "- **Frontend/Backend** : Streamlit (Python pur, sans HTML/JS).\n"
                    "- **Conteneurisation** : Docker (image légère `python:3.9-slim`, utilisateur non-root).\n"
                    "- **Orchestration** : Docker Compose pour gérer l'application et ses dépendances.\n"
                    "- **CI/CD** : GitHub Actions (11 tests unitaires + build automatique de l'image Docker).\n"
                    "- **Monitoring** : Prometheus (métriques exposées sur le port 8000, interface sur le port 9090).\n"
                    "- **Déploiement** : Streamlit Community Cloud pour la démo publique, Docker en local pour le développement.\n\n"
            
                    "**Points clés :**\n"
                    "- **Mise à jour automatique** toutes les 5 minutes.\n"
                    "- **Export CSV** des données affichées.\n"
                    "- **Sécurité** : CIDR /32 pour SSH, secrets gérés via `.env`, audit des dépendances Python.\n"
                    "- **Évolutions prévues** : Migration vers PostgreSQL, ajout de Kubernetes, renforcement HTTPS.\n\n"
            
                    "Ce projet illustre une **stack moderne** pour une application data-driven, "
                    "avec une attention particulière à la **maintenabilité**, la **sécurité** et l'**automatisation**."
                )
            },
            # ── SECTION 01 — Contexte & Projet ──────────────────────────────
            {
                "type": "qcm",
                "section": "Contexte & Projet",
                "question": "Quelle est la principale source de données de l'application TopGainersCrypto ?",
                "options": ["Binance API", "CoinGecko API", "CoinMarketCap API", "Yahoo Finance"],
                "correct": 1,
                "explanation": (
                    "L'application utilise l'API CoinGecko dans sa version gratuite, limitée à "
                    "environ 10 à 30 appels par minute. CoinGecko fournit les prix et variations "
                    "des crypto-monnaies en temps réel via des appels HTTP JSON."
                ),
            },
            {
                "type": "qcm",
                "section": "Contexte & Projet",
                "question": "Combien de crypto-monnaies sont affichées par défaut dans le tableau de bord ?",
                "options": ["5", "10", "20", "50"],
                "correct": 1,
                "explanation": (
                    "L'application affiche le Top 10 des crypto-monnaies avec la plus forte "
                    "progression sur 24 heures, avec leur prix et leur variation en pourcentage."
                ),
            },
            {
                "type": "qcm",
                "section": "Contexte & Projet",
                "question": "Quelle fonctionnalité a été abandonnée en cours de développement car jugée dispensable ?",
                "options": ["L'export CSV", "La mise à jour automatique", "La recherche par nom", "L'historique des données"],
                "correct": 2,
                "explanation": (
                    "La recherche par crypto-monnaie était prévue mais a été retirée. "
                    "L'export CSV, la mise à jour automatique toutes les 5 minutes et "
                    "l'historique SQLite ont tous été conservés et livrés."
                ),
            },
            # ── SECTION 02 — Architecture ────────────────────────────────────
            {
                "type": "qcm",
                "section": "Architecture technique",
                "question": "Quel est le rôle de SQLite dans ce projet ?",
                "options": [
                    "Remplacer entièrement l'API CoinGecko",
                    "Stocker l'historique et servir de fallback si l'API est indisponible",
                    "Gérer l'authentification des utilisateurs",
                    "Stocker les images des crypto-monnaies",
                ],
                "correct": 1,
                "explanation": (
                    "SQLite joue deux rôles : premièrement stocker l'historique des données "
                    "récupérées avec horodatage, deuxièmement servir de fallback — si l'API "
                    "CoinGecko est indisponible, l'app affiche les dernières données connues "
                    "en base plutôt que de planter."
                ),
            },
            {
                "type": "qcm",
                "section": "Architecture technique",
                "question": "Quelle version de Python est utilisée dans ce projet ?",
                "options": ["Python 2.7", "Python 3.6", "Python 3.9", "Python 3.12"],
                "correct": 2,
                "explanation": (
                    "Python 3.9 est utilisé, correspondant à l'image Docker de base "
                    "python:3.9-slim. Cette version est stable et compatible avec toutes "
                    "les dépendances utilisées : Streamlit, prometheus_client, SQLite."
                ),
            },
            {
                "type": "qcm",
                "section": "Architecture technique",
                "question": "Quel est le rôle du fichier logging_conf.py ?",
                "options": [
                    "Configurer uniquement les logs applicatifs",
                    "Configurer Docker Compose",
                    "Configurer les logs ET les métriques Prometheus",
                    "Gérer la connexion à l'API CoinGecko",
                ],
                "correct": 2,
                "explanation": (
                    "logging_conf.py gère à la fois la configuration des logs applicatifs "
                    "pour détecter les erreurs, et l'exposition des métriques Prometheus "
                    "via prometheus_client sur le port 8000."
                ),
            },
            # ── SECTION 03 — Docker ──────────────────────────────────────────
            {
                "type": "qcm",
                "section": "Conteneurisation Docker",
                "question": "Quelle image Docker de base est utilisée et pourquoi 'slim' ?",
                "options": [
                    "ubuntu:latest — pour avoir tous les outils système",
                    "python:3.9-slim — pour réduire la taille et les failles potentielles",
                    "alpine:3.9 — pour la compatibilité maximale",
                    "debian:buster — pour la stabilité",
                ],
                "correct": 1,
                "explanation": (
                    "python:3.9-slim est choisie pour minimiser la taille de l'image Docker. "
                    "L'image slim supprime les outils de développement et fichiers non "
                    "nécessaires à l'exécution, réduisant aussi la surface d'attaque."
                ),
            },
            {
                "type": "qcm",
                "section": "Conteneurisation Docker",
                "question": "Pourquoi crée-t-on un utilisateur 'appuser' non-root dans le Dockerfile ?",
                "options": [
                    "Pour accélérer le démarrage du conteneur",
                    "Par convention Docker, sans impact réel sur la sécurité",
                    "Principe du moindre privilège — limiter les droits en cas de compromission",
                    "Pour permettre l'accès SSH au conteneur",
                ],
                "correct": 2,
                "explanation": (
                    "Principe du moindre privilège : si l'application est compromise, "
                    "l'attaquant ne dispose que des droits de appuser, pas de root. "
                    "Créé via adduser --disabled-password --gecos apostrophe apostrophe appuser."
                ),
            },
            {
                "type": "qcm",
                "section": "Conteneurisation Docker",
                "question": "Quel port expose quoi dans ce projet Docker ?",
                "options": [
                    "8501 Prometheus, 9090 Streamlit, 8000 Métriques",
                    "8501 Streamlit, 8000 Métriques Prometheus, 9090 Interface Prometheus",
                    "80 Streamlit, 443 Prometheus, 22 SSH",
                    "3000 Streamlit, 9090 Prometheus, 8080 API",
                ],
                "correct": 1,
                "explanation": (
                    "Trois ports : 8501 pour l'interface Streamlit accessible dans le "
                    "navigateur, 8000 pour les métriques brutes exposées par prometheus_client, "
                    "9090 pour l'interface graphique de Prometheus avec PromQL."
                ),
            },
            {
                "type": "qcm",
                "section": "Conteneurisation Docker",
                "question": "Que fait la directive 'restart: unless-stopped' dans docker-compose.yml ?",
                "options": [
                    "Redémarre le conteneur uniquement au démarrage du système",
                    "Redémarre automatiquement si crash, sauf si arrêt manuel",
                    "Empêche tout redémarrage automatique",
                    "Redémarre le conteneur toutes les heures",
                ],
                "correct": 1,
                "explanation": (
                    "restart: unless-stopped signifie : redémarre automatiquement si le "
                    "conteneur s'arrête de façon inattendue, mais ne redémarre pas si "
                    "l'arrêt a été fait manuellement avec docker stop. "
                    "Garantit la disponibilité de l'application."
                ),
            },
            {
                "type": "qcm",
                "section": "Conteneurisation Docker",
                "question": "Pourquoi utilise-t-on un volume Docker pour /app/data ?",
                "options": [
                    "Pour accélérer les requêtes SQLite",
                    "Parce que SQLite ne fonctionne pas dans un conteneur",
                    "Pour que les données persistent après redémarrage ou recréation du conteneur",
                    "Pour partager la base entre plusieurs conteneurs simultanément",
                ],
                "correct": 2,
                "explanation": (
                    "Sans volume, la base SQLite est dans le conteneur et perdue à chaque "
                    "docker-compose down. Avec le volume ./data:/app/data, les données sont "
                    "sur l'hôte et survivent aux redémarrages et reconstructions d'image."
                ),
            },
            # ── SECTION 04 — CI/CD ───────────────────────────────────────────
            {
                "type": "qcm",
                "section": "CI/CD GitHub Actions",
                "question": "Combien de tests unitaires ont été écrits et quel est leur résultat ?",
                "options": [
                    "5 tests, 2 échecs",
                    "11 tests, 100% de réussite",
                    "7 tests, 100% de réussite",
                    "15 tests, 3 ignorés",
                ],
                "correct": 1,
                "explanation": (
                    "11 tests au total : 4 dans test_top_movers.py testant succès API, "
                    "échec, réponse vide et erreur réseau, et 7 dans test_database.py "
                    "testant création table, idempotence, structure et insertions. "
                    "Tous passent : 0 erreur, 0 échec."
                ),
            },
            {
                "type": "qcm",
                "section": "CI/CD GitHub Actions",
                "question": "Qu'est-ce que le 'mocking' dans le contexte des tests ?",
                "options": [
                    "Simuler de fausses données crypto pour l'interface",
                    "Remplacer l'appel réel à l'API CoinGecko par une réponse simulée",
                    "Créer une base de données temporaire pour les tests",
                    "Vérifier manuellement les résultats des tests",
                ],
                "correct": 1,
                "explanation": (
                    "Le mocking simule l'API CoinGecko sans faire de vrai appel réseau. "
                    "On contrôle exactement ce que renvoie l'API pour tester tous les cas "
                    "de façon rapide et déterministe : succès, erreur, réponse vide, timeout."
                ),
            },
            {
                "type": "qcm",
                "section": "CI/CD GitHub Actions",
                "question": "Quelle est la différence entre CI et CD ?",
                "options": [
                    "CI tests manuels, CD tests automatiques",
                    "CI intégration continue avec tests auto à chaque push, CD déploiement continu si CI passe",
                    "CI Docker, CD GitHub Actions",
                    "Aucune différence, c'est le même concept",
                ],
                "correct": 1,
                "explanation": (
                    "CI, Continuous Integration : à chaque push, les tests se lancent "
                    "automatiquement. Si un test échoue, on est immédiatement alerté. "
                    "CD, Continuous Deployment : si la CI passe, le build Docker et le "
                    "déploiement se font automatiquement sans intervention manuelle."
                ),
            },
            # ── SECTION 05 — Prometheus ──────────────────────────────────────
            {
                "type": "qcm",
                "section": "Monitoring Prometheus",
                "question": "Comment Prometheus collecte-t-il les métriques de l'application ?",
                "options": [
                    "Mode PUSH — l'application envoie les métriques à Prometheus toutes les minutes",
                    "Mode PULL — Prometheus vient chercher les métriques sur l'endpoint :8000/metrics",
                    "Mode PUSH — Prometheus envoie des requêtes à l'application",
                    "Les deux modes simultanément",
                ],
                "correct": 1,
                "explanation": (
                    "Prometheus fonctionne en mode PULL ou scrape : c'est lui qui interroge "
                    "l'endpoint /metrics de l'application à intervalles réguliers, toutes les "
                    "10 secondes dans ce projet. L'application n'envoie rien, elle expose."
                ),
            },
            {
                "type": "qcm",
                "section": "Monitoring Prometheus",
                "question": "Sur quelle URL peut-on consulter les métriques brutes de l'application ?",
                "options": [
                    "http://localhost:8501/metrics",
                    "http://localhost:9090/metrics",
                    "http://localhost:8000/metrics",
                    "http://localhost:3000/metrics",
                ],
                "correct": 2,
                "explanation": (
                    "Les métriques brutes sont exposées par prometheus_client sur le port 8000. "
                    "Le port 9090 est l'interface Prometheus elle-même. "
                    "Le port 8501 est Streamlit. Le port 3000 serait Grafana."
                ),
            },
            # ── SECTION 06 — Compétences ─────────────────────────────────────
            {
                "type": "qcm",
                "section": "Compétences du titre",
                "question": "Parmi ces éléments, lequel n'est PAS utilisé dans le projet TopGainersCrypto ?",
                "options": ["Kubernetes", "Docker Compose", "GitHub Actions", "Prometheus"],
                "correct": 0,
                "explanation": (
                    "Kubernetes n'est pas utilisé dans ce projet. C'est d'ailleurs cité "
                    "comme piste d'amélioration future. Le projet utilise Docker Compose "
                    "pour l'orchestration, GitHub Actions pour le CI/CD et Prometheus "
                    "pour le monitoring."
                ),
            },
            {
                "type": "qcm",
                "section": "Compétences du titre",
                "question": "Comment l'application garantit-elle de ne pas stocker de clés API dans le code source ?",
                "options": [
                    "Les clés sont chiffrées dans le code",
                    "Il n'y a pas de clé API nécessaire",
                    "Variables d'environnement dans un fichier .env listé dans .gitignore",
                    "Les clés sont stockées dans la base SQLite",
                ],
                "correct": 2,
                "explanation": (
                    "Bonne pratique de sécurité : les clés API sont dans un fichier .env "
                    "via variables d'environnement, jamais dans le code source. "
                    "Le .gitignore exclut ce fichier des commits. "
                    "Ne jamais committer de secrets sur un dépôt public."
                ),
            },
            {
                "type": "qcm",
                "section": "Compétences du titre",
                "question": "Quelle plateforme cloud héberge l'interface Streamlit publiquement ?",
                "options": [
                    "AWS Elastic Beanstalk",
                    "Google Cloud Run",
                    "Streamlit Community Cloud",
                    "Heroku",
                ],
                "correct": 2,
                "explanation": (
                    "Streamlit Community Cloud permet de déployer gratuitement une app "
                    "Streamlit depuis un repo GitHub public. Docker est utilisé en local "
                    "pour le développement et le monitoring Prometheus."
                ),
            },
            {
                "type": "qcm",
                "section": "Compétences du titre",
                "question": "Quelle commande permet d'accéder à un conteneur sans ouvrir de port SSH ?",
                "options": [
                    "docker ssh <conteneur>",
                    "docker attach <conteneur>",
                    "docker exec -it <conteneur> bash",
                    "docker connect <conteneur>",
                ],
                "correct": 2,
                "explanation": (
                    "docker exec -it <conteneur> bash ouvre un shell interactif dans le "
                    "conteneur sans serveur SSH. C'est la méthode recommandée. "
                    "SSH n'est utile que pour accéder à une machine hôte distante, "
                    "pas à un conteneur local."
                ),
            },
        ],
    },

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION PROJET : QUESTIONS DE JURY OUVERTES — TOPGAINERSCRYPTO
    # ══════════════════════════════════════════════════════════════════════════
    {
        "id": "topgainers_jury",
        "title": "Projet : Questions de Jury",
        "icon": "Mic",
        "content": [
            {
                "type": "intro",
                "text": (
                    "12 questions ouvertes types que le jury ASD pose systématiquement "
                    "sur le projet TopGainersCrypto. Pour chaque question, écoute la "
                    "réponse modèle et entraîne-toi à la reformuler avec tes propres mots. "
                    "Le jury évalue ta compréhension, pas ta mémoire."
                ),
            },
            {
                "type": "jury_open",
                "title": "Pourquoi avoir choisi SQLite plutôt que PostgreSQL ou MySQL ?",
                "model_answer": (
                    "SQLite est adapté à ce projet pour plusieurs raisons : il ne nécessite "
                    "pas de serveur dédié, son fichier s'intègre naturellement dans un volume "
                    "Docker, et le projet n'a pas besoin de concurrence élevée ni de "
                    "multi-utilisateurs. C'est un choix pragmatique cohérent avec la taille "
                    "du projet. J'ai identifié PostgreSQL comme piste d'amélioration si le "
                    "projet devait passer à l'échelle."
                ),
            },
            {
                "type": "jury_open",
                "title": "Comment fonctionne le fallback quand l'API CoinGecko est indisponible ?",
                "model_answer": (
                    "Quand l'appel à l'API échoue, timeout ou rate limit, le code Python dans "
                    "top_movers.py intercepte l'exception, logue l'erreur, et requête la base "
                    "SQLite pour récupérer les dernières données enregistrées. Streamlit "
                    "affiche ces données avec un message indiquant qu'il s'agit du cache. "
                    "L'application reste accessible et ne plante pas."
                ),
            },
            {
                "type": "jury_open",
                "title": "Quelle est la différence entre une image Docker et un conteneur ?",
                "model_answer": (
                    "Une image Docker est un modèle figé et immuable, c'est la recette. "
                    "Un conteneur est une instance en cours d'exécution de cette image. "
                    "On peut créer plusieurs conteneurs identiques depuis la même image. "
                    "Dans ce projet : le Dockerfile définit l'image, "
                    "docker-compose up crée les conteneurs."
                ),
            },
            {
                "type": "jury_open",
                "title": "Si un test unitaire échoue dans votre pipeline, que se passe-t-il ?",
                "model_answer": (
                    "GitHub Actions bloque le workflow à l'étape des tests. "
                    "Le build Docker et le déploiement ne se déclenchent pas. "
                    "Une notification est envoyée. C'est l'intérêt du CI : empêcher "
                    "une régression d'atteindre la production. Sur mon projet, "
                    "tous les tests passent à chaque push, garantissant que le code "
                    "est dans un état déployable."
                ),
            },
            {
                "type": "jury_open",
                "title": "Pouvez-vous expliquer la ligne COPY requirements.txt . dans le Dockerfile ?",
                "model_answer": (
                    "Cette ligne copie requirements.txt de la machine hôte vers le répertoire "
                    "de travail dans le conteneur. On le copie AVANT le code source pour "
                    "profiter du cache Docker : si requirements.txt n'a pas changé, "
                    "Docker réutilise la couche d'installation des dépendances sans tout "
                    "réinstaller, ce qui accélère les builds."
                ),
            },
            {
                "type": "jury_open",
                "title": "Qu'est-ce que PromQL et pouvez-vous donner un exemple concret ?",
                "model_answer": (
                    "PromQL est le langage de requête de Prometheus pour analyser les métriques. "
                    "Exemple concret : rate de api_calls_total avec status error sur 5 minutes "
                    "calcule le taux d'erreurs API sur les 5 dernières minutes. "
                    "Autre exemple : rate de api_response_seconds_sum sur rate de "
                    "api_response_seconds_count donne le temps de réponse moyen."
                ),
            },
            {
                "type": "jury_open",
                "title": "Qu'avez-vous appris de ce projet que vous n'auriez pas appris autrement ?",
                "model_answer": (
                    "Plusieurs choses concrètes. Premièrement Docker m'a appris que "
                    "ça marche sur ma machine n'est pas une réponse. "
                    "Deuxièmement tester son code force à mieux le structurer. "
                    "Troisièmement surveiller une application c'est mesurer son comportement, "
                    "pas attendre la panne. Quatrièmement construire quelque chose de "
                    "fonctionnel en Python depuis presque zéro donne confiance pour "
                    "apprendre d'autres technologies."
                ),
            },
            {
                "type": "jury_open",
                "title": "Comment géreriez-vous une montée en charge si 1000 utilisateurs consultaient l'app ?",
                "model_answer": (
                    "Dans l'état actuel l'architecture ne supporte pas 1000 utilisateurs. "
                    "Les pistes d'évolution identifiées sont : passer à Kubernetes pour "
                    "la scalabilité horizontale, remplacer SQLite par PostgreSQL pour "
                    "la concurrence, ajouter un cache Redis pour limiter les appels API, "
                    "et mettre en place un load balancer devant plusieurs instances Streamlit."
                ),
            },
            {
                "type": "jury_open",
                "title": "Pourquoi avoir choisi Streamlit plutôt que Flask ou FastAPI ?",
                "model_answer": (
                    "Streamlit permet de créer une interface web en Python pur, sans HTML, "
                    "CSS ou JavaScript. Comme j'apprenais Python en même temps que DevOps, "
                    "c'était cohérent avec mon niveau et les objectifs du projet. "
                    "Flask ou FastAPI auraient nécessité du développement front-end. "
                    "Streamlit a aussi l'avantage de son Community Cloud pour un "
                    "déploiement rapide et gratuit."
                ),
            },
            {
                "type": "jury_open",
                "title": "Qu'est-ce que le principe du moindre privilège et comment l'avez-vous appliqué ?",
                "model_answer": (
                    "Le principe du moindre privilège signifie que chaque composant ne doit "
                    "avoir accès qu'à ce qui lui est strictement nécessaire. Dans ce projet : "
                    "l'utilisateur appuser dans Docker n'a pas les droits root, les clés API "
                    "sont en variables d'environnement jamais dans le code, et le gitignore "
                    "protège les fichiers sensibles. Ce principe m'était déjà familier "
                    "dans mon contexte support IT pour la gestion des droits utilisateurs."
                ),
            },
            {
                "type": "jury_open",
                "title": "En quoi ce projet couvre-t-il toutes les compétences du titre ASD ?",
                "model_answer": (
                    "Chacune des 10 compétences est adressée : automatisation serveur via "
                    "setup-app-server.sh, déploiement automatisé via Docker et CI/CD, "
                    "sécurisation via variables d'environnement et utilisateur non-root, "
                    "mise en production cloud via Streamlit Community Cloud, "
                    "environnement de test via pytest avec 11 tests, "
                    "stockage données via SQLite et volumes Docker, "
                    "gestion conteneurs via Docker Compose, "
                    "automatisation mise en prod via GitHub Actions, "
                    "statistiques services via 4 métriques Prometheus, "
                    "et supervision via l'interface Prometheus avec PromQL."
                ),
            },
            {
                "type": "jury_open",
                "title": "Quels sont les points faibles ou les limites de votre projet ?",
                "model_answer": (
                    "Honnêteté importante ici. Prometheus n'a pas été exploité à son plein "
                    "potentiel : pas de dashboards Grafana ni d'alertes configurées. "
                    "L'API CoinGecko gratuite limite les appels et donc la fraîcheur des données. "
                    "Streamlit n'est pas adapté à une vraie charge de production. "
                    "Pas de graphiques d'évolution des prix, fonctionnalité prévue non réalisée. "
                    "Architecture mono-instance non scalable. "
                    "Ce sont des pistes d'amélioration réalistes et identifiées."
                ),
            },
        ],
    },
]

# ====================== HTML FRONTEND ======================
FRONTEND_HTML = """<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Révision ASD — Titre Pro</title>
<style>
  :root {
    --bg: #0f1117;
    --surface: #1a1d27;
    --surface2: #22263a;
    --border: #2e3248;
    --accent: #4f7cff;
    --accent2: #7c3aed;
    --green: #22c55e;
    --amber: #f59e0b;
    --red: #ef4444;
    --cyan: #06b6d4;
    --text: #e2e8f0;
    --text2: #94a3b8;
    --text3: #64748b;
    --mono: 'JetBrains Mono', 'Fira Code', monospace;
    --sans: 'Inter', system-ui, sans-serif;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: var(--sans);
    background: var(--bg);
    color: var(--text);
    min-height: 100vh;
    display: flex;
    flex-direction: column;
  }
  /* Header */
  header {
    padding: 16px 24px;
    background: var(--surface);
    border-bottom: 1px solid var(--border);
    display: flex;
    align-items: center;
    gap: 16px;
    flex-wrap: wrap;
    position: sticky;
    top: 0;
    z-index: 100;
  }
  .logo {
    font-size: 15px;
    font-weight: 700;
    color: var(--accent);
    letter-spacing: -0.02em;
    white-space: nowrap;
  }
  .logo span { color: var(--text2); font-weight: 400; }
  /* Status bar */
  .status-bar {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-left: auto;
    flex-wrap: wrap;
  }
  .status-dot {
    width: 8px; height: 8px;
    border-radius: 50%;
    background: var(--text3);
    transition: background 0.3s;
    flex-shrink: 0;
  }
  .status-dot.playing { background: var(--green); box-shadow: 0 0 6px var(--green); animation: pulse 1s infinite; }
  @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.5} }
  #status-text { font-size: 13px; color: var(--text2); white-space: nowrap; }
  /* Controls */
  .controls { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
  select, button {
    font-family: var(--sans);
    font-size: 12px;
    padding: 5px 10px;
    border-radius: 6px;
    border: 1px solid var(--border);
    background: var(--surface2);
    color: var(--text);
    cursor: pointer;
    transition: border-color 0.15s, background 0.15s;
    outline: none;
  }
  select:hover, button:hover { border-color: var(--accent); }
  button.stop { border-color: var(--red); color: var(--red); }
  button.stop:hover { background: rgba(239,68,68,0.1); }
  .lang-toggle {
    display: flex;
    border: 1px solid var(--border);
    border-radius: 6px;
    overflow: hidden;
  }
  .lang-toggle button {
    border: none;
    border-radius: 0;
    padding: 5px 12px;
    background: transparent;
    color: var(--text2);
  }
  .lang-toggle button.active {
    background: var(--accent);
    color: #fff;
  }
  /* Layout */
  .main { display: flex; flex: 1; overflow: hidden; }
  /* Sidebar */
  aside {
    width: 220px;
    flex-shrink: 0;
    background: var(--surface);
    border-right: 1px solid var(--border);
    overflow-y: auto;
    padding: 12px 8px;
  }
  .aside-title {
    font-size: 10px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: var(--text3);
    padding: 4px 8px 8px;
  }
  .aside-separator {
    font-size: 9px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    color: var(--amber);
    padding: 12px 8px 4px;
    border-top: 1px solid var(--border);
    margin-top: 6px;
  }
  .nav-item {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 8px 10px;
    border-radius: 6px;
    cursor: pointer;
    font-size: 13px;
    color: var(--text2);
    transition: background 0.15s, color 0.15s;
    border: none;
    background: none;
    width: 100%;
    text-align: left;
  }
  .nav-item:hover { background: var(--surface2); color: var(--text); }
  .nav-item.active { background: rgba(79,124,255,0.15); color: var(--accent); font-weight: 500; }
  .nav-item.project-item { color: #fbbf24; }
  .nav-item.project-item:hover { background: rgba(245,158,11,0.1); color: var(--amber); }
  .nav-item.project-item.active { background: rgba(245,158,11,0.15); color: var(--amber); }
  .nav-item .nav-label { flex: 1; line-height: 1.3; }
  .nav-item .progress-dot {
    width: 6px; height: 6px;
    border-radius: 50%;
    background: var(--green);
    flex-shrink: 0;
    opacity: 0;
    transition: opacity 0.3s;
  }
  .nav-item.done .progress-dot { opacity: 1; }
  /* Content area */
  .content-wrap {
    flex: 1;
    overflow-y: auto;
    padding: 24px;
  }
  .section-header {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 20px;
    padding-bottom: 16px;
    border-bottom: 1px solid var(--border);
  }
  .section-title { font-size: 20px; font-weight: 700; letter-spacing: -0.02em; }
  .section-hint { font-size: 13px; color: var(--text3); margin-top: 2px; }
  .items-list { display: flex; flex-direction: column; gap: 6px; }
  /* Item blocks */
  .item-block {
    padding: 12px 14px;
    border-radius: 8px;
    border: 1px solid var(--border);
    cursor: pointer;
    transition: border-color 0.15s, background 0.15s, transform 0.1s;
    position: relative;
    overflow: hidden;
  }
  .item-block::before {
    content: '';
    position: absolute;
    left: 0; top: 0; bottom: 0;
    width: 3px;
    background: transparent;
    transition: background 0.15s;
  }
  .item-block:hover { border-color: var(--border); background: var(--surface2); }
  .item-block:hover::before { background: var(--accent); }
  .item-block:active { transform: scale(0.995); }
  /* States */
  .item-block.highlighted { background: rgba(79,124,255,0.08); border-color: rgba(79,124,255,0.4); }
  .item-block.highlighted::before { background: var(--accent); }
  .item-block.playing { background: rgba(34,197,94,0.08); border-color: rgba(34,197,94,0.4); }
  .item-block.playing::before { background: var(--green); }
  /* Type badge */
  .type-badge {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    font-size: 10px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    padding: 2px 7px;
    border-radius: 4px;
    margin-bottom: 6px;
  }
  .badge-intro    { background: rgba(100,116,139,0.2); color: #94a3b8; }
  .badge-concept  { background: rgba(79,124,255,0.15); color: #7ca3ff; }
  .badge-method   { background: rgba(124,58,237,0.15); color: #a78bfa; }
  .badge-technical{ background: rgba(6,182,212,0.12); color: #22d3ee; }
  .badge-security { background: rgba(239,68,68,0.12); color: #f87171; }
  .badge-jury     { background: rgba(245,158,11,0.15); color: #fbbf24; }
  .badge-command  { background: rgba(34,197,94,0.12); color: #4ade80; }
  .badge-code     { background: rgba(6,182,212,0.12); color: #22d3ee; }
  .badge-explain  { background: rgba(100,116,139,0.15); color: #94a3b8; }
  .badge-tip      { background: rgba(245,158,11,0.15); color: #fbbf24; }
  .badge-analogy  { background: rgba(124,58,237,0.12); color: #c4b5fd; }
  .badge-file     { background: rgba(6,182,212,0.12); color: #22d3ee; }
  .badge-qa       { background: rgba(245,158,11,0.15); color: #fbbf24; }
  .badge-conclusion{ background: rgba(34,197,94,0.12); color: #4ade80; }
  /* Nouveaux badges pour les sections projet */
  .badge-qcm      { background: rgba(79,124,255,0.2); color: #93c5fd; }
  .badge-jury-open{ background: rgba(245,158,11,0.2); color: #fcd34d; }
  .item-title { font-size: 14px; font-weight: 600; color: var(--text); margin-bottom: 4px; }
  .item-text  { font-size: 14px; color: var(--text2); line-height: 1.65; }
  /* Code block */
  .item-code {
    font-family: var(--mono);
    font-size: 12.5px;
    color: #a5f3fc;
    background: rgba(0,0,0,0.35);
    padding: 10px 12px;
    border-radius: 6px;
    white-space: pre-wrap;
    word-break: break-all;
    line-height: 1.6;
    border: 1px solid rgba(6,182,212,0.2);
  }
  /* Q&A */
  .qa-question {
    font-size: 14px;
    font-weight: 600;
    color: var(--text);
    margin-bottom: 6px;
    display: flex;
    align-items: flex-start;
    gap: 8px;
  }
  .qa-q-badge {
    font-size: 10px;
    font-weight: 700;
    background: rgba(245,158,11,0.2);
    color: #fbbf24;
    padding: 2px 6px;
    border-radius: 4px;
    flex-shrink: 0;
    margin-top: 2px;
  }
  .qa-answer {
    font-size: 14px;
    color: var(--text2);
    line-height: 1.65;
    padding-left: 32px;
    border-left: 2px solid rgba(34,197,94,0.3);
    margin-left: 0;
  }
  /* QCM block */
  .qcm-question { font-size: 14px; font-weight: 600; color: var(--text); margin-bottom: 8px; }
  .qcm-section-tag {
    font-size: 10px; font-weight: 600;
    color: #93c5fd; background: rgba(79,124,255,0.12);
    padding: 1px 6px; border-radius: 3px;
    margin-bottom: 6px; display: inline-block;
  }
  .qcm-options { display: flex; flex-direction: column; gap: 4px; margin-bottom: 8px; }
  .qcm-option {
    font-size: 13px; color: var(--text2);
    padding: 4px 8px; border-radius: 4px;
    display: flex; align-items: flex-start; gap: 6px;
  }
  .qcm-option.correct-opt { color: var(--green); font-weight: 600; }
  .qcm-option-letter {
    font-size: 10px; font-weight: 700;
    min-width: 18px; height: 18px;
    border-radius: 50%;
    background: var(--surface2);
    color: var(--text3);
    display: flex; align-items: center; justify-content: center;
    flex-shrink: 0; margin-top: 1px;
  }
  .qcm-option.correct-opt .qcm-option-letter { background: rgba(34,197,94,0.2); color: var(--green); }
  .qcm-explanation {
    font-size: 13px; color: var(--text3);
    border-left: 2px solid rgba(79,124,255,0.3);
    padding-left: 8px; line-height: 1.55;
  }
  /* Jury open block */
  .jury-open-question { font-size: 14px; font-weight: 600; color: #fbbf24; margin-bottom: 8px; }
  .jury-open-answer {
    font-size: 13px; color: var(--text2); line-height: 1.65;
    border-left: 2px solid rgba(245,158,11,0.35);
    padding-left: 10px;
  }
  /* Play indicator */
  .play-icon {
    position: absolute;
    right: 12px;
    top: 50%;
    transform: translateY(-50%);
    font-size: 12px;
    color: var(--text3);
    opacity: 0;
    transition: opacity 0.15s;
  }
  .item-block:hover .play-icon { opacity: 0.6; }
  .item-block.playing .play-icon { opacity: 1; color: var(--green); animation: pulse 1s infinite; }
  /* Speed badge */
  .speed-info {
    font-size: 10px;
    color: var(--text3);
    position: absolute;
    right: 32px;
    top: 50%;
    transform: translateY(-50%);
    opacity: 0;
    transition: opacity 0.15s;
  }
  .item-block:hover .speed-info { opacity: 1; }
  /* Scrollbar */
  ::-webkit-scrollbar { width: 6px; }
  ::-webkit-scrollbar-track { background: transparent; }
  ::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }
  /* Pagination */
  .pagination {
    display: flex;
    justify-content: center;
    align-items: center;
    gap: 8px;
    margin-top: 20px;
    padding: 12px 0;
  }
  .pagination button {
    padding: 6px 12px;
    border-radius: 6px;
    border: 1px solid var(--border);
    background: var(--surface2);
    color: var(--text);
    cursor: pointer;
    font-size: 13px;
    transition: all 0.15s;
  }
  .pagination button:hover {
    background: var(--surface);
    border-color: var(--accent);
  }
  .pagination button.active {
    background: var(--accent);
    color: white;
    border-color: var(--accent);
  }
  /* Mobile */
  @media (max-width: 680px) {
    aside { display: none; }
    .content-wrap { padding: 16px; }
  }
</style>
</head>
<body>
<!-- Header -->
<header>
  <div class="logo">Révision ASD <span>/ Titre Pro</span></div>
  <div class="status-bar">
    <div class="status-dot" id="status-dot"></div>
    <span id="status-text">Cliquez sur un bloc pour lire</span>
  </div>
  <div class="controls">
    <div class="lang-toggle">
      <button id="btn-fr" class="active" onclick="setLang('fr')">🇫🇷 FR</button>
      <button id="btn-en" onclick="setLang('en')">🇬🇧 EN</button>
    </div>
    <select id="voice-select" title="Choisir la voix"></select>
    <button class="stop" onclick="stopAll()">⏹ Stop</button>
  </div>
</header>

<div class="main">
  <!-- Sidebar -->
  <aside>
    <div class="aside-title">Sections</div>
    <div id="nav-list"></div>
  </aside>

  <!-- Content -->
  <div class="content-wrap">
    <div id="section-header" class="section-header"></div>
    <div class="items-list" id="items-list"></div>
    <div class="pagination" id="pagination"></div>
  </div>
</div>

<script>
// ─────────────────────────────────────────────────────────
// CONSTANTES
// ─────────────────────────────────────────────────────────
const ITEMS_PER_PAGE = __ITEMS_PER_PAGE__;
const COURSE = __COURSE_JSON__;

// IDs des sections projet (affichage distinct dans la sidebar)
const PROJECT_SECTION_IDS = ['topgainers_qcm', 'topgainers_jury'];

let currentSectionId = null;
let currentPage = 1;

// ─────────────────────────────────────────────────────────
// ÉTAT
// ─────────────────────────────────────────────────────────
let currentLang = 'fr';
let voices = [];
let frVoices = [];
let enVoices = [];
let currentBlock = null;

// ─────────────────────────────────────────────────────────
// VITESSES PAR TYPE
// ─────────────────────────────────────────────────────────
const RATES = {
  audio_command: 0.75, audio_code: 0.78, audio_file: 0.72,
  audio_code_explain: 0.88, security: 0.88, jury: 0.88, qa: 0.88,
  audio_terminal_tip: 0.90, method: 0.92, technical: 0.90,
  concept: 0.95, intro: 0.98, audio_analogy: 0.95, conclusion: 0.92,
  // Nouveaux types
  qcm: 0.90, jury_open: 0.88,
  _default: 0.95,
};

// ─────────────────────────────────────────────────────────
// WEB SPEECH API
// ─────────────────────────────────────────────────────────
function loadVoices() {
  const all = speechSynthesis.getVoices();
  if (!all.length) { setTimeout(loadVoices, 100); return; }
  voices = all;
  frVoices = all.filter(v => v.lang.startsWith('fr'));
  enVoices = all.filter(v => v.lang.startsWith('en'));
  const sel = document.getElementById('voice-select');
  sel.innerHTML = '';
  const pool = currentLang === 'fr' ? (frVoices.length ? frVoices : all) : (enVoices.length ? enVoices : all);
  pool.forEach((v, i) => {
    const opt = document.createElement('option');
    opt.value = i;
    opt.textContent = v.name.replace('Microsoft ', '').replace(' Desktop', '').substring(0, 28);
    sel.appendChild(opt);
  });
}

function getSelectedVoice() {
  const sel = document.getElementById('voice-select');
  const idx = parseInt(sel.value) || 0;
  const pool = currentLang === 'fr' ? (frVoices.length ? frVoices : voices) : (enVoices.length ? enVoices : voices);
  return pool[idx] || null;
}

function setLang(lang) {
  currentLang = lang;
  document.getElementById('btn-fr').classList.toggle('active', lang === 'fr');
  document.getElementById('btn-en').classList.toggle('active', lang === 'en');
  loadVoices();
  setStatus('Langue changée — cliquez pour relire');
  if (currentSectionId) renderSection(currentSectionId, currentPage);
}

function speak(item, blockEl) {
  speechSynthesis.cancel();
  if (currentBlock) currentBlock.classList.remove('playing', 'highlighted');
  currentBlock = blockEl;
  currentBlock.classList.add('playing');
  document.getElementById('status-dot').classList.add('playing');
  const text = buildSpeechText(item);
  const rate = getRate(item.type);
  setStatus('Lecture... (×' + rate.toFixed(2) + ')');
  const utt = new SpeechSynthesisUtterance(text);
  utt.lang = currentLang === 'fr' ? 'fr-FR' : 'en-US';
  utt.rate = rate;
  const voice = getSelectedVoice();
  if (voice) utt.voice = voice;
  utt.onend = () => {
    if (currentBlock) { currentBlock.classList.remove('playing'); currentBlock.classList.add('highlighted'); }
    document.getElementById('status-dot').classList.remove('playing');
    setStatus('Lecture terminée. Cliquez pour relire.');
  };
  utt.onerror = () => {
    if (currentBlock) currentBlock.classList.remove('playing');
    document.getElementById('status-dot').classList.remove('playing');
    setStatus('Erreur de lecture. Réessayez.');
  };
  speechSynthesis.speak(utt);
}

function stopAll() {
  speechSynthesis.cancel();
  if (currentBlock) currentBlock.classList.remove('playing', 'highlighted');
  document.getElementById('status-dot').classList.remove('playing');
  setStatus('Arrêté');
}

function setStatus(msg) { document.getElementById('status-text').textContent = msg; }

// ─────────────────────────────────────────────────────────
// PAGINATION
// ─────────────────────────────────────────────────────────
function paginateContent(content, page) {
  const total_items = content.length;
  const total_pages = Math.ceil(total_items / ITEMS_PER_PAGE);
  const start_idx = (page - 1) * ITEMS_PER_PAGE;
  return {
    data: content.slice(start_idx, start_idx + ITEMS_PER_PAGE),
    page, total_pages, total_items
  };
}

function renderPagination(totalPages, currentPage) {
  const div = document.getElementById('pagination');
  div.innerHTML = '';
  if (currentPage > 1) {
    const b = document.createElement('button');
    b.textContent = '←';
    b.addEventListener('click', () => renderSection(currentSectionId, currentPage - 1));
    div.appendChild(b);
  }
  for (let i = 1; i <= totalPages; i++) {
    const b = document.createElement('button');
    b.textContent = i;
    if (i === currentPage) b.classList.add('active');
    b.addEventListener('click', () => renderSection(currentSectionId, i));
    div.appendChild(b);
  }
  if (currentPage < totalPages) {
    const b = document.createElement('button');
    b.textContent = '→';
    b.addEventListener('click', () => renderSection(currentSectionId, currentPage + 1));
    div.appendChild(b);
  }
}

// ─────────────────────────────────────────────────────────
// RENDU DES BLOCS
// ─────────────────────────────────────────────────────────
const TYPE_LABELS = {
  intro: ['intro', 'badge-intro'], concept: ['concept', 'badge-concept'],
  method: ['méthode', 'badge-method'], technical: ['technique', 'badge-technical'],
  security: ['sécurité', 'badge-security'], jury: ['⚠ jury', 'badge-jury'],
  audio_command: ['commande', 'badge-command'], audio_code: ['code', 'badge-code'],
  audio_code_explain: ['explication', 'badge-explain'], audio_terminal_tip: ['astuce', 'badge-tip'],
  audio_analogy: ['analogie', 'badge-analogy'], audio_file: ['config', 'badge-file'],
  qa: ['Q&A jury', 'badge-qa'], conclusion: ['conclusion', 'badge-conclusion'],
  // Nouveaux types
  qcm: ['QCM', 'badge-qcm'],
  jury_open: ['🎤 jury ouvert', 'badge-jury-open'],
};

function renderItemBlock(item) {
  const div = document.createElement('div');
  div.className = 'item-block';
  const [label, badgeClass] = TYPE_LABELS[item.type] || [item.type, 'badge-explain'];

  let bodyHTML = '';

  if (item.type === 'qcm') {
    // ── Rendu spécial QCM ──────────────────────────────────────────────────
    const sectionTag = item.section
      ? `<span class="qcm-section-tag">${escapeHtml(item.section)}</span><br>`
      : '';
    const optsHTML = (item.options || []).map((opt, j) => {
      const isCorrect = j === item.correct;
      const letter = String.fromCharCode(65 + j);
      return `<div class="qcm-option${isCorrect ? ' correct-opt' : ''}">
        <span class="qcm-option-letter">${letter}</span>
        <span>${escapeHtml(opt)}${isCorrect ? ' ✓' : ''}</span>
      </div>`;
    }).join('');
    const expHTML = item.explanation
      ? `<div class="qcm-explanation">${escapeHtml(item.explanation)}</div>`
      : '';
    bodyHTML = `${sectionTag}<div class="qcm-question">${escapeHtml(item.question || '')}</div><div class="qcm-options">${optsHTML}</div>${expHTML}`;

  } else if (item.type === 'jury_open') {
    // ── Rendu spécial question de jury ouverte ─────────────────────────────
    bodyHTML = `
      <div class="jury-open-question">${escapeHtml(item.title || '')}</div>
      <div class="jury-open-answer">${escapeHtml(item.model_answer || '')}</div>
    `;

  } else if (item.type === 'qa') {
    bodyHTML = `<div class="qa-question"><span class="qa-q-badge">Q</span>${escapeHtml(item.question || '')}</div><div class="qa-answer">${escapeHtml(item.answer || '')}</div>`;

  } else if (['audio_command', 'audio_code', 'audio_file'].includes(item.type)) {
    bodyHTML = `<pre class="item-code">${escapeHtml(item.text || '')}</pre>`;

  } else {
    const titleHTML = item.title ? `<div class="item-title">${escapeHtml(item.title)}</div>` : '';
    bodyHTML = `${titleHTML}<div class="item-text">${escapeHtml(item.text || '')}</div>`;
  }

  div.innerHTML = `
    <div class="type-badge ${badgeClass}">${label}</div>
    ${bodyHTML}
    <span class="play-icon">▶</span>
  `;
  div.addEventListener('click', (e) => { e.stopPropagation(); speak(item, div); });
  return div;
}

function renderSection(sectionId, page = 1) {
  speechSynthesis.cancel();
  if (currentBlock) currentBlock.classList.remove('playing', 'highlighted');
  document.getElementById('status-dot').classList.remove('playing');

  const section = COURSE.find(s => s.id === sectionId);
  if (!section) return;
  currentSectionId = sectionId;
  currentPage = page;

  document.querySelectorAll('.nav-item').forEach(b => b.classList.remove('active'));
  const navBtn = document.querySelector('.nav-item[data-id="' + sectionId + '"]');
  if (navBtn) navBtn.classList.add('active');

  document.getElementById('section-header').innerHTML = `
    <div class="section-title">${section.title}</div>
    <div class="section-hint">${section.content.length} blocs — page ${page}/${Math.ceil(section.content.length / ITEMS_PER_PAGE)}</div>
  `;

  const paginated = paginateContent(section.content, page);
  renderPagination(paginated.total_pages, page);

  const list = document.getElementById('items-list');
  list.innerHTML = '';
  paginated.data.forEach(item => list.appendChild(renderItemBlock(item)));

  setStatus(paginated.data.length + ' blocs — cliquez pour lire');
}

// ─────────────────────────────────────────────────────────
// NAVIGATION
// ─────────────────────────────────────────────────────────
function buildNav() {
  const nav = document.getElementById('nav-list');
  let projectSeparatorAdded = false;

  COURSE.forEach(section => {
    const isProject = PROJECT_SECTION_IDS.includes(section.id);

    // Ajouter le séparateur avant les sections projet
    if (isProject && !projectSeparatorAdded) {
      const sep = document.createElement('div');
      sep.className = 'aside-separator';
      sep.textContent = '★ Projet — Soutenance';
      nav.appendChild(sep);
      projectSeparatorAdded = true;
    }

    const btn = document.createElement('button');
    btn.className = 'nav-item' + (isProject ? ' project-item' : '');
    btn.dataset.id = section.id;
    btn.innerHTML = `<span class="nav-label">${section.title}</span><span class="progress-dot"></span>`;
    btn.addEventListener('click', () => renderSection(section.id));
    nav.appendChild(btn);
  });
}

// ─────────────────────────────────────────────────────────
// INITIALISATION
// ─────────────────────────────────────────────────────────
buildNav();
renderSection('intro', 1);

if (typeof speechSynthesis !== 'undefined') {
  if (speechSynthesis.onvoiceschanged !== undefined) speechSynthesis.onvoiceschanged = loadVoices;
  setTimeout(loadVoices, 300);
} else {
  setStatus('⚠ Web Speech API non supportée');
}

// ─────────────────────────────────────────────────────────
// UTILITAIRES
// ─────────────────────────────────────────────────────────
function escapeHtml(s) {
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

function getRate(type) { return RATES[type] || RATES._default; }

function buildSpeechText(item) {
  const t = item.type;
  const text = item.text || '';
  const title = item.title || '';
  const lang = currentLang;

  // ── Nouveaux types ───────────────────────────────────────────────────────
  if (t === 'qcm') {
    const opts = (item.options || []).map((o, i) => `Option ${String.fromCharCode(65+i)}: ${o}`).join('. ');
    const correctLetter = String.fromCharCode(65 + (item.correct || 0));
    return lang === 'fr'
      ? `Question. ${item.question || ''}. ${opts}. Bonne réponse : option ${correctLetter}. Explication : ${item.explanation || ''}.`
      : `Question. ${item.question || ''}. ${opts}. Correct answer: option ${correctLetter}. Explanation: ${item.explanation || ''}.`;
  }

  if (t === 'jury_open') {
    return lang === 'fr'
      ? `Question de jury. ${title}. Réponse modèle. ${item.model_answer || ''}.`
      : `Jury question. ${title}. Model answer. ${item.model_answer || ''}.`;
  }
  // ── Types existants ──────────────────────────────────────────────────────

  const prefixes = {
    fr: {
      audio_command: 'Commande terminal. ', audio_code: 'Code. ',
      audio_file: 'Fichier de configuration. ', audio_code_explain: '',
      audio_terminal_tip: 'Astuce importante. ', audio_analogy: 'Pour mieux comprendre. ',
      security: 'Point sécurité. ', jury: 'Question piège du jury. ', qa: '',
      conclusion: 'Pour conclure. ', method: 'Méthode. ', concept: 'Concept clé. ',
      technical: '', intro: '',
    },
    en: {
      audio_command: 'Terminal command. ', audio_code: 'Code. ',
      audio_file: 'Configuration file. ', audio_code_explain: '',
      audio_terminal_tip: 'Important tip. ', audio_analogy: 'To understand better. ',
      security: 'Security point. ', jury: 'Tricky jury question. ', qa: '',
      conclusion: 'To conclude. ', method: 'Method. ', concept: 'Key concept. ',
      technical: '', intro: '',
    },
  };

  const prefix = (prefixes[lang] || prefixes.fr)[t] || '';
  const titlePart = title ? title + '. ' : '';

  if (t === 'qa') {
    const q = item.question || ''; const a = item.answer || '';
    return lang === 'fr'
      ? `Question du jury. ${q}. Réponse. ${a}.`
      : `Jury question. ${q}. Answer. ${a}.`;
  }

  return prefix + titlePart + text;
}
</script>
</body>
</html>"""

# ====================== ROUTES ======================
@api_router.get("/")
async def api_root():
    return JSONResponse(content={"message": "API ASD Audio Learning v2 - OK"})

@api_router.get("/course")
async def get_course():
    return JSONResponse(content=COURSE_CONTENT)

@api_router.get("/course/{section_id}")
async def get_section(section_id: str, page: int = 1):
    section = next((s for s in COURSE_CONTENT if s["id"] == section_id), None)
    if not section:
        raise HTTPException(status_code=404, detail="Section non trouvée")

    paginated = {
        "data": section["content"][(page-1)*ITEMS_PER_PAGE : page*ITEMS_PER_PAGE],
        "page": page,
        "total_pages": (len(section["content"]) + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE,
        "total_items": len(section["content"])
    }
    return JSONResponse(content=paginated)

@api_router.get("/audio/{section_id}")
async def get_audio(section_id: str):
    section = next((s for s in COURSE_CONTENT if s["id"] == section_id), None)
    if not section:
        raise HTTPException(status_code=404, detail="Section non trouvée")

    engine = _init_tts_engine()
    full_audio = b""
    for item in section["content"]:
        try:
            audio_chunk = generate_audio_for_item(engine, item)
            full_audio += audio_chunk
        except Exception as e:
            logging.warning(f"Erreur TTS pour item {item.get('type', '?')}: {e}")
            continue

    return StreamingResponse(
        iter([full_audio]),
        media_type="audio/wav",
        headers={"Content-Disposition": f"attachment; filename={section_id}.wav"}
    )

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
def _build_frontend() -> str:
    """Injecte le contenu du cours et la pagination dans le HTML frontend."""
    course_json = _json.dumps(COURSE_CONTENT, ensure_ascii=False)
    frontend_html = FRONTEND_HTML.replace('__COURSE_JSON__', course_json)
    frontend_html = frontend_html.replace('__ITEMS_PER_PAGE__', str(ITEMS_PER_PAGE))
    return frontend_html

STATIC_FILES_DIR = STATIC_DIR / "static"
if STATIC_DIR.exists() and (STATIC_DIR / "index.html").exists():
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
    async def serve_integrated_frontend():
        return HTMLResponse(content=_build_frontend())

    @app.get("/{full_path:path}")
    async def catch_all(full_path: str):
        if full_path.startswith("api"):
            return JSONResponse({"error": "Not found"}, status_code=404)
        return HTMLResponse(content=_build_frontend())

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
