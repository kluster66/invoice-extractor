# Changelog

Tous les changements notables de ce projet sont documentés dans ce fichier.

Format basé sur [Keep a Changelog](https://keepachangelog.com/fr/1.0.0/),
versionnage selon [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [3.0.0] - 2026-04-23

### Ajouté

- **Interface graphique NiceGui** (`ui_invoices.py`) :
  - Tableau des factures triable par colonne
  - Filtres par fournisseur et par date
  - Upload de PDF par clic ou glisser-déposer (déclenche la Lambda automatiquement)
  - Export XLSX de la sélection ou de toutes les lignes
  - Suppression sélective ou totale avec confirmation
  - Bouton Quitter + arrêt automatique à la fermeture de l'onglet
- **Outil CLI** (`view_invoices.py`) : consultation et export XLSX depuis le terminal
- **Export Excel natif** (`openpyxl`) : dates, montants, en-têtes formatés, filtres automatiques, ligne figée
- **Champ `devise`** : extraction du code ISO (EUR, USD, GBP…) ajoutée au prompt Bedrock
- **Support `.PDF` (majuscules)** : le trigger S3 accepte désormais `.pdf` ET `.PDF`

### Modifié

- Configuration externalisée via `.env` / `os.getenv()` — suppression de l'Account ID hardcodé
- `.gitignore` mis à jour : `factures/`, `.claude/`, `not_used_*`, `lambda_package_deploy/`
- `env.example` mis à jour avec toutes les variables nécessaires

### Supprimé

- Fichiers `not_used_*` retirés du dépôt
- Dossier `.claude/` exclu du versionnage

---

## [2.1.0] - 2026-01-24

### Ajouté

- **Logique de correction fournisseur** : correction automatique quand le LLM confond client (ex: Boardriders) et fournisseur
- **Support Claude 3.5 Sonnet** dans la liste des modèles

### Modifié

- **Extraction PDF simplifiée** : PyPDF2 uniquement pour plus de stabilité dans Lambda
- Documentation complète mise à jour (README, DEPLOY, CONFIGURATION)
- Nettoyage du repo : fichiers obsolètes préfixés `not_used_`

---

## [2.0.1] - 2026-01-11

### Ajouté

- `.gitignore` complet pour push GitHub sécurisé
- Script de déploiement CloudFormation direct
- Structure de projet propre : code source dans `src_propre/`

### Modifié

- Documentation mise à jour pour CloudFormation
- Problème SAM avec Python 3.14 documenté

---

## [2.0.0] - 2026-01-11

### Ajouté

- Support multi-modèles Bedrock : Claude 3, Llama 3, Amazon Titan, etc.
- Configuration AWS intelligente : détection automatique région/credentials depuis AWS CLI
- Parsing robuste : extraction JSON même avec texte supplémentaire
- Normalisation des champs : support français/anglais automatique

### Modifié

- Client Bedrock refactorisé pour les différents formats d'API
- Configuration : priorité AWS CLI → Variables d'environnement → Valeurs par défaut
- Prompt d'extraction optimisé
- Modèle par défaut : Llama 3.1 70B (pas d'activation requise)

### Supprimé

- Configuration hardcodée (région/credentials)

---

## [1.0.0] - 2026-01-10

### Ajouté

- Extraction PDF avec PyPDF2
- Intégration AWS Bedrock (Claude 3 Sonnet)
- Stockage DynamoDB avec indexes secondaires
- Déclenchement S3 (architecture serverless)
- Déploiement multi-méthodes : SAM, CDK, manuel
- Tests unitaires
- Documentation complète

---

## Convention de version

- **MAJOR** : Changements incompatibles
- **MINOR** : Nouvelles fonctionnalités rétrocompatibles
- **PATCH** : Corrections de bugs
