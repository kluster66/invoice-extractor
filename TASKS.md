# Tasks - Invoice Extractor

## v3.2.0 — Fiabilité & qualité code (Avril 2026)

- [x] Suppression de `known_suppliers` (liste fermée) → extraction générique du fournisseur depuis le nom de fichier par élimination
- [x] `KNOWN_CLIENTS` déplacé en constante de module — injecté dynamiquement dans le prompt
- [x] Prompt restructuré en 2 étapes (identifier client → déduire fournisseur) pour réduire les confusions LLM
- [x] Correction noms de champs DynamoDB (`chrono`, `couverture`, `nom_fichier`) — données perdues silencieusement
- [x] Ajout champ `devise` dans les champs persistés DynamoDB et dans `_normalize_field_names`
- [x] Fuite fichier `/tmp/` corrigée dans `process_s3_event` (`try/finally`)
- [x] Regex JSON greedy remplacée par parsing brace-balanced
- [x] `datetime.utcnow()` → `datetime.now(timezone.utc)` (déprécié Python 3.12+)
- [x] `except:` nu → `except ValueError:`
- [x] `deploy.py` : `ensurepip.bootstrap()` + `sys.executable` + retrait `boto3`/`botocore` du package Lambda
- [x] `.gitignore` : nettoyage complets (doublons, chemins absolus, `.claude/` exclu)
- [x] Tests unitaires : imports et classes corrigés — 16 tests passent
- [x] Documentation mise à jour (CHANGELOG, CONFIGURATION, CONTRIBUTING, DEPLOY, TASKS)

---

## v3.0.0 — Interface & Export (Avril 2026)

- [x] Interface graphique NiceGui (`ui_invoices.py`)
  - Tableau des factures avec tri par colonne
  - Filtres fournisseur / date
  - Upload PDF par clic ou glisser-déposer
  - Export XLSX sélection / tout
  - Suppression sélective ou totale avec confirmation
  - Bouton Quitter + arrêt sur fermeture d'onglet
- [x] Outil CLI (`view_invoices.py`) avec export XLSX
- [x] Export Excel natif (openpyxl) : dates, montants, filtres auto, ligne figée
- [x] Champ `devise` ajouté au prompt d'extraction
- [x] Support extension `.PDF` (majuscules) dans le trigger S3
- [x] Suppression de l'Account ID hardcodé — configuration via `.env`
- [x] Nettoyage des fichiers `not_used_*`
- [x] `.gitignore` mis à jour (`factures/`, `.claude/`, `lambda_package_deploy/`)
- [x] Tous les `.md` mis à jour (v3.0.0)

---

## v2.1.0 — Robustesse extraction (Janvier 2026)

- [x] Logique de correction client/fournisseur (Boardriders toujours client)
- [x] Passage à PyPDF2 uniquement pour stabilité Lambda
- [x] Support Claude 3.5 Sonnet
- [x] Documentation mise à jour

---

## v2.0.0 — Multi-modèles (Janvier 2026)

- [x] Support multi-modèles Bedrock (Claude 3, Llama 3, Titan, etc.)
- [x] Configuration AWS intelligente (AWS CLI → env → défaut)
- [x] Parsing JSON robuste
- [x] Modèle par défaut : Llama 3.1 70B (pas d'activation requise)

---

## v1.0.0 — Version initiale (Janvier 2026)

- [x] Extraction PDF avec PyPDF2
- [x] Intégration AWS Bedrock
- [x] Stockage DynamoDB avec indexes
- [x] Trigger S3 → Lambda
- [x] Déploiement CloudFormation
- [x] Tests unitaires

---

## Idées futures

- [ ] Retraitement automatique des factures sans devise (migration des anciens enregistrements)
- [ ] Support des PDF multi-pages avec extraction améliorée
- [ ] Pagination dans l'interface NiceGui pour les grands volumes
- [ ] Alerte CloudWatch en cas d'erreur Lambda
- [ ] Export multi-feuilles Excel (une feuille par fournisseur)
- [ ] Mode dark dans l'interface NiceGui
