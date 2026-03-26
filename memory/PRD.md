# Application Révision Audio ASD

## Problem Statement
L'utilisateur prépare le Titre Professionnel ASD (Admin Sys DevOps) en juin 2026. Il a besoin d'une application pour apprendre sa fiche de révision en audio de manière intelligente - pas juste une lecture, mais un vrai cours explicatif.

## Architecture
- **Frontend**: React 19 + Tailwind CSS + Shadcn UI
- **Backend**: FastAPI + MongoDB
- **TTS**: Web Speech Synthesis API (gratuit, navigateur)

## User Personas
- Candidat titre pro ASD préparant l'examen
- Besoin d'apprentissage audio pour mémoriser les concepts DevOps

## Core Requirements (Static)
1. Lecture audio du contenu de révision
2. Contenu explicatif (cours, pas simple lecture)
3. Navigation par blocs/sections
4. Contrôle de vitesse
5. Suivi de progression
6. Solution 100% gratuite

## Implemented Features (26/03/2026)
- ✅ 5 sections de cours (Intro IA, IaC, Docker/CI-CD, Monitoring, Questions Jury)
- ✅ Lecteur audio avec Web Speech Synthesis
- ✅ Contrôles: Play/Pause/Stop, Vitesse (0.5x-2x), Sélection voix
- ✅ Navigation sidebar avec icônes
- ✅ Suivi de progression (sections complétées marquées)
- ✅ Barre de progression visuelle
- ✅ Blocs colorés par type (concept, technique, sécurité, Q/R jury)
- ✅ Surlignage du bloc en cours de lecture
- ✅ Sauvegarde progression en base MongoDB
- ✅ Navigation section précédente/suivante
- ✅ Design Swiss/High-Contrast (IBM Plex Sans/Inter)

## Prioritized Backlog
### P0 (Done)
- Lecture audio complète
- Navigation sections

### P1 (Future)
- Mode quiz interactif sur les questions jury
- Export PDF de la fiche

### P2 (Future)
- Mode sombre
- Partage de progression
- Autres fiches de révision

## Next Action Items
1. Tester l'audio dans un vrai navigateur (Chrome/Firefox avec voix FR)
2. Ajouter mode quiz pour les questions jury
3. Permettre l'upload de nouvelles fiches
