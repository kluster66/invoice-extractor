# Invoice Extractor avec AWS Bedrock

Outil serverless pour extraire automatiquement les informations structurées des factures PDF en utilisant AWS Bedrock (LLM), avec une interface graphique de consultation et d'export.

## Fonctionnalités

- **Extraction intelligente** : Identification automatique du fournisseur, montant HT, devise, numéro, date, chrono, couverture — avec logique de correction client/fournisseur
- **Déclenchement automatique** : Upload d'un PDF dans S3 → Lambda → Bedrock → DynamoDB
- **Support `.pdf` et `.PDF`** : Les deux extensions déclenchent la Lambda
- **Interface graphique** : `ui_invoices.py` (NiceGui) pour consulter, filtrer, uploader et exporter
- **Outil CLI** : `view_invoices.py` pour consulter et exporter depuis le terminal
- **Export Excel** : Fichiers `.xlsx` avec formatage natif (dates, nombres, filtres auto)
- **Déploiement automatisé** : Infrastructure as Code avec CloudFormation

## Architecture

```
S3 (Upload PDF .pdf/.PDF)
        │
        ▼
   AWS Lambda
        │
        ├──► AWS Bedrock (LLM - extraction JSON)
        │
        └──► DynamoDB (stockage structuré)
                │
        ┌───────┴────────┐
        │                │
  ui_invoices.py   view_invoices.py
  (NiceGui web)    (CLI terminal)
```

## Prérequis

1. **Compte AWS** avec accès à : Bedrock, Lambda, S3, DynamoDB, CloudFormation, IAM
2. **AWS CLI** configuré :
   ```powershell
   aws configure
   ```
3. **Python 3.11+** et **uv** (recommandé) ou pip
4. **Modèles Bedrock activés** (Llama 3.1 70B ne requiert pas d'activation)

## Installation

```powershell
# 1. Cloner le projet
git clone <url-du-repo>
cd invoice-extractor

# 2. Créer l'environnement virtuel
uv venv .venv
.\.venv\Scripts\Activate.ps1

# 3. Installer les dépendances
uv pip install -r requirements.txt
uv pip install nicegui openpyxl

# 4. Créer le fichier de configuration local
copy env.example .env
# Éditer .env avec vos valeurs (Account ID AWS, etc.)
```

## Déploiement AWS

```powershell
python deploy.py
```

Le script gère automatiquement :
- Validation du template CloudFormation
- Création du package Lambda (ZIP)
- Upload du code vers S3
- Déploiement / mise à jour de la stack CloudFormation
- Affichage des URLs de monitoring

## Utilisation

### Interface graphique (recommandé)

```powershell
python ui_invoices.py
# Ouvrir http://localhost:8080
```

Fonctionnalités disponibles :
- **Upload** : glisser-déposer ou sélection de fichiers PDF
- **Tableau** : liste des factures extraites, triable par colonne
- **Filtres** : par fournisseur et par date
- **Export sélection** : télécharge les lignes cochées en `.xlsx`
- **Tout exporter** : télécharge toutes les lignes visibles en `.xlsx`
- **Suppression** : sélective ou totale avec confirmation
- **Quitter** : bouton de sortie propre (ou fermer l'onglet)

### Outil CLI

```powershell
# Afficher toutes les factures
python view_invoices.py

# Exporter en XLSX
python view_invoices.py --export

# Filtres
python view_invoices.py --fournisseur ORANGE --depuis 2025-01-01 --export
```

## Données extraites

| Champ | Type | Description |
|-------|------|-------------|
| `fournisseur` | String | Société émettrice de la facture |
| `numero_facture` | String | Numéro de la facture |
| `date_facture` | Date (YYYY-MM-DD) | Date de la facture |
| `montant_ht` | Number | Montant hors taxes |
| `devise` | String | Code ISO (EUR, USD, GBP…) |
| `chrono` | String | Numéro chrono si présent |
| `couverture` | String | Période de couverture |
| `nom_fichier` | String | Nom du fichier PDF source |

## Configuration

Créer un fichier `.env` à la racine (non versionné) :

```env
DYNAMODB_TABLE_NAME=invoices-extractor
S3_INPUT_BUCKET=invoice-input-{votre-account-id}-us-west-2
AWS_REGION=us-west-2
BEDROCK_MODEL_ID=meta.llama3-1-70b-instruct-v1:0
```

Voir `env.example` pour la liste complète des variables.

## Structure du projet

```
invoice-extractor/
├── src_propre/                         # Code Lambda
│   ├── main.py                        # Handler Lambda + prompt d'extraction
│   ├── bedrock_client.py              # Client AWS Bedrock
│   ├── dynamodb_client.py             # Client DynamoDB
│   ├── pdf_extractor_simple.py        # Extraction texte PDF (PyPDF2)
│   └── config.py                      # Configuration via variables d'env
├── ui_invoices.py                     # Interface graphique NiceGui
├── view_invoices.py                   # Outil CLI
├── deploy.py                          # Script de déploiement AWS
├── cleanup.py                         # Script de nettoyage AWS
├── cloudformation-template-final.yaml # Infrastructure as Code
├── requirements.txt                   # Dépendances locales
├── requirements-lambda.txt            # Dépendances Lambda
├── env.example                        # Template de configuration
└── .gitignore                         # Fichiers exclus du repo
```

## Ressources créées par CloudFormation

| Service | Nom | Description |
|---------|-----|-------------|
| S3 | `invoice-input-{account}-{region}` | Bucket d'entrée des factures |
| Lambda | `invoice-extractor-prod` | Fonction d'extraction |
| DynamoDB | `invoices-extractor` | Table de stockage |
| CloudWatch | `/aws/lambda/invoice-extractor-prod` | Logs |
| IAM | Rôle Lambda | Permissions S3, DynamoDB, Bedrock |

## Dépannage

**"Model access not granted"** → Activer le modèle dans la console AWS Bedrock, ou utiliser Llama 3.1 (pas d'activation requise)

**Lambda ne se déclenche pas** → Vérifier que le trigger S3 accepte `.pdf` ET `.PDF` (cf. `cloudformation-template-final.yaml`)

**Logs Lambda** :
```powershell
aws logs filter-log-events --log-group-name "/aws/lambda/invoice-extractor-prod" --region us-west-2 --limit 20
```

## Nettoyage AWS

```powershell
python cleanup.py
# ou
aws cloudformation delete-stack --stack-name invoice-extractor --region us-west-2
```

---

**Version** : 3.0.0 | **Runtime Lambda** : Python 3.11+ | **Région** : us-west-2
