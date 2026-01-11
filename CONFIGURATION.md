# Guide de Configuration - Invoice Extractor

Ce guide explique comment configurer l'extracteur de factures pour votre environnement AWS.

## 📋 Table des matières

1. [Configuration AWS](#-configuration-aws)
2. [Configuration Bedrock](#-configuration-bedrock)
3. [Configuration DynamoDB](#-configuration-dynamodb)
4. [Configuration S3](#-configuration-s3)
5. [Configuration Application](#-configuration-application)
6. [Structure du projet](#-structure-du-projet)
7. [Dépannage](#-dépannage)

## 🔧 Configuration AWS

### Méthode 1: AWS CLI (recommandée)
```bash
# Configurer AWS CLI une fois
aws configure

# Vérifier la configuration
aws configure get region
aws configure get aws_access_key_id
```

### Méthode 2: Variables d'environnement
```bash
# Définir les variables (Linux/Mac)
export AWS_REGION=us-west-2
export AWS_ACCESS_KEY_ID=AKIA...
export AWS_SECRET_ACCESS_KEY=...

# Windows (PowerShell)
$env:AWS_REGION="us-west-2"
$env:AWS_ACCESS_KEY_ID="AKIA..."
$env:AWS_SECRET_ACCESS_KEY="..."
```

### Méthode 3: Fichier .env
```env
AWS_REGION=us-west-2
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
AWS_SESSION_TOKEN=...  # Optionnel
```

### Priorité de configuration
L'application utilise cette priorité :
1. **Variables d'environnement** (AWS_*)
2. **AWS CLI configuration** (aws configure)
3. **Valeurs par défaut** (us-west-2)

## 🤖 Configuration Bedrock

### Activation des modèles
1. **Accéder à AWS Console** : https://console.aws.amazon.com/bedrock/
2. **Naviguer vers "Model access"**
3. **Sélectionner les modèles** et cliquer sur "Request model access"
4. **Remplir le formulaire** de cas d'utilisation
5. **Attendre l'approbation** (généralement rapide)

### Modèles recommandés

#### Pour la production
| Modèle | ID | Avantages | Coût/1K tokens |
|--------|-----|-----------|----------------|
| **Claude 3.5 Sonnet** | `anthropic.claude-3-5-sonnet-20241022-v2:0` | Meilleure précision | ~$3.00 |
| **Llama 3.1 70B** | `meta.llama3-1-70b-instruct-v1:0` | Bon rapport qualité/prix | ~$1.05 |
| **Claude 3 Haiku** | `anthropic.claude-3-haiku-20240307-v1:0` | Rapide et économique | ~$0.25 |

#### Pour le développement
| Modèle | ID | Avantages |
|--------|-----|-----------|
| **Llama 3.1 8B** | `meta.llama3-1-8b-instruct-v1:0` | Très économique |
| **Amazon Titan** | `amazon.titan-text-express-v1` | Natif AWS |

### Configuration du modèle
```env
# Dans .env
BEDROCK_MODEL_ID=meta.llama3-1-70b-instruct-v1:0
BEDROCK_MAX_TOKENS=1000
BEDROCK_TEMPERATURE=0.1
```

### Tester l'accès aux modèles
```bash
# Lister les modèles disponibles
python list_available_models.py

# Tester un modèle spécifique
python -c "
from config.config import Config
Config.set_model('llama-3-1-70b')
print(f'Modèle configuré: {Config.BEDROCK_MODEL_ID}')
"
```

## 🗄️ Configuration DynamoDB

### Table automatique
L'application crée automatiquement la table avec :
- **Nom** : `invoices` (configurable)
- **Clé primaire** : `invoice_id` (UUID)
- **Indexes secondaires** :
  - `numero_facture-index` : Recherche par numéro de facture
  - `date_facture-index` : Recherche par date
  - `fournisseur-index` : Recherche par fournisseur

### Configuration
```env
DYNAMODB_TABLE_NAME=invoices
DYNAMODB_READ_CAPACITY=5
DYNAMODB_WRITE_CAPACITY=5
```

### Vérifier la table
```bash
# Via AWS CLI
aws dynamodb describe-table --table-name invoices

# Via script Python
python check_dynamodb.py
```

## 📦 Configuration S3

### Création du bucket
```bash
# Créer un bucket S3
aws s3 mb s3://votre-bucket-factures --region us-west-2

# Configurer les notifications
aws s3api put-bucket-notification-configuration \
    --bucket votre-bucket-factures \
    --notification-configuration file://s3-notification.json
```

### Configuration
```env
S3_INPUT_BUCKET=votre-bucket-factures
S3_PROCESSED_PREFIX=processed/
S3_ERROR_PREFIX=error/
```

### Structure recommandée
```
s3://votre-bucket-factures/
├── incoming/           # Factures à traiter
├── processed/         # Factures traitées
├── error/            # Factures en erreur
└── archive/          # Archive (optionnel)
```

## ⚙️ Configuration Application

### Variables de base
```env
# Niveau de log
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR

# Limites
MAX_PDF_SIZE_MB=50
EXTRACTION_TIMEOUT=300  # 5 minutes
MAX_RETRY_ATTEMPTS=3

# Répertoire temporaire
TEMP_DIR=/tmp
```

### Configuration avancée
```env
# Pour le développement
LOG_LEVEL=DEBUG
BEDROCK_TEMPERATURE=0.5  # Plus créatif

# Pour la production
LOG_LEVEL=WARNING
BEDROCK_TEMPERATURE=0.1  # Plus précis
MAX_RETRY_ATTEMPTS=5
```

## 📁 Structure du projet

### Organisation des fichiers
```
invoice-extractor/
├── src_propre/              # Code source propre (à versionner)
│   ├── main.py             # Handler Lambda principal
│   ├── bedrock_client.py   # Client multi-modèles AWS Bedrock
│   ├── dynamodb_client.py  # Client DynamoDB avec indexes
│   ├── pdf_extractor.py    # Extraction PDF (PyPDF2 + pdfplumber)
│   └── config.py           # Configuration intelligente AWS
├── config/                 # Configuration
│   ├── config.py          # (copié dans src_propre/)
│   └── env.example        # Template variables d'environnement
├── infrastructure/         # Infrastructure as Code
│   └── cdk-stack.py       # Stack AWS CDK
├── tests/                 # Tests unitaires et d'intégration
├── .gitignore            # Fichiers à ignorer pour GitHub
├── cloudformation-template.yaml  # Template CloudFormation
├── template.yaml         # Template AWS SAM
├── deploy_with_cloudformation.py # Script de déploiement
├── requirements.txt      # Dépendances Python
└── requirements-lambda.txt # Dépendances pour Lambda
```

### Fichiers importants
- **`.gitignore`** : Exclut les secrets, dépendances, artefacts de build
- **`src_propre/`** : Code source propre (pas de dépendances)
- **`config/env.example`** : Template pour variables d'environnement
- **`deploy_with_cloudformation.py`** : Script de déploiement simplifié

### Configuration pour GitHub
Avant de pousser sur GitHub :
1. Vérifier qu'aucun fichier `.env` n'est présent
2. Confirmer que le dossier `src/` (avec dépendances) est ignoré
3. S'assurer que `src_propre/` contient uniquement le code source
4. Vérifier qu'aucune facture réelle n'est dans `test_factures/`

## 🔍 Dépannage

### Problème : "Model access not granted"
**Solution** :
1. AWS Console → Bedrock → Model access
2. Sélectionner le modèle souhaité
3. Cliquer sur "Request model access"
4. Remplir le formulaire
5. Attendre l'approbation (généralement < 1h)

### Problème : "Credentials not found"
**Solution** :
```bash
# Vérifier AWS CLI
aws configure get region
aws sts get-caller-identity

# Configurer si nécessaire
aws configure
```

### Problème : "Region not available"
**Solution** :
```bash
# Vérifier les régions disponibles
aws ec2 describe-regions

# Changer la région
aws configure set region us-west-2
```

### Problème : "DynamoDB table not found"
**Solution** :
```bash
# Créer la table manuellement
aws dynamodb create-table \
    --table-name invoices \
    --attribute-definitions \
        AttributeName=invoice_id,AttributeType=S \
        AttributeName=numero_facture,AttributeType=S \
    --key-schema AttributeName=invoice_id,KeyType=HASH \
    --provisioned-throughput ReadCapacityUnits=5,WriteCapacityUnits=5
```

### Problème : "S3 bucket not found"
**Solution** :
```bash
# Créer le bucket
aws s3 mb s3://votre-bucket-factures --region us-west-2

# Vérifier les permissions
aws s3 ls s3://votre-bucket-factures
```

### Problème : "sam build échoue avec Python 3.14"
**Solution** :
```bash
# Utiliser CloudFormation direct
python deploy_with_cloudformation.py

# Ou utiliser Python 3.12
python3.12 -m venv venv
venv\Scripts\activate
pip install aws-sam-cli
sam build
```

## 📊 Monitoring

### CloudWatch Logs
- **Groupe de logs** : `/aws/lambda/invoice-extractor`
- **Filtres** : `ERROR`, `WARNING`, `INFO`

### CloudWatch Metrics
- `ExtractionSuccess` : Extractions réussies
- `ExtractionFailure` : Échecs d'extraction
- `ProcessingTime` : Temps de traitement

### Vérifications manuelles
```bash
# Vérifier les logs récents
aws logs tail /aws/lambda/invoice-extractor --since 1h

# Compter les éléments dans DynamoDB
aws dynamodb scan --table-name invoices --select COUNT

# Lister les fichiers dans S3
aws s3 ls s3://votre-bucket-factures/ --recursive
```

## 🔄 Mise à jour de la configuration

### Changer de modèle Bedrock
```python
# Via code Python
from config.config import Config
Config.set_model('claude-3-haiku')  # Changer pour Claude 3 Haiku

# Via .env
BEDROCK_MODEL_ID=anthropic.claude-3-haiku-20240307-v1:0
```

### Ajuster les paramètres d'extraction
```env
# Augmenter la précision
BEDROCK_TEMPERATURE=0.1
BEDROCK_MAX_TOKENS=2000

# Réduire les coûts
BEDROCK_MAX_TOKENS=500
```

### Modifier la structure DynamoDB
Modifier `src_propre/dynamodb_client.py` :
- Ajouter/supprimer des indexes
- Changer les capacités
- Ajouter de nouveaux champs

## 🎯 Bonnes pratiques

### Pour le développement
1. Utiliser **Llama 3.1 70B** (pas d'activation requise)
2. Configurer `LOG_LEVEL=DEBUG`
3. Tester avec des petites factures d'abord

### Pour la production
1. Utiliser **Claude 3.5 Sonnet** (meilleure précision)
2. Configurer `LOG_LEVEL=WARNING`
3. Mettre en place des alertes CloudWatch
4. Configurer une stratégie de retention S3

### Optimisation des coûts
1. Utiliser **Claude 3 Haiku** pour les factures simples
2. Limiter `BEDROCK_MAX_TOKENS` à 1000
3. Configurer S3 Lifecycle pour archiver les anciennes factures
4. Utiliser DynamoDB On-Demand si le trafic est variable

## 📞 Support

En cas de problème :
1. **Vérifier les logs** CloudWatch
2. **Tester la configuration** avec `test_models_simple.py`
3. **Vérifier les permissions** IAM
4. **Consulter** la documentation AWS

Pour des questions spécifiques :
- **Documentation AWS Bedrock** : https://docs.aws.amazon.com/bedrock/
- **Forum AWS** : https://repost.aws/
- **Issues GitHub** : https://github.com/votre-repo/issues

---

**Dernière mise à jour** : Janvier 2026  
**Version du guide** : 2.0.1  
**Compatibilité** : AWS us-west-2, Python 3.8+  
**Structure** : Code source propre dans `src_propre/`  
**GitHub Ready** : ✅ Avec `.gitignore` complet  
**Options de déploiement** : CloudFormation, SAM, CDK, Manuel
