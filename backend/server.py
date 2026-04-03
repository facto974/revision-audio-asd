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
from typing import List
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

class UserProgress(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    section_id: str
    completed: bool = False
    last_position: int = 0
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# ====================== CONTENU DE COURS OPTIMISÉ AUDIO ======================
COURSE_CONTENT = [
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
                "text": "Il existe trois types de virtualisation à connaître. Premier type : l'Hyperviseur de Type 1, comme VMware ESXi, KVM ou Hyper-V. Il s'installe directement sur le matériel, on dit bare metal. C'est utilisé en production."
            },
            {
                "type": "technical",
                "text": "Deuxième type : l'Hyperviseur de Type 2, comme VirtualBox ou VMware Workstation. Il s'installe sur un système d'exploitation existant. C'est utilisé pour le développement et les tests en local."
            },
            {
                "type": "technical",
                "text": "Troisième type : les Containers, comme Docker. C'est une isolation légère qui partage le même noyau que le système hôte. Plus léger qu'une machine virtuelle complète."
            },
            {
                "type": "concept",
                "title": "Script Bash : structure de base",
                "text": "Un script Bash est une liste d'instructions shell exécutées dans l'ordre. Il sert à automatiser des actions manuelles dans un terminal. La première ligne commence par le shebang, qui indique que c'est un script Bash. On ajoute souvent une option pour arrêter automatiquement le script si une commande échoue."
            },
            {
                "type": "technical",
                "title": "Exemple de script Bash",
                "text": "Un script typique d'installation serveur va d'abord mettre à jour la liste des paquets, puis installer les services nécessaires comme Nginx, le pare-feu UFW et fail2ban. Ensuite il active et démarre ces services. Enfin il vérifie que tout fonctionne correctement."
            },
            {
                "type": "concept",
                "title": "Script Python pour l'automatisation",
                "text": "Python peut aussi automatiser l'administration système. On utilise le module subprocess pour exécuter des commandes système. L'avantage de Python : une meilleure gestion des erreurs, des conditions, et un code plus lisible pour des automatisations complexes."
            },
            {
                "type": "technical",
                "title": "Script PowerShell pour Windows",
                "text": "Sur Windows Server, on utilise PowerShell. On peut installer des fonctionnalités serveur, créer des utilisateurs locaux, gérer les services. C'est l'équivalent de Bash pour l'écosystème Microsoft."
            }
        ]
    },
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
                "text": "Terraform utilise le langage HCL, avec des fichiers point TF. Il est stateful, ce qui signifie qu'il garde un fichier d'état qui mémorise l'état de ton infrastructure. Attention, règle d'or : ne jamais committer ce fichier d'état dans Git ! En équipe, on le stocke sur S3 avec un verrou DynamoDB."
            },
            {
                "type": "method",
                "title": "Commandes Terraform essentielles",
                "text": "Les commandes clés à retenir : init pour initialiser et télécharger les providers. Validate pour vérifier la syntaxe. Plan pour prévisualiser les changements, c'est un dry-run. Apply pour appliquer et créer l'infrastructure. Destroy pour tout supprimer. Output pour afficher les valeurs de sortie comme l'IP publique."
            },
            {
                "type": "concept",
                "title": "Caractéristiques d'Ansible",
                "text": "Ansible utilise YAML avec des fichiers playbook. Il est idempotent : si tu rejoues le même playbook dix fois, tu obtiens le même résultat. C'est sa force. Pas besoin d'agent sur les serveurs cibles, tout passe par SSH."
            },
            {
                "type": "method",
                "title": "Fichiers Ansible à connaître",
                "text": "Les fichiers clés d'Ansible : le fichier inventory qui liste les serveurs à configurer. Le fichier playbook qui contient les tâches à exécuter. Les fichiers templates en point J2 pour les configurations dynamiques. Et le dossier group_vars pour les variables par groupe de serveurs."
            },
            {
                "type": "technical",
                "title": "Commandes Ansible essentielles",
                "text": "Les commandes essentielles : ansible all moins m ping pour tester la connectivité vers tous les serveurs. Et ansible-playbook avec l'option check pour faire un dry-run, une simulation sans appliquer les changements."
            }
        ]
    },
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
                "text": "Première action de sécurité SSH : désactiver le login root. Dans le fichier de configuration SSH, tu mets PermitRootLogin à no. Pourquoi ? C'est le principe du moindre privilège. Si le compte root est compromis, tout est perdu."
            },
            {
                "type": "security",
                "title": "Action 2 : Clés SSH uniquement",
                "text": "Deuxième action : utiliser uniquement des clés ED25519, pas de mots de passe. Tu mets PasswordAuthentication à no. Un mot de passe peut être bruteforcé en quelques heures, une clé ED25519 c'est quasi impossible. Tu génères la paire de clés avec ssh-keygen et tu copies la clé publique sur le serveur."
            },
            {
                "type": "security",
                "title": "Action 3 : Restreindre l'accès réseau",
                "text": "Troisième action : configurer le Security Group AWS avec un CIDR en slash 32. Tu mets uniquement ton IP avec un masque slash 32. Comme ça, seul toi peux atteindre le port 22. Surface d'attaque nulle. Si tu mets 0.0.0.0 slash 0, n'importe qui peut tenter une attaque."
            },
            {
                "type": "security",
                "title": "Action 4 : Installer fail2ban",
                "text": "Quatrième action : installer fail2ban et configurer une jail SSH. Ça bannit automatiquement les IP après N tentatives de connexion échouées. C'est une protection supplémentaire contre le brute force."
            },
            {
                "type": "concept",
                "title": "Configuration du pare-feu UFW",
                "text": "UFW, le pare-feu simplifié d'Ubuntu. La stratégie : bloquer tout par défaut en entrée, autoriser tout en sortie. Puis ouvrir uniquement les ports nécessaires : 22 pour SSH, 80 pour HTTP, 443 pour HTTPS. Enfin activer le pare-feu."
            },
            {
                "type": "jury",
                "title": "Question jury : HTTPS",
                "text": "Question probable du jury : vous n'avez pas configuré HTTPS ? Ta réponse : En production j'utiliserais Let's Encrypt avec Certbot ou AWS Certificate Manager. Le reverse proxy Nginx redirigerait automatiquement le HTTP vers HTTPS."
            }
        ]
    },
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
                "text": "PaaS, Platform as a Service : tu gères uniquement l'application et les données. Le provider gère tout le reste. Exemple : Heroku ou AWS Elastic Beanstalk."
            },
            {
                "type": "technical",
                "text": "SaaS, Software as a Service : tu gères uniquement la configuration utilisateur. Le provider gère absolument tout. Exemples : Gmail, Office 365, Salesforce."
            },
            {
                "type": "concept",
                "title": "Composants AWS de ton projet",
                "text": "VPC avec un réseau en 10.0.0.0 slash 16 : c'est ton réseau virtuel isolé. Subnet public en 10.0.1.0 slash 24 : c'est le sous-réseau accessible depuis Internet. Security Group : c'est le pare-feu avec SSH restreint et HTTP/HTTPS ouvert."
            },
            {
                "type": "technical",
                "text": "Instance EC2 de type t2.micro : c'est ton serveur web, éligible au Free Tier AWS. Bucket S3 : c'est le stockage pour les fichiers statiques. Internet Gateway : c'est la connexion du VPC vers Internet."
            },
            {
                "type": "jury",
                "title": "Question jury : pourquoi t2.micro",
                "text": "Le jury pourrait demander : Pourquoi t2.micro ? Ta réponse : C'est l'instance éligible au Free Tier AWS, suffisante pour un serveur web statique en contexte de formation. En production je dimensionnerais selon la charge prévue."
            }
        ]
    },
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
                "text": "CI, Intégration Continue : chaque commit déclenche automatiquement le build et les tests. CD, Déploiement Continu : si les tests passent, le déploiement se fait automatiquement. Ton pipeline : push sur la branche main, vérification du style Python, tests avec pytest, build de l'image Docker, puis déploiement."
            },
            {
                "type": "technical",
                "title": "Pipeline GitHub Actions",
                "text": "La CI/CD c'est comme une chaîne de montage automobile. On ne livre pas la voiture si une étape de contrôle qualité échoue. Le trigger se déclenche sur push vers main. Le job checkout récupère le code. Ensuite les tests avec pytest. Si tout passe, on build l'image Docker avec le SHA du commit comme tag pour la traçabilité. Enfin on push vers le registry."
            },
            {
                "type": "concept",
                "title": "Vocabulaire Agile Scrum",
                "text": "Sprint : itération courte de une à quatre semaines. Backlog : liste des fonctionnalités à développer, priorisée. User Story : besoin exprimé du point de vue de l'utilisateur. Definition of Done : critères pour qu'une tâche soit considérée comme terminée. Daily standup : réunion quotidienne de 15 minutes maximum."
            },
            {
                "type": "method",
                "title": "Les environnements du pipeline",
                "text": "La chaîne des environnements : DEV en local sur WSL2, puis TEST avec pytest, puis Staging pour la validation, puis Production. Règle importante : chaque environnement doit être identique au suivant. Docker garantit ça : même image égale même comportement partout."
            }
        ]
    },
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
                "text": "SQLite est une base de données fichier, sans serveur séparé. Choix justifié pour un projet solo ou à faible charge. Question probable du jury : Pourquoi SQLite et pas PostgreSQL ? Ta réponse : Pas de serveur séparé à gérer, adapté à un seul utilisateur. J'ai identifié la migration vers PostgreSQL comme évolution si le projet prend de l'ampleur."
            },
            {
                "type": "concept",
                "title": "Les trois types de stockage",
                "text": "Stockage bloc, comme AWS EBS ou SAN : utilisé pour le système d'exploitation et les bases de données. C'est comme un disque dur classique. Stockage fichier, comme NFS ou AWS EFS : utilisé pour le partage entre serveurs. Stockage objet, comme AWS S3 : utilisé pour les fichiers statiques, les backups et les logs."
            },
            {
                "type": "method",
                "title": "Sauvegarde des données",
                "text": "Pour SQLite, la sauvegarde la plus simple est une copie du fichier de base de données avec un horodatage. En production, on pousse cette sauvegarde vers S3 pour la redondance. Règle d'or : tester régulièrement la restauration des sauvegardes."
            }
        ]
    },
    {
        "id": "cp7",
        "title": "CP7 : Docker & Containers",
        "icon": "Container",
        "content": [
            {
                "type": "intro",
                "text": "Compétence 7 : Gérer des containers. Docker est au coeur du DevOps moderne. Tu dois pouvoir expliquer ton Dockerfile ligne par ligne."
            },
            {
                "type": "concept",
                "title": "Dockerfile : la recette de cuisine",
                "text": "Un Dockerfile, c'est comme une recette de cuisine. L'instruction FROM, ce sont tes ingrédients de base, l'image sur laquelle tu construis. Les instructions RUN, ce sont les étapes de préparation. Et CMD, c'est la façon de servir le plat, la commande de démarrage."
            },
            {
                "type": "technical",
                "title": "FROM : image de base",
                "text": "FROM python 3.9 tiret slim : on choisit une image de base légère. Le suffixe slim signifie sans outils inutiles. Résultat : moins de failles de sécurité potentielles et une image plus petite à télécharger."
            },
            {
                "type": "technical",
                "title": "Utilisateur non-root",
                "text": "RUN useradd app : on crée un utilisateur non-root. Règle d'or absolue : ne jamais faire tourner un conteneur en root en production. C'est l'isolation des privilèges. Si le conteneur est compromis, l'attaquant n'a pas les droits root."
            },
            {
                "type": "technical",
                "title": "Optimisation du cache Docker",
                "text": "COPY requirements.txt avant COPY du code source. Pourquoi cet ordre ? Pour exploiter le cache des layers Docker. Si ton code change mais pas tes dépendances, Docker ne réinstalle pas tout. C'est beaucoup plus rapide."
            },
            {
                "type": "technical",
                "title": "EXPOSE et CMD",
                "text": "EXPOSE 8501 : c'est de la documentation. Le vrai mapping de port se fait au lancement avec docker run moins p ou dans le docker-compose. CMD entre crochets : c'est la commande par défaut, mais elle est surchargeable. Différent de ENTRYPOINT qui est fixe."
            },
            {
                "type": "method",
                "title": "Commandes Docker essentielles",
                "text": "Docker build pour construire une image. Docker run moins d pour lancer en arrière-plan. Docker ps pour lister les containers actifs. Docker logs moins f pour suivre les logs en temps réel. Docker exec moins it pour entrer dans un container. Docker stats pour voir la consommation CPU et RAM."
            },
            {
                "type": "concept",
                "title": "Docker Compose",
                "text": "Docker Compose orchestre plusieurs containers. Tu définis tes services, les ports, les volumes pour la persistance, les variables d'environnement. Un seul fichier YAML pour tout décrire. Docker-compose up moins d pour tout lancer, docker-compose down pour tout arrêter."
            }
        ]
    },
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
                "text": "Kubernetes a deux parties. Le Control Plane, c'est le cerveau du cluster. Il gère l'état désiré. L'API Server est le point d'entrée de toutes les commandes. etcd stocke l'état du cluster. Le Scheduler décide sur quel noeud placer les Pods."
            },
            {
                "type": "technical",
                "text": "Les Worker Nodes sont les machines qui font tourner les Pods. Le kubelet est l'agent sur chaque node, il applique les instructions. Un Pod est la plus petite unité Kubernetes, il contient un ou plusieurs containers."
            },
            {
                "type": "technical",
                "title": "Deployment et Service",
                "text": "Un Deployment gère les Pods : réplication, rolling update, rollback. Un Service expose les Pods sur le réseau avec une IP stable. C'est comme un load balancer interne."
            },
            {
                "type": "jury",
                "title": "Question jury : pourquoi pas Kubernetes",
                "text": "Le jury pourrait demander : Pourquoi Kubernetes n'est pas dans votre projet ? Ta réponse : Docker Compose couvre mes besoins actuels sur un seul serveur. Kubernetes apporterait haute disponibilité avec les replicas, rolling updates sans downtime, autoscaling selon la charge, et gestion multi-noeuds. Je l'ai identifié comme évolution naturelle pour la production."
            },
            {
                "type": "method",
                "title": "Commandes kubectl essentielles",
                "text": "kubectl apply moins f pour déployer un fichier YAML. kubectl get pods pour lister les pods. kubectl logs moins f pour suivre les logs. kubectl exec moins it pour entrer dans un pod. kubectl rollout undo pour faire un rollback. kubectl scale pour changer le nombre de replicas."
            }
        ]
    },
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
                "text": "SLI, Service Level Indicator : c'est la mesure réelle. Exemple : taux de succès API égal 98%. SLO, Service Level Objective : c'est l'objectif interne. Exemple : on vise 99,5% de succès. SLA, Service Level Agreement : c'est le contrat client. Exemple : remboursement si disponibilité inférieure à 99%."
            },
            {
                "type": "technical",
                "title": "Error Budget",
                "text": "L'Error Budget c'est la marge d'erreur autorisée. Si ton SLO est 99,5%, tu as 0,5% d'erreur tolérée. Ça représente environ 3 heures 30 de downtime par mois. Tant que tu restes dans ce budget, tu peux prendre des risques et innover."
            },
            {
                "type": "concept",
                "title": "Tes métriques Prometheus",
                "text": "Dans ton projet, tu exposes des métriques via prometheus_client sur le port 8000. app_requests_total compte le nombre total de requêtes. api_calls_total avec le label status distingue succès et erreurs. api_response_seconds mesure le temps de réponse. db_records_total compte les enregistrements en base."
            },
            {
                "type": "method",
                "title": "Indicateurs système à surveiller",
                "text": "CPU : alerte si supérieur à 80% pendant 5 minutes. RAM : alerte si plus de 85% utilisée. Disque : alerte si plus de 85% utilisé. Load average : alerte si supérieur au nombre de CPUs. Ces seuils sont des points de départ, à ajuster selon l'application."
            }
        ]
    },
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
                "title": "Les trois ports à connaître",
                "text": "Le jury adore cette question sur les ports. Port 8000 : c'est ton application Python qui expose l'endpoint /metrics via prometheus_client. Prometheus vient scraper ce port. Port 9090 : c'est l'interface web de Prometheus qui centralise et stocke les métriques. Port 3000 : c'est Grafana, le dashboard de visualisation."
            },
            {
                "type": "jury",
                "title": "Question jury : deux ports",
                "text": "Pourquoi deux ports 8000 et 9090 ? Ta réponse : Port 8000 est exposé par mon application Python via prometheus_client. C'est l'endpoint que Prometheus scrape pour collecter les métriques. Port 9090 c'est l'interface de Prometheus lui-même, qui centralise, stocke et rend interrogeables les métriques collectées depuis le 8000."
            },
            {
                "type": "concept",
                "title": "Le mode PULL de Prometheus",
                "text": "Prometheus fonctionne en mode PULL, il va chercher les métriques. Contrairement aux systèmes PUSH où les applications envoient leurs données. L'analogie : Prometheus est comme un facteur qui passe relever le courrier à heures fixes. Les applications n'ont pas besoin de savoir où envoyer, elles exposent juste leurs métriques sur /metrics."
            },
            {
                "type": "method",
                "title": "Requêtes PromQL essentielles",
                "text": "Cinq requêtes à connaître. Première : api_calls_total avec status égal success pour le compteur d'appels réussis. Deuxième : rate de api_calls_total status error sur 5 minutes pour le taux d'erreurs par seconde. Troisième : division du sum par le count sur 5 minutes pour le temps de réponse moyen. Quatrième : db_records_total pour le nombre d'enregistrements. Cinquième : up avec le job pour vérifier si l'application est accessible."
            },
            {
                "type": "concept",
                "title": "SNMP et Syslog",
                "text": "SNMP, Simple Network Management Protocol : supervise les équipements réseau comme les switches et routeurs. Chaque équipement a un agent SNMP. Syslog : protocole de centralisation des logs système. Les serveurs envoient leurs logs vers un serveur central. Prometheus fait pour les métriques applicatives ce que SNMP fait pour le réseau."
            }
        ]
    },
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
                "title": "Vocabulaire anglais technique",
                "text": "Deployment signifie déploiement. Troubleshoot signifie diagnostiquer. Workaround signifie contournement, solution temporaire. Deprecated signifie obsolète. Throughput signifie débit. Overhead signifie surcharge de ressources. Upstream signifie projet source. Rolling update signifie mise à jour progressive."
            },
            {
                "type": "technical",
                "title": "Structure d'une bonne question technique",
                "text": "Pour poser une question sur un forum anglophone, structure en 5 points. Environment : ton OS et la version de l'outil. Problem : ce que tu observes. What you tried : ce que tu as déjà essayé. Error message : le message d'erreur exact. Question : ta question précise."
            }
        ]
    },
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
                "text": "Première étape OBSERVER : que se passe-t-il ? Consulte les logs, les métriques, les messages d'erreur. Deuxième étape ISOLER : depuis quand ? Quel composant ? Est-ce reproductible ? Troisième étape HYPOTHÈSE : quelle est la cause probable ?"
            },
            {
                "type": "method",
                "text": "Quatrième étape TESTER : vérifie l'hypothèse avec un seul changement à la fois. Cinquième étape CORRIGER : applique la correction et documente l'incident pour que ça ne se reproduise pas."
            },
            {
                "type": "concept",
                "title": "Outils de diagnostic",
                "text": "Pour les logs, utilise journalctl pour les services système ou docker logs pour les containers. Pour l'espace disque, la commande df. Pour la mémoire, la commande free. Pour les ports en écoute, la commande ss. Pour tester la connectivité réseau, ping vers une IP externe."
            },
            {
                "type": "concept",
                "title": "Sources de veille technologique",
                "text": "Documentation officielle AWS, HashiCorp pour Terraform et Vault, kubernetes.io pour K8s. Le site de l'ANSSI pour les alertes et guides de sécurité. Le blog CNCF pour les tendances cloud native. Reddit r/devops pour les retours d'expérience de la communauté."
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
                "text": "Les 10 questions types du jury avec les réponses flash. Entraîne-toi à les réciter avec tes propres mots !"
            },
            {
                "type": "qa",
                "question": "Question 1 : Présentez votre projet en 2 minutes",
                "answer": "Application web qui affiche les cryptos les plus performantes sur 24h. Elle interroge l'API CoinGecko, stocke en SQLite, affiche via Streamlit. Conteneurisée avec Docker, déployée via CI/CD GitHub Actions, surveillée par Prometheus."
            },
            {
                "type": "qa",
                "question": "Question 2 : Terraform vs Ansible ?",
                "answer": "Terraform provisionne l'infrastructure, il crée la VM, le réseau, le pare-feu sur AWS. Ansible configure ce qui tourne dessus, il installe Nginx, crée les utilisateurs. Terraform d'abord, Ansible ensuite."
            },
            {
                "type": "qa",
                "question": "Question 3 : Pourquoi un CIDR slash 32 sur SSH ?",
                "answer": "Moindre privilège réseau : seule mon IP peut atteindre le port 22. Si j'ouvre à 0.0.0.0/0, n'importe qui peut tenter du brute force."
            },
            {
                "type": "qa",
                "question": "Question 4 : Explique ton Dockerfile",
                "answer": "FROM slim pour image légère. Utilisateur non-root par sécurité. COPY requirements avant le code pour le cache Docker. EXPOSE pour documenter. CMD pour la commande de démarrage."
            },
            {
                "type": "qa",
                "question": "Question 5 : Pourquoi deux ports 8000 et 9090 ?",
                "answer": "8000 c'est l'endpoint métriques de mon application exposé via prometheus_client. 9090 c'est l'interface Prometheus qui scrappe ce 8000 et stocke les métriques."
            },
            {
                "type": "qa",
                "question": "Question 6 : Pourquoi SQLite et pas PostgreSQL ?",
                "answer": "Pas de serveur séparé à gérer, adapté à un seul utilisateur. J'ai identifié la migration vers PostgreSQL comme évolution si la charge augmente."
            },
            {
                "type": "qa",
                "question": "Question 7 : Kubernetes, pourquoi pas dans le projet ?",
                "answer": "Docker Compose suffit pour un seul serveur et un seul utilisateur. Kubernetes apporterait haute disponibilité, rolling updates, autoscaling. Identifié comme évolution naturelle pour la production."
            },
            {
                "type": "qa",
                "question": "Question 8 : Comment tu as utilisé l'IA ?",
                "answer": "Comme outil d'accélération, pas comme solution magique. Pour chaque bloc généré : lu, vérifié sur des sources fiables, compris, testé, adapté. Je peux expliquer chaque ligne."
            },
            {
                "type": "qa",
                "question": "Question 9 : Ton app plante en prod, que fais-tu ?",
                "answer": "D'abord observer les logs avec docker logs. Vérifier les métriques Prometheus. Identifier depuis quand et quel composant. Hypothèse, tester un changement à la fois. Corriger et documenter l'incident."
            },
            {
                "type": "qa",
                "question": "Question 10 : Comment sécuriser davantage ?",
                "answer": "Ajouter HTTPS avec Let's Encrypt et Certbot. Stocker les secrets dans HashiCorp Vault plutôt qu'en fichier env. Appliquer les recommandations ANSSI de hardening Linux. Renforcer fail2ban."
            },
            {
                "type": "conclusion",
                "title": "Message final",
                "text": "Rappelle-toi : le jury évalue ta compréhension, pas ta mémoire. Tu as les projets, tu as la logique, tu as la méthode. Explique avec tes propres mots pourquoi tu as fait chaque choix. Tu n'as pas besoin de tout réciter par coeur. Bonne chance pour ton titre pro ASD, Romain !"
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
