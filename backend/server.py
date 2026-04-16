from fastapi import FastAPI, APIRouter, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse
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
    audio_settings: Optional[dict] = None

class UserProgress(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    section_id: str
    completed: bool = False
    last_position: int = 0
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ====================== FONCTIONS TTS OPTIMISÉES ======================

def _init_tts_engine() -> pyttsx3.Engine:
    """Initialise le moteur TTS avec une voix française si disponible."""
    engine = pyttsx3.init()
    voices = engine.getProperty('voices')
    try:
        french_voice = next(
            v for v in voices
            if 'french' in v.name.lower() or 'fr' in (v.languages or [])
        )
        engine.setProperty('voice', french_voice.id)
    except StopIteration:
        pass  # Garde la voix par défaut
    engine.setProperty('rate', 150)
    return engine


def _render_tts(engine: pyttsx3.Engine, text: str, rate: int = 150) -> bytes:
    """
    Synthétise `text` en audio et retourne les bytes WAV/MP3.
    pyttsx3.save_to_file() exige un chemin fichier, pas un BytesIO.
    """
    engine.setProperty('rate', rate)
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp_path = tmp.name

    engine.save_to_file(text, tmp_path)
    engine.runAndWait()

    with open(tmp_path, "rb") as f:
        data = f.read()
    os.unlink(tmp_path)
    return data


# ---------- Décomposeurs techniques ----------

# Dictionnaire de sigles et abréviations prononcés lettre par lettre
SPELL_OUT = {
    "apt": "A-P-T",
    "ssh": "S-S-H",
    "tls": "T-L-S",
    "ssl": "S-S-L",
    "ci": "C-I",
    "cd": "C-D",
    "cpu": "C-P-U",
    "ram": "R-A-M",
    "vpc": "V-P-C",
    "aws": "A-W-S",
    "ec2": "E-C-2",
    "s3": "S-3",
    "nfs": "N-F-S",
    "efs": "E-F-S",
    "ebs": "E-B-S",
    "hcl": "H-C-L",
    "dns": "D-N-S",
    "snmp": "S-N-M-P",
    "iam": "I-A-M",
    "rbac": "R-B-A-C",
    "cncf": "C-N-C-F",
    "yaml": "YAML",
    "json": "JSON",
    "ip": "I-P",
    "os": "O-S",
    "vm": "V-M",
    "url": "U-R-L",
    "api": "A-P-I",
    "sli": "S-L-I",
    "slo": "S-L-O",
    "sla": "S-L-A",
    "tty": "T-T-Y",
    "kvm": "K-V-M",
}

# Symboles techniques à vocaliser (utilisé UNIQUEMENT dans les blocs code/commande)
TECH_SYMBOLS = {
    "/": " slash ",
    "-": " tiret ",
    "_": " underscore ",
    ":": " deux-points ",
    "=": " égal ",
    ".": " point ",
    "@": " arobase ",
    "#": " dièse ",
    "*": " étoile ",
    "&": " et ",
    "|": " pipe ",
    ">": " supérieur ",
    "<": " inférieur ",
    "~": " tilde ",
    "`": " backtick ",
    "$": " dollar ",
    "%": " pourcent ",
    "+": " plus ",
    "\\": " antislash ",
    "!": " point d'exclamation ",
    "{": " accolade ouvrante ",
    "}": " accolade fermante ",
    "[": " crochet ouvrant ",
    "]": " crochet fermant ",
    "(": " parenthèse ouvrante ",
    ")": " parenthèse fermante ",
    '"': " guillemet ",
    "'": " apostrophe ",
}

# Tokens spéciaux à remplacer par leur signification
KNOWN_PATTERNS = [
    # Versions (ex: python:3.9-slim → python version 3.9 slim)
    (r'(\w+):(\d+\.\d+(?:\.\d+)?)-?(\w+)?', lambda m: (
        f"{m.group(1)} version {m.group(2)}"
        + (f" {m.group(3)}" if m.group(3) else "")
    )),
    # CIDR (ex: 10.0.0.0/16 → 10 point 0 point 0 point 0 slash 16)
    (r'(\d+\.\d+\.\d+\.\d+)/(\d+)', lambda m: (
        " point ".join(m.group(1).split("."))
        + f" sur {m.group(2)}"
    )),
    # Options courtes (ex: -d, -f, -it)
    (r'\s-([a-zA-Z]+)', lambda m: f" option {m.group(1)} "),
    # Options longues (ex: --replicas=3)
    (r'--(\w+)(?:=(\S+))?', lambda m: (
        f" option {m.group(1)}"
        + (f" égal {m.group(2)}" if m.group(2) else "")
    )),
    # Variable GitHub Actions (ex: ${{ github.sha }})
    (r'\$\{\{\s*(\S+)\s*\}\}', lambda m: f" variable {m.group(1)} "),
]


def _apply_spell_out(token: str) -> str:
    """Épelle les sigles connus (case-insensitive)."""
    lower = token.lower().rstrip(".,;:")
    if lower in SPELL_OUT:
        suffix = token[len(lower):]
        return SPELL_OUT[lower] + suffix
    return token


def _vocalize_tech_token(token: str) -> str:
    """Vocalise un token technique : sigle, version, option, chemin…"""
    token = _apply_spell_out(token)
    result = ""
    for ch in token:
        result += TECH_SYMBOLS.get(ch, ch)
    return result


def format_command_for_tts(command: str) -> str:
    """
    Transforme une commande shell en texte lisible par TTS.
    Ex: 'docker build -t myapp:latest .' →
        'Commande terminal. docker build, option t, myapp version latest, point.'
    """
    # Appliquer les patterns complexes en premier
    processed = command.strip()
    for pattern, replacement in KNOWN_PATTERNS:
        processed = re.sub(pattern, replacement, processed)

    # Vocaliser token par token
    tokens = processed.split()
    readable_tokens = [_apply_spell_out(t) for t in tokens]
    readable = ", ".join(readable_tokens)

    return (
        f"Commande terminal. "
        f"{readable}. "
        f"Fin de commande."
    )


def format_code_for_tts(code: str) -> str:
    """
    Transforme un extrait de code en texte lisible.
    Ex: 'FROM python:3.9-slim' → 'Extrait de code. FROM python version 3.9 slim.'
    """
    lines = [l.strip() for l in code.strip().splitlines() if l.strip()]
    readable_lines = []
    for line in lines:
        processed = line
        for pattern, replacement in KNOWN_PATTERNS:
            processed = re.sub(pattern, replacement, processed)
        # Vocaliser les symboles restants
        vocalised = ""
        for ch in processed:
            vocalised += TECH_SYMBOLS.get(ch, ch)
        # Nettoyer les espaces multiples
        vocalised = re.sub(r'\s{2,}', ' ', vocalised).strip()
        readable_lines.append(vocalised)

    body = ". Ligne suivante. ".join(readable_lines)
    return (
        f"Extrait de code. "
        f"{body}. "
        f"Fin de l'extrait."
    )


def format_yaml_for_tts(yaml_text: str) -> str:
    """
    Lit un fichier YAML/config ligne par ligne de façon structurée.
    Ex: 'services:\\n  web:\\n    image: nginx'
    → 'Fichier de configuration. Clé services. Sous-clé web. image nginx. Fin du fichier.'
    """
    lines = yaml_text.strip().splitlines()
    readable_parts = ["Fichier de configuration."]

    prev_indent = 0
    for line in lines:
        if not line.strip() or line.strip().startswith("#"):
            continue

        indent = len(line) - len(line.lstrip())
        stripped = line.strip()

        # Détecter clé: valeur ou clé seule
        if ":" in stripped:
            parts = stripped.split(":", 1)
            key = parts[0].strip()
            value = parts[1].strip() if len(parts) > 1 else ""

            depth = indent // 2
            if depth == 0:
                prefix = "Clé principale"
            elif depth == 1:
                prefix = "Sous-clé"
            else:
                prefix = "Paramètre"

            key_readable = _apply_spell_out(key)
            if value:
                value_readable = _apply_spell_out(value.strip('"\''))
                readable_parts.append(f"{prefix} {key_readable}, valeur {value_readable}.")
            else:
                readable_parts.append(f"{prefix} {key_readable}.")
        elif stripped.startswith("-"):
            item = stripped.lstrip("- ").strip()
            item_readable = _apply_spell_out(item)
            readable_parts.append(f"Élément de liste: {item_readable}.")
        else:
            readable_parts.append(_apply_spell_out(stripped) + ".")

        prev_indent = indent

    readable_parts.append("Fin du fichier de configuration.")
    return " ".join(readable_parts)


def format_promql_for_tts(query: str) -> str:
    """
    Lit une requête PromQL de façon compréhensible.
    Ex: 'rate(api_calls_total{status="error"}[5m])'
    → 'Requête PromQL. taux de api_calls_total, filtre status égal error, sur 5 minutes.'
    """
    query = query.strip()
    readable = query

    # Fonctions PromQL
    readable = re.sub(r'\brate\(', 'taux de variation de (', readable)
    readable = re.sub(r'\bavg\(', 'moyenne de (', readable)
    readable = re.sub(r'\bsum\(', 'somme de (', readable)
    readable = re.sub(r'\bcount\(', 'comptage de (', readable)

    # Filtres {label="value"}
    readable = re.sub(
        r'\{([^}]+)\}',
        lambda m: f", filtre {m.group(1).replace('=', ' égal ').replace('\"', '')}",
        readable
    )

    # Fenêtre temporelle [5m]
    readable = re.sub(r'\[(\d+)m\]', r' sur \1 minutes', readable)
    readable = re.sub(r'\[(\d+)s\]', r' sur \1 secondes', readable)

    return f"Requête PromQL. {readable}. Fin de la requête."


def format_cidr_for_tts(cidr: str) -> str:
    """10.0.0.0/16 → '10 point 0 point 0 point 0 sur 16'"""
    m = re.match(r'(\d+)\.(\d+)\.(\d+)\.(\d+)/(\d+)', cidr.strip())
    if m:
        ip = f"{m.group(1)} point {m.group(2)} point {m.group(3)} point {m.group(4)}"
        return f"Réseau {ip} sur {m.group(5)}."
    return cidr


def _is_command(text: str) -> bool:
    """Heuristique : commence par un binaire connu ou contient des flags."""
    command_starters = [
        "docker", "kubectl", "terraform", "ansible", "ansible-playbook",
        "sudo", "apt", "pip", "npm", "git", "ssh", "cp", "mv", "rm",
        "df", "free", "ss", "ping", "journalctl", "systemctl",
        "python", "bash", "cat", "echo", "curl", "wget",
        "#!/", "docker-compose",
    ]
    t = text.strip().lower()
    return any(t.startswith(s) for s in command_starters)


def _is_cidr(text: str) -> bool:
    return bool(re.match(r'^\d+\.\d+\.\d+\.\d+/\d+$', text.strip()))


def _is_promql(text: str) -> bool:
    return bool(re.search(r'(rate|avg|sum|count)\(|_total|_seconds|\{[^}]+\}|\[(\d+)[ms]\]', text))


def _is_yaml_block(text: str) -> bool:
    """Détecte un bloc YAML multi-lignes."""
    return "\n" in text and (":" in text or "- " in text)


def _is_code_line(text: str) -> bool:
    """Ligne de code unique (pas une phrase)."""
    # Contient des symboles typiques du code sans espaces de prose
    return bool(re.search(r'[A-Z_]{2,}\s|::|->|&&|\|\|', text)) or text.startswith("FROM ")


# ====================== GÉNÉRATION AUDIO PRINCIPALE ======================

def generate_audio_for_item(engine: pyttsx3.Engine, item: dict) -> bytes:
    """
    Génère l'audio pour un item de contenu selon son type.
    Applique la vocalisation technique appropriée.
    """
    item_type = item.get("type", "")
    text = item.get("text", "").strip()

    # ---- Commandes terminal ----
    if item_type == "audio_command" or (item_type in ("technical",) and _is_command(text)):
        spoken = format_command_for_tts(text)
        return _render_tts(engine, spoken, rate=130)  # Plus lent pour les commandes

    # ---- Extraits de code ----
    elif item_type == "audio_code":
        if _is_cidr(text):
            spoken = format_cidr_for_tts(text)
        elif _is_promql(text):
            spoken = format_promql_for_tts(text)
        elif _is_yaml_block(text):
            spoken = format_yaml_for_tts(text)
        elif _is_command(text):
            spoken = format_command_for_tts(text)
        else:
            spoken = format_code_for_tts(text)
        return _render_tts(engine, spoken, rate=130)

    # ---- Fichiers de config (YAML, Dockerfile…) ----
    elif item_type == "audio_file":
        if _is_yaml_block(text):
            spoken = format_yaml_for_tts(text)
        elif _is_command(text):
            spoken = format_command_for_tts(text)
        else:
            spoken = format_code_for_tts(text)
        return _render_tts(engine, spoken, rate=125)  # Encore plus lent pour les fichiers

    # ---- Questions/Réponses jury ----
    elif item_type == "qa":
        question = item.get("question", "")
        answer = item.get("answer", "")
        spoken = (
            f"Question du jury. {question}. "
            f"[pause] "
            f"Réponse. {answer}."
        )
        return _render_tts(engine, spoken, rate=145)

    # ---- Explications de code (texte prose sur du code) ----
    elif item_type == "audio_code_explain":
        return _render_tts(engine, text, rate=150)

    # ---- Astuce terminal ----
    elif item_type == "audio_terminal_tip":
        spoken = f"Astuce importante. {text}"
        return _render_tts(engine, spoken, rate=148)

    # ---- Analogie ----
    elif item_type == "audio_analogy":
        spoken = f"Pour mieux comprendre. {text}"
        return _render_tts(engine, spoken, rate=150)

    # ---- Question jury (bloc dédié) ----
    elif item_type == "jury":
        title = item.get("title", "")
        spoken = f"Attention, question piège du jury. {title}. {text}"
        return _render_tts(engine, spoken, rate=148)

    # ---- Sécurité ----
    elif item_type == "security":
        title = item.get("title", "")
        prefix = f"Point sécurité. {title}. " if title else "Point sécurité. "
        spoken = prefix + text
        return _render_tts(engine, spoken, rate=148)

    # ---- Méthode ----
    elif item_type == "method":
        title = item.get("title", "")
        prefix = f"Méthode. {title}. " if title else ""
        spoken = prefix + text
        return _render_tts(engine, spoken, rate=150)

    # ---- Concept ----
    elif item_type == "concept":
        title = item.get("title", "")
        prefix = f"Concept clé. {title}. " if title else ""
        spoken = prefix + text
        return _render_tts(engine, spoken, rate=150)

    # ---- Conclusion ----
    elif item_type == "conclusion":
        title = item.get("title", "")
        spoken = f"Pour conclure. {title}. {text}"
        return _render_tts(engine, spoken, rate=148)

    # ---- Texte générique (intro, technical, etc.) ----
    else:
        title = item.get("title", "")
        prefix = f"{title}. " if title else ""
        spoken = prefix + text
        return _render_tts(engine, spoken, rate=150)


# ====================== CONTENU DE COURS ======================
COURSE_CONTENT = [
    # ---- Introduction ----
    {
        "id": "intro",
        "title": "Introduction & Méthode IA",
        "icon": "Brain",
        "content": [
            {
                "type": "intro",
                "text": "Bienvenue dans cette fiche de révision pour le Titre Professionnel Administrateur Système DevOps. Ce document couvre les onze compétences professionnelles du REAC. Je vais t'expliquer chaque notion comme si on était en cours ensemble."
            },
            {
                "type": "concept",
                "title": "La philosophie de l'IA en DevOps",
                "text": "Retiens cette citation importante : L'IA n'est pas un copilote magique. C'est un junior qui code vite mais qui se trompe souvent. Ton rôle d'Admin Sys DevOps, c'est d'être le senior qui relit, comprend, teste et valide. L'IA est un outil, pas une solution magique. L'humain est le garant de la qualité et de la compréhension."
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
                "title": "Question piège du jury",
                "text": "Le jury pourrait te demander : Vous avez utilisé l'IA, donc vous ne comprenez pas votre code ? Ta réponse : Non, j'ai utilisé l'IA comme outil d'accélération. Pour chaque bloc généré, j'ai appliqué ma méthode : lire, comprendre, adapter, tester. Je peux expliquer chaque ligne de mon Dockerfile, de mon fichier Terraform, de mon pipeline CI/CD."
            }
        ]
    },
    # ---- CP1 : Scripts Serveurs ----
    {
        "id": "cp1",
        "title": "CP1 : Scripts Serveurs",
        "icon": "Terminal",
        "content": [
            {
                "type": "intro",
                "text": "Compétence 1 : Automatiser la création de serveurs à l'aide de scripts. Cette compétence couvre la virtualisation et les différents types de scripts."
            },
            {
                "type": "concept",
                "title": "Les types de virtualisation",
                "text": "Il existe trois types de virtualisation à connaître. Premier type : l'Hyperviseur de Type 1, comme VMware ESXi, KVM ou Hyper-V. Il s'installe directement sur le matériel. C'est utilisé en production."
            },
            {
                "type": "technical",
                "text": "Deuxième type : l'Hyperviseur de Type 2, comme VirtualBox ou VMware Workstation. Il s'installe sur un système d'exploitation existant. C'est utilisé pour le développement et les tests en local."
            },
            {
                "type": "technical",
                "text": "Troisième type : les Conteneurs, comme Docker. C'est une isolation légère qui partage le même noyau que le système hôte. Plus léger qu'une machine virtuelle complète."
            },
            {
                "type": "concept",
                "title": "Script Bash : structure de base",
                "text": "Un script Bash est une liste d'instructions shell exécutées dans l'ordre. Il sert à automatiser des actions manuelles dans un terminal. La première ligne est le shebang, qui indique l'interpréteur à utiliser."
            },
            {
                "type": "audio_command",
                "text": "#!/bin/bash"
            },
            {
                "type": "audio_terminal_tip",
                "text": "Astuce : Ajoute souvent set -e pour arrêter automatiquement le script si une commande échoue."
            },
            {
                "type": "technical",
                "title": "Exemple de script Bash d'installation",
                "text": "Un script typique d'installation serveur va d'abord mettre à jour la liste des paquets, puis installer les services nécessaires comme Nginx, le pare-feu UFW et fail2ban. Ensuite il active et démarre ces services. Enfin il vérifie que tout fonctionne correctement."
            },
            {
                "type": "audio_command",
                "text": "sudo apt update && sudo apt upgrade -y"
            },
            {
                "type": "audio_command",
                "text": "sudo apt install -y nginx ufw fail2ban"
            },
            {
                "type": "audio_command",
                "text": "sudo systemctl enable --now nginx ufw fail2ban"
            },
            {
                "type": "concept",
                "title": "Script Python pour l'automatisation",
                "text": "Python peut aussi automatiser l'administration système. On utilise le module subprocess pour exécuter des commandes système. L'avantage de Python : une meilleure gestion des erreurs, des conditions, et un code plus lisible pour des automatisations complexes."
            },
            {
                "type": "audio_code",
                "text": "import subprocess\nsubprocess.run([\"sudo\", \"apt\", \"update\"], check=True)"
            },
            {
                "type": "technical",
                "title": "Script PowerShell pour Windows",
                "text": "Sur Windows Server, on utilise PowerShell. On peut installer des fonctionnalités serveur, créer des utilisateurs locaux, gérer les services. C'est l'équivalent de Bash pour l'écosystème Microsoft."
            }
        ]
    },
    # ---- CP2 : Terraform & Ansible ----
    {
        "id": "cp2",
        "title": "CP2 : Terraform & Ansible",
        "icon": "Server",
        "content": [
            {
                "type": "intro",
                "text": "Compétence 2 : Automatiser le déploiement d'une infrastructure avec Terraform et Ansible. C'est fondamental pour ton titre pro."
            },
            {
                "type": "concept",
                "title": "Terraform vs Ansible : l'analogie imparable",
                "text": "Voici comment différencier ces deux outils. Terraform, c'est l'architecte qui construit les murs et pose les fondations. Il crée ton infrastructure : les instances EC2, les VPC, les Security Groups, les buckets S3."
            },
            {
                "type": "technical",
                "text": "Ansible, c'est le décorateur qui arrive après et installe les meubles, configure les prises. Il installe Nginx, crée les utilisateurs, copie les fichiers de configuration. L'ordre est important : on fait toujours Terraform d'abord pour créer l'infrastructure, puis Ansible ensuite pour la configurer."
            },
            {
                "type": "concept",
                "title": "Caractéristiques de Terraform",
                "text": "Terraform utilise le langage HCL, avec des fichiers point TF. Il est stateful, ce qui signifie qu'il garde un fichier d'état qui mémorise l'état de ton infrastructure."
            },
            {
                "type": "audio_terminal_tip",
                "text": "Règle d'or : ne jamais committer le fichier terraform.tfstate dans Git ! En équipe, on le stocke sur S3 avec un verrou DynamoDB."
            },
            {
                "type": "method",
                "title": "Commandes Terraform essentielles",
                "text": "Les commandes clés à retenir : init pour initialiser et télécharger les providers. validate pour vérifier la syntaxe. plan pour prévisualiser les changements sans rien modifier. apply pour créer l'infrastructure. destroy pour tout supprimer. output pour afficher les valeurs de sortie comme l'IP publique."
            },
            {
                "type": "audio_command",
                "text": "terraform init"
            },
            {
                "type": "audio_command",
                "text": "terraform validate"
            },
            {
                "type": "audio_command",
                "text": "terraform plan"
            },
            {
                "type": "audio_command",
                "text": "terraform apply"
            },
            {
                "type": "audio_command",
                "text": "terraform destroy"
            },
            {
                "type": "audio_command",
                "text": "terraform output"
            },
            {
                "type": "concept",
                "title": "Caractéristiques d'Ansible",
                "text": "Ansible utilise YAML avec des fichiers playbook. Il est idempotent : si tu rejoues le même playbook dix fois, tu obtiens le même résultat. Pas besoin d'agent sur les serveurs cibles, tout passe par SSH."
            },
            {
                "type": "method",
                "title": "Fichiers Ansible à connaître",
                "text": "Les fichiers clés d'Ansible : le fichier inventory qui liste les serveurs à configurer. Le fichier playbook qui contient les tâches à exécuter. Les fichiers templates en point J2 pour les configurations dynamiques. Et le dossier group_vars pour les variables par groupe de serveurs."
            },
            {
                "type": "audio_file",
                "text": "---\n- hosts: webservers\n  tasks:\n    - name: Install Nginx\n      apt:\n        name: nginx\n        state: present"
            },
            {
                "type": "method",
                "title": "Commandes Ansible essentielles",
                "text": "Les commandes essentielles : ansible all avec l'option m ping pour tester la connectivité vers tous les serveurs. Et ansible-playbook avec l'option check pour faire un dry-run, une simulation sans appliquer les changements."
            },
            {
                "type": "audio_command",
                "text": "ansible all -m ping"
            },
            {
                "type": "audio_command",
                "text": "ansible-playbook playbook.yml --check"
            }
        ]
    },
    # ---- CP3 : Sécurisation Infrastructure ----
    {
        "id": "cp3",
        "title": "CP3 : Sécurisation Infrastructure",
        "icon": "Shield",
        "content": [
            {
                "type": "intro",
                "text": "Compétence 3 : Sécuriser l'infrastructure. Un sujet que le jury adore. Quatre actions essentielles à connaître pour SSH."
            },
            {
                "type": "security",
                "title": "Action 1 : Désactiver le login root",
                "text": "Dans le fichier de configuration SSH, tu mets PermitRootLogin à no. Pourquoi ? C'est le principe du moindre privilège. Si le compte root est compromis, tout est perdu."
            },
            {
                "type": "audio_code",
                "text": "PermitRootLogin no"
            },
            {
                "type": "security",
                "title": "Action 2 : Clés SSH uniquement, pas de mot de passe",
                "text": "On désactive l'authentification par mot de passe et on n'autorise que les clés SSH. Une clé SSH ne peut pas être brute-forcée comme un mot de passe."
            },
            {
                "type": "audio_code",
                "text": "PasswordAuthentication no"
            },
            {
                "type": "security",
                "title": "Action 3 : Restreindre l'accès SSH par IP",
                "text": "Dans le Security Group AWS, on restreint le port 22 à ta seule adresse IP avec un CIDR slash 32. Si on ouvre à 0.0.0.0/0, n'importe qui peut tenter du brute force depuis Internet."
            },
            {
                "type": "audio_code",
                "text": "0.0.0.0/0"
            },
            {
                "type": "audio_code_explain",
                "text": "Ce CIDR zéro sur zéro signifie tout Internet. C'est à éviter absolument pour le port SSH."
            },
            {
                "type": "security",
                "title": "Action 4 : fail2ban contre le brute force",
                "text": "fail2ban surveille les tentatives de connexion échouées et bannit automatiquement les adresses IP suspectes. C'est ta dernière ligne de défense si quelqu'un tente d'attaquer ton serveur."
            },
            {
                "type": "jury",
                "title": "Question jury : pourquoi slash 32 sur SSH",
                "text": "Pourquoi un CIDR slash 32 sur SSH ? Ta réponse : Moindre privilège réseau. Seule mon IP peut atteindre le port 22. Si j'ouvre à 0.0.0.0 slash 0, n'importe qui peut tenter du brute force."
            }
        ]
    },
    # ---- CP4 : Production Cloud ----
    {
        "id": "cp4",
        "title": "CP4 : Production Cloud",
        "icon": "Cloud",
        "content": [
            {
                "type": "intro",
                "text": "Compétence 4 : Mettre l'infrastructure en production dans le cloud. Comprendre les modèles de service et les composants AWS."
            },
            {
                "type": "concept",
                "title": "Les trois modèles de service cloud",
                "text": "IaaS, Infrastructure as a Service : tu gères l'OS, le runtime et l'application. Le provider gère le matériel et le réseau. Exemple : EC2 sur AWS. C'est ce que tu utilises dans ton projet."
            },
            {
                "type": "technical",
                "text": "PaaS, Platform as a Service : tu gères uniquement l'application et les données. Le provider gère tout le reste. Exemples : Heroku ou AWS Elastic Beanstalk."
            },
            {
                "type": "technical",
                "text": "SaaS, Software as a Service : tu gères uniquement la configuration utilisateur. Le provider gère absolument tout. Exemples : Gmail, Office 365, Salesforce."
            },
            {
                "type": "concept",
                "title": "Composants AWS de ton projet",
                "text": "Voici les composants que tu as déployés. Première brique : le VPC, ton réseau virtuel isolé."
            },
            {
                "type": "audio_code",
                "text": "10.0.0.0/16"
            },
            {
                "type": "audio_code_explain",
                "text": "Ce réseau en slash 16 te donne 65 536 adresses IP disponibles dans ton espace réseau privé."
            },
            {
                "type": "audio_code",
                "text": "10.0.1.0/24"
            },
            {
                "type": "audio_code_explain",
                "text": "Le subnet public en slash 24 te donne 256 adresses. C'est le sous-réseau accessible depuis Internet."
            },
            {
                "type": "technical",
                "text": "Security Group : c'est le pare-feu virtuel AWS. SSH restreint à ton IP, HTTP et HTTPS ouverts au public. Internet Gateway : c'est la passerelle qui connecte ton VPC vers Internet. Instance EC2 de type t2.micro : ton serveur web, éligible au Free Tier AWS. Bucket S3 : le stockage pour tes fichiers statiques et tes backups."
            },
            {
                "type": "jury",
                "title": "Question jury : pourquoi t2.micro",
                "text": "Le jury pourrait demander : Pourquoi t2.micro ? Ta réponse : C'est l'instance éligible au Free Tier AWS, suffisante pour un serveur web statique en contexte de formation. En production je dimensionnerais selon la charge prévue avec un outil comme AWS Cost Explorer."
            }
        ]
    },
    # ---- CP5 : CI/CD & Tests ----
    {
        "id": "cp5",
        "title": "CP5 : CI/CD & Tests",
        "icon": "GitBranch",
        "content": [
            {
                "type": "intro",
                "text": "Compétence 5 : Préparer un environnement de test. La démarche CI/CD et la méthodologie Agile."
            },
            {
                "type": "concept",
                "title": "CI/CD expliqué simplement",
                "text": "CI, Intégration Continue : chaque commit déclenche automatiquement le build et les tests. CD, Déploiement Continu : si les tests passent, le déploiement se fait automatiquement. C'est comme une chaîne de montage automobile. On ne livre pas la voiture si une étape de contrôle qualité échoue."
            },
            {
                "type": "audio_code_explain",
                "text": "Ton pipeline complet : push sur la branche main, vérification du style Python avec flake8, tests avec pytest, build de l'image Docker taguée avec le SHA du commit, puis déploiement."
            },
            {
                "type": "technical",
                "title": "Pipeline GitHub Actions",
                "text": "Voici la structure du fichier YAML de pipeline. Le trigger se déclenche sur push vers main. Le job tourne sur un runner ubuntu-latest. Il checkout le code, lance pytest, puis build l'image Docker."
            },
            {
                "type": "audio_file",
                "text": "name: CI/CD Pipeline\non:\n  push:\n    branches: [ main ]\njobs:\n  test:\n    runs-on: ubuntu-latest\n    steps:\n      - uses: actions/checkout@v2\n      - name: Run tests\n        run: pytest"
            },
            {
                "type": "audio_command",
                "text": "docker build -t myapp:${{ github.sha }} ."
            },
            {
                "type": "audio_code_explain",
                "text": "On utilise le SHA du commit comme tag Docker. Ça garantit la traçabilité : on sait exactement quel commit correspond à quelle image en production."
            },
            {
                "type": "concept",
                "title": "Vocabulaire Agile Scrum",
                "text": "Sprint : itération courte de une à quatre semaines. Backlog : liste des fonctionnalités à développer, priorisée. User Story : besoin exprimé du point de vue de l'utilisateur. Definition of Done : critères pour qu'une tâche soit considérée comme terminée."
            },
            {
                "type": "method",
                "title": "Les environnements du pipeline",
                "text": "La chaîne des environnements : DEV en local sur WSL2, puis TEST avec pytest, puis Staging pour la validation métier, puis Production. Règle importante : chaque environnement doit être identique au suivant. Docker garantit ça : même image, même comportement partout."
            }
        ]
    },
    # ---- CP6 : Stockage des Données ----
    {
        "id": "cp6",
        "title": "CP6 : Stockage des Données",
        "icon": "Database",
        "content": [
            {
                "type": "intro",
                "text": "Compétence 6 : Gérer le stockage des données. SQLite, les types de stockage et les bonnes pratiques de sauvegarde."
            },
            {
                "type": "concept",
                "title": "SQLite dans ton projet",
                "text": "SQLite est une base de données fichier, sans serveur séparé. Choix justifié pour un projet solo ou à faible charge. Zéro configuration, zéro administration."
            },
            {
                "type": "jury",
                "title": "Question jury : Pourquoi SQLite ?",
                "text": "Question probable du jury : Pourquoi SQLite et pas PostgreSQL ? Ta réponse : Pas de serveur séparé à gérer, adapté à un seul utilisateur. J'ai identifié la migration vers PostgreSQL comme évolution si le projet prend de l'ampleur et nécessite de la concurrence en écriture."
            },
            {
                "type": "concept",
                "title": "Les trois types de stockage",
                "text": "Premier type : le stockage bloc, comme AWS EBS ou SAN. C'est utilisé pour le système d'exploitation et les bases de données. C'est comme un disque dur classique. Deuxième type : le stockage fichier, comme NFS ou AWS EFS. Utilisé pour le partage entre plusieurs serveurs. Troisième type : le stockage objet, comme AWS S3. Utilisé pour les fichiers statiques, les backups et les logs. C'est le moins cher et le plus scalable."
            },
            {
                "type": "method",
                "title": "Sauvegarde des données",
                "text": "Pour SQLite, la sauvegarde la plus simple est une copie du fichier de base de données avec un horodatage automatique."
            },
            {
                "type": "audio_command",
                "text": "cp database.sqlite database_$(date +%Y%m%d).sqlite"
            },
            {
                "type": "audio_code_explain",
                "text": "La commande date avec le format année mois jour crée un nom de fichier unique à chaque sauvegarde. En production, on pousse ensuite cette sauvegarde vers S3 pour la redondance géographique."
            },
            {
                "type": "audio_terminal_tip",
                "text": "Règle d'or : tester régulièrement la restauration des sauvegardes. Une sauvegarde non testée n'est pas une sauvegarde."
            }
        ]
    },
    # ---- CP7 : Docker & Containers ----
    {
        "id": "cp7",
        "title": "CP7 : Docker & Containers",
        "icon": "Container",
        "content": [
            {
                "type": "intro",
                "text": "Compétence 7 : Gérer des containers. Docker est au cœur du DevOps moderne. Tu dois pouvoir expliquer ton Dockerfile ligne par ligne."
            },
            {
                "type": "audio_analogy",
                "text": "Un Dockerfile, c'est comme une recette de cuisine. L'instruction FROM, ce sont tes ingrédients de base, l'image sur laquelle tu construis. RUN, c'est les étapes de préparation. CMD, c'est comment servir le plat."
            },
            {
                "type": "audio_code",
                "text": "FROM python:3.9-slim"
            },
            {
                "type": "audio_code_explain",
                "text": "FROM slim pour une image légère. Le suffixe slim signifie sans outils inutiles. Résultat : moins de failles de sécurité potentielles et une image plus petite à télécharger."
            },
            {
                "type": "audio_code",
                "text": "RUN useradd app"
            },
            {
                "type": "audio_code_explain",
                "text": "On crée un utilisateur non-root. Règle d'or absolue : ne jamais faire tourner un conteneur en root en production. C'est l'isolation des privilèges. Si le conteneur est compromis, l'attaquant n'a pas les droits root."
            },
            {
                "type": "audio_code",
                "text": "COPY requirements.txt /app/"
            },
            {
                "type": "audio_code_explain",
                "text": "On copie requirements.txt avant le code source. Pourquoi cet ordre ? Pour exploiter le cache des layers Docker. Si ton code change mais pas tes dépendances, Docker ne réinstalle pas tout. C'est beaucoup plus rapide."
            },
            {
                "type": "audio_code",
                "text": "COPY . /app/"
            },
            {
                "type": "audio_code",
                "text": "RUN pip install -r /app/requirements.txt"
            },
            {
                "type": "audio_code",
                "text": "EXPOSE 8501"
            },
            {
                "type": "audio_code_explain",
                "text": "EXPOSE 8501 : c'est de la documentation pour les développeurs. Le vrai mapping de port se fait au lancement avec docker run -p ou dans le docker-compose. EXPOSE seul n'ouvre rien."
            },
            {
                "type": "audio_code",
                "text": "CMD [\"python\", \"app.py\"]"
            },
            {
                "type": "audio_code_explain",
                "text": "CMD en tableau JSON : c'est la commande par défaut, mais elle est surchargeable au lancement. Différent de ENTRYPOINT qui est fixe et non surchargeable."
            },
            {
                "type": "method",
                "title": "Commandes Docker essentielles",
                "text": "Les commandes à maîtriser absolument."
            },
            {
                "type": "audio_command",
                "text": "docker build -t myapp ."
            },
            {
                "type": "audio_command",
                "text": "docker run -d myapp"
            },
            {
                "type": "audio_command",
                "text": "docker ps"
            },
            {
                "type": "audio_command",
                "text": "docker logs -f mycontainer"
            },
            {
                "type": "audio_command",
                "text": "docker exec -it mycontainer bash"
            },
            {
                "type": "audio_command",
                "text": "docker stats"
            },
            {
                "type": "concept",
                "title": "Docker Compose",
                "text": "Docker Compose orchestre plusieurs containers. Tu définis tes services, les ports, les volumes pour la persistance, les variables d'environnement. Un seul fichier YAML pour tout décrire."
            },
            {
                "type": "audio_file",
                "text": "version: '3'\nservices:\n  web:\n    image: nginx\n    ports:\n      - \"80:80\"\n    volumes:\n      - ./html:/usr/share/nginx/html"
            },
            {
                "type": "audio_command",
                "text": "docker-compose up -d"
            },
            {
                "type": "audio_command",
                "text": "docker-compose down"
            }
        ]
    },
    # ---- CP8 : Kubernetes ----
    {
        "id": "cp8",
        "title": "CP8 : Kubernetes",
        "icon": "Layers",
        "content": [
            {
                "type": "intro",
                "text": "Compétence 8 : Automatiser la mise en production avec Kubernetes. Même si Kubernetes n'est pas dans ton projet, tu dois pouvoir l'expliquer conceptuellement."
            },
            {
                "type": "concept",
                "title": "Architecture Kubernetes",
                "text": "Kubernetes a deux parties. Le Control Plane, c'est le cerveau du cluster. Il contient l'API Server, point d'entrée de toutes les commandes. etcd qui stocke l'état du cluster. Et le Scheduler qui décide sur quel noeud placer les Pods."
            },
            {
                "type": "audio_code_explain",
                "text": "Les Worker Nodes sont les machines qui font tourner les Pods. Le kubelet est l'agent sur chaque node, il applique les instructions. Un Pod est la plus petite unité Kubernetes, il contient un ou plusieurs containers."
            },
            {
                "type": "technical",
                "title": "Deployment et Service",
                "text": "Un Deployment gère les Pods : réplication, rolling update, rollback automatique. Un Service expose les Pods sur le réseau avec une IP stable. C'est comme un load balancer interne qui distribue le trafic entre les Pods."
            },
            {
                "type": "jury",
                "title": "Question jury : pourquoi pas Kubernetes",
                "text": "Le jury pourrait demander : Pourquoi Kubernetes n'est pas dans votre projet ? Ta réponse : Docker Compose couvre mes besoins actuels sur un seul serveur. Kubernetes apporterait haute disponibilité avec les replicas, rolling updates sans downtime, autoscaling selon la charge, et gestion multi-noeuds. Je l'ai identifié comme évolution naturelle pour la production."
            },
            {
                "type": "method",
                "title": "Commandes kubectl essentielles",
                "text": "Les commandes kubectl à connaître."
            },
            {
                "type": "audio_command",
                "text": "kubectl apply -f deployment.yaml"
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
        "content": [
            {
                "type": "intro",
                "text": "Compétence 9 : Définir et mettre en place des statistiques de services. SLI, SLO, SLA et tes métriques Prometheus."
            },
            {
                "type": "concept",
                "title": "SLI, SLO, SLA expliqués",
                "text": "SLI, Service Level Indicator : c'est la mesure réelle observée. Exemple : taux de succès API égal 98 pourcent. SLO, Service Level Objective : c'est l'objectif interne. Exemple : on vise 99,5 pourcent de succès. SLA, Service Level Agreement : c'est le contrat signé avec le client. Exemple : remboursement si disponibilité inférieure à 99 pourcent."
            },
            {
                "type": "technical",
                "title": "Error Budget",
                "text": "L'Error Budget c'est la marge d'erreur autorisée. Si ton SLO est de 99,5 pourcent, tu as 0,5 pourcent d'erreur tolérée. Ça représente environ 3 heures 30 de downtime par mois. Tant que tu restes dans ce budget, tu peux prendre des risques et innover."
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
                "text": "Compteur du nombre total de requêtes reçues par l'application."
            },
            {
                "type": "audio_code",
                "text": "api_calls_total{status=\"success\"}"
            },
            {
                "type": "audio_code_explain",
                "text": "Compteur des appels API réussis, filtré par le label status égal success."
            },
            {
                "type": "audio_code",
                "text": "api_response_seconds"
            },
            {
                "type": "audio_code_explain",
                "text": "Histogramme du temps de réponse en secondes. Permet de calculer les percentiles P50, P90, P99."
            },
            {
                "type": "method",
                "title": "Seuils d'alerte à retenir",
                "text": "Les seuils standards à surveiller : CPU supérieur à 80 pourcent pendant 5 minutes, déclenche une alerte. RAM supérieure à 85 pourcent utilisée, déclenche une alerte. Disque supérieur à 85 pourcent utilisé, déclenche une alerte. Load average supérieur au nombre de CPUs, déclenche une alerte."
            }
        ]
    },
    # ---- CP10 : Monitoring Prometheus ----
    {
        "id": "cp10",
        "title": "CP10 : Monitoring Prometheus",
        "icon": "Activity",
        "content": [
            {
                "type": "intro",
                "text": "Compétence 10 : Exploiter une solution de supervision. Prometheus et Grafana. Question quasi-certaine au jury !"
            },
            {
                "type": "concept",
                "title": "Les trois ports à connaître par cœur",
                "text": "Le jury adore cette question sur les ports. Retiens bien les trois. Port 8000 : ton application Python expose ses métriques sur l'endpoint /metrics via prometheus_client. C'est Prometheus qui vient scraper ce port. Port 9090 : c'est l'interface web de Prometheus, qui centralise et stocke les métriques collectées. Port 3000 : c'est Grafana, le dashboard de visualisation des métriques."
            },
            {
                "type": "jury",
                "title": "Question jury : pourquoi deux ports",
                "text": "Pourquoi deux ports 8000 et 9090 ? Ta réponse : Port 8000 est exposé par mon application Python via prometheus_client. C'est l'endpoint que Prometheus scrape toutes les 15 secondes pour collecter les métriques. Port 9090, c'est l'interface de Prometheus lui-même, qui centralise, stocke et rend interrogeables les métriques collectées."
            },
            {
                "type": "audio_analogy",
                "text": "Prometheus est comme un facteur qui passe relever le courrier à heures fixes. Les applications n'ont pas besoin de savoir où envoyer, elles exposent juste leurs métriques sur /metrics. C'est le mode PULL, opposé au mode PUSH où l'application envoie elle-même les données."
            },
            {
                "type": "method",
                "title": "Requêtes PromQL essentielles",
                "text": "Cinq requêtes à connaître pour le jury."
            },
            {
                "type": "audio_code",
                "text": "api_calls_total{status=\"success\"}"
            },
            {
                "type": "audio_code_explain",
                "text": "Compteur total des appels réussis depuis le démarrage."
            },
            {
                "type": "audio_code",
                "text": "rate(api_calls_total{status=\"error\"}[5m])"
            },
            {
                "type": "audio_code_explain",
                "text": "Taux d'erreurs par seconde calculé sur une fenêtre glissante de 5 minutes. Idéal pour les alertes."
            },
            {
                "type": "audio_code",
                "text": "avg(api_response_seconds)"
            },
            {
                "type": "audio_code_explain",
                "text": "Temps de réponse moyen. Si ce chiffre monte, il y a peut-être un problème de performance."
            },
            {
                "type": "audio_code",
                "text": "up{job=\"monapp\"}"
            },
            {
                "type": "audio_code_explain",
                "text": "Retourne 1 si l'application est accessible, 0 si elle est down. C'est le check de disponibilité de base."
            },
            {
                "type": "concept",
                "title": "SNMP et Syslog",
                "text": "SNMP, Simple Network Management Protocol : supervise les équipements réseau comme les switches et routeurs. Syslog : protocole de centralisation des logs système. Prometheus fait pour les métriques applicatives ce que SNMP fait pour le matériel réseau."
            }
        ]
    },
    # ---- CP11 : Anglais Professionnel ----
    {
        "id": "cp11",
        "title": "CP11 : Anglais Professionnel",
        "icon": "Globe",
        "content": [
            {
                "type": "intro",
                "text": "Compétence 11 : Échanger sur des réseaux professionnels en anglais. Les communautés à connaître et le vocabulaire technique."
            },
            {
                "type": "concept",
                "title": "Communautés professionnelles",
                "text": "Stack Overflow pour résoudre des bugs et chercher des solutions. Server Fault pour les questions système et réseau. GitHub Discussions pour les projets open source. HashiCorp Forum pour Terraform et Vault. Reddit r/devops pour la veille et les retours d'expérience. CNCF Slack pour la communauté Kubernetes et cloud native."
            },
            {
                "type": "method",
                "title": "Vocabulaire anglais technique essentiel",
                "text": "Deployment signifie déploiement. Troubleshoot signifie diagnostiquer un problème. Workaround signifie contournement ou solution temporaire. Deprecated signifie obsolète, à ne plus utiliser. Throughput signifie débit de données. Overhead signifie surcharge de ressources. Upstream signifie le projet source d'origine. Rolling update signifie mise à jour progressive sans downtime."
            },
            {
                "type": "technical",
                "title": "Structure d'une bonne question technique en anglais",
                "text": "Pour poser une question sur un forum anglophone, structure en 5 points. Environment : ton OS et la version de l'outil. Problem : ce que tu observes concrètement. What you tried : ce que tu as déjà essayé. Error message : le message d'erreur exact en anglais. Question : ta question précise et concise."
            }
        ]
    },
    # ---- Compétences Transversales ----
    {
        "id": "transversal",
        "title": "Compétences Transversales",
        "icon": "Wrench",
        "content": [
            {
                "type": "intro",
                "text": "Compétences transversales : la résolution de problèmes et l'apprentissage continu. Méthodes à maîtriser pour le jury."
            },
            {
                "type": "method",
                "title": "Résolution d'incident en 5 étapes",
                "text": "Première étape OBSERVER : que se passe-t-il ? Consulte les logs, les métriques, les messages d'erreur. Ne saute pas directement aux conclusions."
            },
            {
                "type": "method",
                "text": "Deuxième étape ISOLER : depuis quand ? Quel composant est affecté ? Est-ce reproductible ? Quel est le périmètre de l'incident ?"
            },
            {
                "type": "method",
                "text": "Troisième étape HYPOTHÈSE : formule une cause probable basée sur les observations. Note-la avant d'agir."
            },
            {
                "type": "method",
                "text": "Quatrième étape TESTER : vérifie l'hypothèse avec un seul changement à la fois. Un seul changement, sinon tu ne sauras pas ce qui a résolu le problème."
            },
            {
                "type": "method",
                "text": "Cinquième étape CORRIGER : applique la correction définitive et documente l'incident dans un post-mortem pour que ça ne se reproduise pas."
            },
            {
                "type": "concept",
                "title": "Outils de diagnostic système",
                "text": "Les commandes de diagnostic à maîtriser."
            },
            {
                "type": "audio_command",
                "text": "journalctl -u nginx"
            },
            {
                "type": "audio_code_explain",
                "text": "Logs du service nginx via systemd."
            },
            {
                "type": "audio_command",
                "text": "docker logs moncontainer"
            },
            {
                "type": "audio_code_explain",
                "text": "Logs d'un conteneur Docker."
            },
            {
                "type": "audio_command",
                "text": "df -h"
            },
            {
                "type": "audio_code_explain",
                "text": "Espace disque disponible en format lisible."
            },
            {
                "type": "audio_command",
                "text": "free -h"
            },
            {
                "type": "audio_code_explain",
                "text": "Mémoire RAM disponible et utilisée."
            },
            {
                "type": "audio_command",
                "text": "ss -tuln"
            },
            {
                "type": "audio_code_explain",
                "text": "Ports en écoute sur le serveur. Très utile pour vérifier qu'un service est bien démarré."
            },
            {
                "type": "audio_command",
                "text": "ping 8.8.8.8"
            },
            {
                "type": "audio_code_explain",
                "text": "Test de connectivité réseau vers le DNS Google."
            },
            {
                "type": "concept",
                "title": "Sources de veille technologique",
                "text": "Documentation officielle AWS, HashiCorp pour Terraform et Vault, kubernetes.io pour Kubernetes. Le site de l'ANSSI pour les alertes et guides de sécurité. Le blog CNCF pour les tendances cloud native. Reddit r/devops pour les retours d'expérience de la communauté."
            }
        ]
    },
    # ---- Questions Jury ----
    {
        "id": "questions",
        "title": "Questions Jury : Réponses Flash",
        "icon": "HelpCircle",
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
                "answer": "Terraform provisionne l'infrastructure, il crée la VM, le réseau, le pare-feu sur AWS. Ansible configure ce qui tourne dessus, il installe Nginx, crée les utilisateurs. Terraform d'abord, Ansible ensuite."
            },
            {
                "type": "qa",
                "question": "Pourquoi un CIDR slash 32 sur SSH ?",
                "answer": "Moindre privilège réseau : seule mon IP peut atteindre le port 22. Si j'ouvre à 0.0.0.0 slash 0, n'importe qui peut tenter du brute force."
            },
            {
                "type": "qa",
                "question": "Explique ton Dockerfile",
                "answer": "FROM slim pour image légère. Utilisateur non-root par sécurité. COPY requirements avant le code pour le cache Docker. EXPOSE pour documenter le port. CMD pour la commande de démarrage."
            },
            {
                "type": "qa",
                "question": "Pourquoi deux ports 8000 et 9090 ?",
                "answer": "8000 c'est l'endpoint métriques de mon application exposé via prometheus_client. 9090 c'est l'interface Prometheus qui scrappe ce 8000 et stocke les métriques pour les rendre interrogeables."
            },
            {
                "type": "qa",
                "question": "Pourquoi SQLite et pas PostgreSQL ?",
                "answer": "Pas de serveur séparé à gérer, adapté à un seul utilisateur. J'ai identifié la migration vers PostgreSQL comme évolution si la charge augmente et nécessite de la concurrence en écriture."
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
                "answer": "D'abord observer les logs avec docker logs. Vérifier les métriques Prometheus. Identifier depuis quand et quel composant. Formuler une hypothèse, tester un changement à la fois. Corriger et documenter l'incident dans un post-mortem."
            },
            {
                "type": "qa",
                "question": "Comment sécuriser davantage ?",
                "answer": "Ajouter HTTPS avec Let's Encrypt et Certbot. Stocker les secrets dans HashiCorp Vault plutôt qu'en fichier env. Appliquer les recommandations ANSSI de hardening Linux. Renforcer fail2ban et activer les audits avec auditd."
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


@api_router.get("/audio/{section_id}")
async def get_audio(section_id: str):
    """
    Génère et retourne l'audio pour une section donnée.
    Utilise pyttsx3 (gratuit et hors ligne) avec vocalisation technique optimisée.
    """
    section = next((s for s in COURSE_CONTENT if s["id"] == section_id), None)
    if not section:
        raise HTTPException(status_code=404, detail="Section non trouvée")

    # Un moteur TTS par requête pour éviter les conflits concurrents
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
            "note": "Frontend not found. Use /api/course to get content or /api/audio/{section_id} to generate audio."
        })


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
