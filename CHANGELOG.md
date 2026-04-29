# Changelog

Tous les changements notables de ce projet sont documentés dans ce fichier.

Format basé sur [Keep a Changelog](https://keepachangelog.com/fr/1.0.0/),
versionnage selon [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [3.2.0] - 2026-04-29

### Ajouté

- **Extraction du fournisseur depuis le nom de fichier sans liste fermée** : `_extract_supplier_from_filename()` — fonctionne par élimination (dates, chiffres, clients connus, mots génériques) sans liste de fournisseurs pré-définie. Compatible avec tout nouveau fournisseur automatiquement.
- **`KNOWN_CLIENTS`** : liste des entités clientes déplacée en constante de module dans `main.py` (plus facile à maintenir et injectée dynamiquement dans le prompt)
- **`_FILENAME_NOISE_WORDS`** : mots génériques de noms de fichiers centralisés en constante
- **Champ `devise` dans DynamoDB** : ajouté aux champs extraits et persistés

### Modifié

- **Prompt d'extraction restructuré** : méthode en 2 étapes explicites (1. identifier le client, 2. en déduire le fournisseur) — réduit significativement les confusions client/fournisseur du LLM
- **`known_suppliers` supprimé** : liste fermée remplacée par extraction générique depuis le nom de fichier
- **`deploy.py`** : `ensurepip.bootstrap()` ajouté avant les appels pip — résout l'erreur `No module named pip` quand le `.venv` ne contient pas pip ; `sys.executable` utilisé à la place de `python` ; `boto3`/`botocore` retirés du package Lambda (fournis nativement par le runtime AWS)
- **`datetime.utcnow()`** remplacé par `datetime.now(timezone.utc)` dans `dynamodb_client.py` (déprécié Python 3.12+)
- **`.gitignore`** : doublons supprimés, chemins absolus `~/.aws/` retirés (non fonctionnels), `.claude/` et `CLAUDE.md` exclus, simplifié de 290 à 70 lignes

### Corrigé

- **Noms de champs DynamoDB** : `'Le numero Chrono du document'`, `'La période de couverture'`, `'nom du fichier que tu trouves ici'` → `chrono`, `couverture`, `nom_fichier` (ces champs n'étaient jamais persistés)
- **Fuite fichier temporaire** dans `process_s3_event` : `try/finally` garantit la suppression de `/tmp/{fichier}` même en cas d'erreur
- **Regex JSON greedy** dans `_extract_json_from_response` : `re.search(r'\{.*\}', re.DOTALL)` → parsing brace-balanced (comptage de `{`/`}`) — évitait d'extraire du JSON invalide
- **`except:` nu** dans `_extract_manual_data` → `except ValueError:`
- **`devise` absent** du mapping `_normalize_field_names` → le champ LLM était silencieusement perdu
- **Tests unitaires** : imports cassés (`src.main` → `src_propre/`), mauvaises classes (`InvoiceExtractor` → `InvoiceExtractorSimple`), méthodes inexistantes (`_clean_json_response`) — 16 tests passent désormais

---

## [3.1.0] - 2026-04-23

### Ajouté

- **Permissions IAM marketplace** : `aws-marketplace:ViewSubscriptions`, `aws-marketplace:Subscribe` ajoutées au rôle Lambda — nécessaires pour invoquer Claude Haiku 4.5 via un inference profile
- **Bouton Rafraîchir** dans l'UI : recharge les données DynamoDB sans recharger la page

### Modifié

- **Modèle Bedrock par défaut** : `us.anthropic.claude-haiku-4-5-20251001-v1:0` (Claude Haiku 4.5, cross-region inference profile)
- **`bedrock_client.py`** : support de la Messages API (Claude 3+) en plus de l'ancienne Completions API (Claude 1/2) — distinction automatique selon l'ID du modèle
- **`cleanup.py`** : réécriture complète avec boto3 — vide le bucket S3 avant de supprimer la stack (évite `DELETE_FAILED`), diagnostic des ressources bloquantes, messages d'erreur explicites
- **Bucket S3** : versioning désactivé (le bucket est un passe-plat, pas un stockage de référence)
- **UI** (`ui_invoices.py`) : bouton Rafraîchir déplacé à gauche, résumé (nombre de factures + total HT) déplacé à l'extrémité droite de la barre d'actions

### Corrigé

- Extraction Bedrock silencieusement vide avec Claude 3+ : la Completions API était utilisée à tort — remplacée par la Messages API (`anthropic_version: bedrock-2023-05-31`)
- `DELETE_FAILED` sur `cleanup.py` quand le bucket S3 n'était pas vide : le script vide maintenant le bucket avant de supprimer la stack

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
