# Configuration - Invoice Extractor

Ce document décrit la configuration de l'outil d'extraction de factures PDF.

## 📋 Configuration AWS

### Région AWS

Par défaut : `us-west-2`

Pour changer la région :

1. Modifier le template CloudFormation
2. Mettre à jour les commandes AWS CLI
3. Ré-déployer la stack

### Services AWS utilisés

- **AWS Bedrock** : Modèles LLM pour l'extraction
- **AWS Lambda** : Traitement des factures
- **Amazon S3** : Stockage des fichiers PDF
- **Amazon DynamoDB** : Stockage des données extraites
- **AWS CloudFormation** : Infrastructure as Code
- **AWS IAM** : Gestion des permissions
- **Amazon CloudWatch** : Logs et monitoring

## 🔧 Configuration de l'application

### Variables d'environnement

| Variable | Description | Valeur par défaut | Requis |
| :--- | :--- | :--- | :--- |
| `DYNAMODB_TABLE_NAME` | Nom de la table DynamoDB | `invoices-extractor` | Oui |
| `S3_INPUT_BUCKET` | Nom du bucket S3 (ex: `invoice-input-...`) | Auto-détecté | Oui |
| `BEDROCK_MODEL_ID` | ID du modèle Bedrock à utiliser | `meta.llama3-1-70b-instruct-v1:0` | Oui |
| `ENVIRONMENT_NAME` | Nom de l'environnement (dev, staging, prod) | `prod` | Non |
| `LOG_LEVEL` | Niveau de logging (DEBUG, INFO, WARNING, ERROR) | `INFO` | Non |
| `AWS_REGION` | Région AWS | `us-west-2` | Non |

### Configuration des modèles Bedrock

#### Modèles supportés

```python
# Liste des modèles supportés (dans src_propre/config.py)
BEDROCK_AVAILABLE_MODELS = {
    "llama-3-70b": "meta.llama3-70b-instruct-v1:0",
    "claude-3-sonnet": "anthropic.claude-3-sonnet-20240229-v1:0",
    "claude-3-haiku": "anthropic.claude-3-haiku-20240307-v1:0",
    "titan-text-express": "amazon.titan-text-express-v1"
}
```

#### Activation des modèles

- **Llama 3.1 70B** : Pas d'activation requise
- **Claude 3.5 Sonnet** : Activation requise dans la console AWS Bedrock
- **Amazon Titan** : Activation requise dans la console AWS Bedrock

#### Changer de modèle

```bash
# Via CloudFormation
aws cloudformation update-stack \
  --stack-name invoice-extractor \
  --parameters ParameterKey=BedrockModelId,ParameterValue=anthropic.claude-3-5-sonnet-20241022-v2:0

# Via variable d'environnement (après déploiement)
aws lambda update-function-configuration \
  --function-name invoice-extractor-prod \
  --environment Variables={BEDROCK_MODEL_ID=anthropic.claude-3-5-sonnet-20241022-v2:0}
```

## 🗄️ Configuration DynamoDB

### Structure de la table

```yaml
Table: invoices-extractor
Primary Key: invoice_id (String)
Global Secondary Indexes:
  - numero_facture-index (numero_facture)
  - date_facture-index (date_facture)
  - fournisseur-index (fournisseur)
```

### Schéma des données

```json
{
  "invoice_id": "uuid-v4",
  "numero_facture": "FACT-2024-001",
  "date_facture": "2024-01-15",
  "fournisseur": "Nom du fournisseur",
  "montant_ht": 1500.50,
  "montant_ttc": 1800.60,
  "tva": 300.10,
  "client": "Nom du client",
  "date_echeance": "2024-02-15",
  "statut": "payée",
  "fichier_source": "facture.pdf",
  "date_extraction": "2024-01-15T10:30:00Z",
  "metadata": {
    "modele_utilise": "llama3-1-70b",
    "confiance": 0.95,
    "champs_extraits": ["numero_facture", "date_facture", "montant_ht"]
  }
}
```

### Capacités de provisionnement

- **Read Capacity Units** : 5
- **Write Capacity Units** : 5
- **Auto-scaling** : Non configuré par défaut

Pour modifier les capacités :

```yaml
# Dans cloudformation-template-final.yaml
InvoicesTable:
  Properties:
    ProvisionedThroughput:
      ReadCapacityUnits: 10
      WriteCapacityUnits: 10
```

## 📁 Configuration S3

### Structure du bucket

```text
s3://invoice-extractor-bucket-{id}/
├── factures/              # Factures uploadées
│   ├── 2024/
│   │   ├── 01/
│   │   │   ├── facture1.pdf
│   │   │   └── facture2.pdf
│   │   └── 02/
│   └── 2025/
└── processed/            # Factures traitées (optionnel)
```

### Notifications S3

- **Événements** : `s3:ObjectCreated:*`
- **Filtre** : Fichiers avec extension `.pdf`
- **Destination** : Fonction Lambda `invoice-extractor-prod`

### Configuration des notifications

```json
{
  "LambdaFunctionConfigurations": [{
    "LambdaFunctionArn": "arn:aws:lambda:us-west-2:ACCOUNT:function:invoice-extractor-prod",
    "Events": ["s3:ObjectCreated:*"],
    "Filter": {
      "Key": {
        "FilterRules": [{
          "Name": "suffix",
          "Value": ".pdf"
        }]
      }
    }
  }]
}
```

## ⚙️ Configuration Lambda

### Spécifications techniques

- **Runtime** : Python 3.10
- **Handler** : `main.lambda_handler`
- **Mémoire** : 1024 MB
- **Timeout** : 300 secondes (5 minutes)
- **Architecture** : x86_64

### Variables d'environnement Lambda

```bash
# Voir les variables actuelles
aws lambda get-function-configuration \
  --function-name invoice-extractor-prod \
  --query 'Environment.Variables'

# Mettre à jour les variables
aws lambda update-function-configuration \
  --function-name invoice-extractor-prod \
  --environment 'Variables={LOG_LEVEL=DEBUG,BEDROCK_MODEL_ID=anthropic.claude-3-5-sonnet}'
```

### Permissions IAM

Le rôle Lambda a les permissions suivantes :

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::invoice-extractor-bucket-*",
        "arn:aws:s3:::invoice-extractor-bucket-*/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:PutItem",
        "dynamodb:GetItem",
        "dynamodb:UpdateItem",
        "dynamodb:DeleteItem",
        "dynamodb:Query",
        "dynamodb:Scan",
        "dynamodb:BatchWriteItem",
        "dynamodb:DescribeTable"
      ],
      "Resource": "arn:aws:dynamodb:*:*:table/invoices-extractor"
    },
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:ListFoundationModels"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:*:*:*"
    }
  ]
}
```

## 🔍 Configuration du logging

### Niveaux de log

- **DEBUG** : Informations détaillées pour le débogage
- **INFO** : Informations générales sur l'exécution
- **WARNING** : Avertissements non critiques
- **ERROR** : Erreurs nécessitant une attention

### Configuration CloudWatch

- **Groupe de logs** : `/aws/lambda/invoice-extractor-prod`
- **Rétention** : 30 jours
- **Format** : Texte structuré

### Exemple de logs

```json
{
  "level": "INFO",
  "message": "Début de l'extraction",
  "file": "facture.pdf",
  "model": "llama3-1-70b",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

## 🎯 Configuration de l'extraction

### Prompt d'extraction

```python
EXTRACTION_PROMPT = """
Vous êtes un expert comptable. Extrayez les informations suivantes de la facture :
- Numéro de facture
- Date de facture
- Fournisseur
- Montant HT
- Montant TTC
- TVA
- Client
- Date d'échéance

Retournez les données au format JSON.
"""
```

### Champs extraits

| Champ | Type | Description | Requis |
| :--- | :--- | :--- | :--- |
| `numero_facture` | String | Numéro de la facture | Oui |
| `date_facture` | String (YYYY-MM-DD) | Date de la facture | Oui |
| `fournisseur` | String | Nom du fournisseur | Oui |
| `montant_ht` | Number | Montant hors taxes | Oui |
| `montant_ttc` | Number | Montant toutes taxes comprises | Non |
| `tva` | Number | Montant de la TVA | Non |
| `client` | String | Nom du client | Non |
| `date_echeance` | String (YYYY-MM-DD) | Date d'échéance | Non |

### Normalisation des champs

Le système normalise automatiquement les noms de champs :

- `invoice_number` → `numero_facture`
- `date` → `date_facture`
- `supplier` → `fournisseur`
- `amount` → `montant_ht`

## 🔄 Configuration du déploiement

### Template CloudFormation

- **Fichier** : `cloudformation-template-final.yaml`
- **Région** : `us-west-2`
- **Stack** : `invoice-extractor`

### Paramètres CloudFormation

| Paramètre | Description | Valeur par défaut |
| :--- | :--- | :--- |
| `EnvironmentName` | Nom de l'environnement | `prod` |
| `BucketName` | Nom du bucket S3 | `invoice-input-bucket` |
| `TableName` | Nom de la table DynamoDB | `invoices-extractor` |
| `BedrockModelId` | ID du modèle Bedrock | `meta.llama3-1-70b-instruct-v1:0` |

### Script de déploiement

```bash
# Script principal
python deploy.py

# Fonctions :
# 1. Vérifie les prérequis
# 2. Valide le template
# 3. Crée le package Lambda
# 4. Uploade le code vers le bucket de déploiement
# 5. Déploie la stack CloudFormation
# 6. Affiche les sorties (outputs) et instructions
# 7. Propose un test avec une facture réelle
```

## 🛡️ Configuration de sécurité

### Chiffrement des données

- **S3** : Chiffrement SSE-S3 par défaut
- **DynamoDB** : Chiffrement au repos activé
- **Lambda** : Variables d'environnement non chiffrées

### Contrôle d'accès

- **IAM** : Politiques basées sur les rôles
- **S3** : Accès via politiques de bucket
- **Lambda** : Exécution via rôle IAM

### Bonnes pratiques

1. **Rotation des clés** : Rotation régulière des clés AWS
2. **Audit** : Activation de CloudTrail pour l'audit
3. **Monitoring** : Alertes CloudWatch pour les erreurs
4. **Backup** : Versioning S3 activé

## 📊 Configuration du monitoring

### Métriques CloudWatch

- **Lambda** : Invocations, erreurs, durée, throttling
- **DynamoDB** : Consommation RCU/WCU, latence
- **S3** : Requêtes, données transférées

### Alertes recommandées

```bash
# Créer une alerte pour les erreurs Lambda
aws cloudwatch put-metric-alarm \
  --alarm-name "Lambda-Errors" \
  --metric-name Errors \
  --namespace AWS/Lambda \
  --statistic Sum \
  --period 300 \
  --threshold 1 \
  --comparison-operator GreaterThanThreshold \
  --dimensions Name=FunctionName,Value=invoice-extractor-prod \
  --evaluation-periods 1 \
  --alarm-actions "arn:aws:sns:us-west-2:ACCOUNT:AlertsTopic"
```

## 🔧 Personnalisation avancée

### Ajouter un nouveau champ

1. Modifier le prompt dans `src_propre/bedrock_client.py`
2. Ajouter le mapping dans `_normalize_field_names()`
3. Mettre à jour la validation

### Changer le format de sortie

```python
# Modifier dans src_propre/bedrock_client.py
class BedrockClient:
    def extract_invoice_data(self, text: str) -> Dict:
        # Personnaliser le format de réponse
        prompt = self._build_prompt(text, custom_format=True)
        # ...
```

### Ajouter un prétraitement PDF

```python
# Dans src_propre/pdf_extractor.py
class PDFExtractor:
    def extract_text(self, pdf_path: str) -> str:
        # Ajouter un prétraitement personnalisé
        text = self._extract_with_pypdf2(pdf_path)
        text = self._preprocess_text(text)  # Votre prétraitement
        return text
```

## 📞 Support de configuration

### Problèmes courants

1. **Permissions manquantes** : Vérifier les politiques IAM
2. **Modèle non activé** : Activer dans la console Bedrock
3. **Timeout Lambda** : Augmenter le timeout ou la mémoire
4. **Format PDF non supporté** : Vérifier la compatibilité PyPDF2

### Ressources

- [Documentation AWS Bedrock](https://docs.aws.amazon.com/bedrock/)
- [Guide AWS Lambda](https://docs.aws.amazon.com/lambda/)
- [Template CloudFormation](cloudformation-template-final.yaml)
- [Code source](src_propre/)
