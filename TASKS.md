# Tasks - Invoice Extractor

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
