# Guide de déploiement - Invoice Extractor

## Prérequis

### Compte AWS
Accès aux services suivants :
- AWS Bedrock (modèles activés)
- AWS Lambda, Amazon S3, Amazon DynamoDB
- AWS CloudFormation, AWS IAM, Amazon CloudWatch

### Configuration locale
```powershell
# Installer AWS CLI : https://aws.amazon.com/cli/

# Configurer
aws configure
# Renseigner : Access Key ID, Secret Access Key, région (us-west-2), format (json)

# Vérifier
aws sts get-caller-identity
```

### Environnement Python
```powershell
# Python 3.11+ requis
python --version

# Créer le venv avec uv (recommandé)
uv venv .venv
.\.venv\Scripts\Activate.ps1
uv pip install -r requirements.txt
uv pip install nicegui openpyxl
```

### Fichier .env
```powershell
# Copier le template et renseigner vos valeurs
copy env.example .env
```

Contenu minimal du `.env` :
```env
DYNAMODB_TABLE_NAME=invoices-extractor
S3_INPUT_BUCKET=invoice-input-{votre-account-id}-us-west-2
AWS_REGION=us-west-2
```

Retrouvez votre Account ID :
```powershell
aws sts get-caller-identity --query Account --output text
```

---

## Déploiement automatique (recommandé)

```powershell
python deploy.py
```

Le script effectue automatiquement :
1. Vérification des credentials AWS
2. Validation du template CloudFormation
3. Création du package Lambda (ZIP)
4. Création / vérification du bucket de déploiement S3
5. Upload du code
6. Déploiement ou mise à jour de la stack CloudFormation
7. Affichage des outputs (URLs, ARNs)

Si la stack existe déjà, le script demande confirmation avant la mise à jour.

---

## Ressources créées

| Service | Nom | Description |
|---------|-----|-------------|
| S3 | `invoice-input-{account}-{region}` | Bucket d'entrée des factures PDF |
| S3 | `invoice-extractor-deploy-{account}-{region}` | Bucket de déploiement du code Lambda |
| Lambda | `invoice-extractor-prod` | Fonction d'extraction |
| DynamoDB | `invoices-extractor` | Table de stockage |
| CloudWatch | `/aws/lambda/invoice-extractor-prod` | Logs |
| IAM | Rôle Lambda | Permissions S3, DynamoDB, Bedrock |

---

## Mise à jour du code

Toute modification dans `src_propre/` nécessite un redéploiement :

```powershell
python deploy.py
# Répondre "oui" à la mise à jour de la stack
```

---

## Test du déploiement

### Via l'interface graphique
```powershell
python ui_invoices.py
# Ouvrir http://localhost:8080
# Glisser-déposer un PDF dans la zone d'upload
```

### Via AWS CLI
```powershell
# Uploader directement dans S3
aws s3 cp "chemin\vers\facture.pdf" s3://invoice-input-{account}-us-west-2/ --region us-west-2

# Vérifier les logs Lambda
aws logs filter-log-events --log-group-name "/aws/lambda/invoice-extractor-prod" --region us-west-2 --limit 20

# Vérifier les données extraites
aws dynamodb scan --table-name invoices-extractor --region us-west-2
```

---

## Changer de modèle Bedrock

Via le script de déploiement (modifier `deploy.py`, paramètre `BedrockModelId`) ou directement :

```powershell
aws cloudformation update-stack `
  --stack-name invoice-extractor `
  --template-body file://cloudformation-template-final.yaml `
  --parameters `
    ParameterKey=EnvironmentName,ParameterValue=prod `
    ParameterKey=BedrockModelId,ParameterValue=anthropic.claude-3-5-sonnet-20241022-v2:0 `
  --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM `
  --region us-west-2
```

### Modèles disponibles

| Modèle | ID | Activation requise |
|--------|----|--------------------|
| Llama 3.1 70B | `meta.llama3-1-70b-instruct-v1:0` | Non |
| Claude 3.5 Sonnet | `anthropic.claude-3-5-sonnet-20241022-v2:0` | Oui |
| Claude 3 Haiku | `anthropic.claude-3-haiku-20240307-v1:0` | Oui |
| Amazon Titan | `amazon.titan-text-express-v1` | Oui |

---

## Dépannage

### La Lambda ne se déclenche pas sur upload PDF
```powershell
# Vérifier les notifications S3
aws s3api get-bucket-notification-configuration --bucket invoice-input-{account}-us-west-2 --region us-west-2
```
Le trigger doit accepter `.pdf` ET `.PDF`. Si ce n'est pas le cas, redéployez avec `python deploy.py`.

### Erreur "Model access not granted"
- Utiliser Llama 3.1 70B (pas d'activation requise)
- Ou activer le modèle dans : Console AWS → Bedrock → Model access

### Stack en état ROLLBACK_COMPLETE
```powershell
# Supprimer la stack et recréer
aws cloudformation delete-stack --stack-name invoice-extractor --region us-west-2
aws cloudformation wait stack-delete-complete --stack-name invoice-extractor --region us-west-2
python deploy.py
```

### Logs CloudWatch
```powershell
aws logs filter-log-events `
  --log-group-name "/aws/lambda/invoice-extractor-prod" `
  --region us-west-2 `
  --limit 50
```

---

## Nettoyage

```powershell
# Via script
python cleanup.py

# Via AWS CLI
aws cloudformation delete-stack --stack-name invoice-extractor --region us-west-2
aws cloudformation wait stack-delete-complete --stack-name invoice-extractor --region us-west-2

# Vider et supprimer les buckets S3 manuellement si nécessaire
aws s3 rb s3://invoice-input-{account}-us-west-2 --force
aws s3 rb s3://invoice-extractor-deploy-{account}-us-west-2 --force
```

---

**Note** : Ce déploiement utilise la région `us-west-2` par défaut. Pour une autre région, modifier `AWS_REGION` dans `.env` et dans `deploy.py`.
