# Support de révision audio — TopGainersCryptoProject (Titre Pro ASD)

## Problem Statement
L'utilisateur prépare le Titre Professionnel ASD (Admin Sys DevOps) en juin 2026. Il a besoin d'un support de révision audio pour présenter son projet **TopGainersCryptoProject** devant un jury lors de la soutenance.

## Architecture du support de révision
- **Frontend**: React 19 + Tailwind CSS + Shadcn UI
- **Backend**: FastAPI + MongoDB (suivi de progression)
- **TTS**: Web Speech Synthesis API (gratuit, navigateur) + edge-tts / pyttsx3 côté serveur
- **Projet présenté**: TopGainersCryptoProject (Streamlit + PostgreSQL + Prometheus/Grafana + Docker + Terraform + AWS + GitHub Actions)

## Core Requirements
1. Lecture audio du contenu de révision (Web Speech Synthesis)
2. Contenu explicatif (cours, pas simple lecture)
3. Navigation par blocs/sections (5 sections)
4. Contrôle de vitesse (0.5x-2x) et sélection de voix
5. Suivi de progression (sections complétées)
6. QCM de révision adaptés au projet TopGainersCryptoProject
7. Solution 100% gratuite

## Sections du cours
1. Introduction & Présentation du projet TopGainersCryptoProject
2. Architecture technique (Stack, flux de données, sécurité)
3. Docker, CI/CD et Déploiement (Dockerfile, Compose, GitHub Actions, Terraform, k3s)
4. Monitoring & Supervision (Prometheus, Grafana, métriques, alertes)
5. Questions du jury & Réponses préparées

## Implemented Features
- ✅ 5 sections de cours adaptées à TopGainersCryptoProject
- ✅ Lecteur audio avec Web Speech Synthesis
- ✅ Contrôles: Play/Pause/Stop, Vitesse (0.5x-2x), Sélection voix
- ✅ Navigation sidebar avec icônes
- ✅ Suivi de progression (sections complétées marquées)
- ✅ Blocs colorés par type (concept, technique, sécurité, Q/R jury)
- ✅ QCM corrigés (PostgreSQL, CI/CD, monitoring, sécurité, questions jury)
- ✅ Sauvegarde progression en base MongoDB

## Before the defense (TODO)
- Tester l'audio dans un vrai navigateur (voix FR)
- Répéter les réponses aux questions du jury
- Préparer une démo live de l'app (`docker compose up -d`)
