# Guide de Déploiement - Invoice Extractor

Ce guide explique comment déployer l'extracteur de factures sur AWS.

## 📋 Table des matières

1. [Prérequis](#-prérequis)
2. [Option 1: AWS SAM (recommandé)](#-option-1-aws-sam-recommandé)
3. [Option 2: AWS CDK](#-option-2-aws-cdk)
4. [Option 3: Déploiement manuel](#-option-3-déploiement-manuel)
5. [Post-déploiement](#-post-déploiement)
6. [Mise à jour](#-mise-à-jour)
7. [Dépannage](#-dépannage)

## 📋 Prérequis

### 1. Compte AWS
- Compte AWS avec accès administrateur
- Région supportée (us-west-2 recommandée)

### 2. Outils locaux
```bash
# AWS CLI
aws --version  # >= 2.13.0

# Python
python --version  # >= 3.8

# Optionnel selon la méthode
sam --version     # Pour SAM
cdk --version     # Pour CDK
```

### 3. Permissions IAM
L'utilisateur doit avoir les permissions :
- `IAM:*` (création de rôles)
- `Lambda:*` (création de fonctions)
- `S3:*` (création de buckets)
- `DynamoDB:*` (création de tables)
- `CloudFormation:*` (pour SAM/CDK)
- `Bedrock:*` (accès aux modèles)

## 🚀 Option 1: AWS SAM (recommandé)

### Installation SAM
```bash
# macOS
brew tap aws/tap
brew install aws-sam-cli

# Windows (Chocolatey)
choco install aws-sam-cli

# Linux
pip install aws-sam-cli
```

### Déploiement
```bash
# 1. Naviguer dans le projet
cd invoice-extractor

# 2. Construire l'application
sam build

# 3. Déployer (mode guidé)
sam deploy --guided

# 4. Déployer (mode non guidé)
sam deploy --stack-name invoice-extractor \
  --s3-bucket votre-bucket-deploiement \
  --region us-west-2 \
  --capabilities CAPABILITY_IAM
```

### Paramètres SAM
Lors du déploiement guidé, spécifier :
- **Stack Name** : `invoice-extractor`
- **AWS Region** : `us-west-2`
- **Bedrock Model** : `meta.llama3-1-70b-instruct-v1:0`
- **S3 Bucket Name** : `factures-{account-id}-{region}`
- **Confirm changes** : `y`
- **Save arguments** : `y`

### Structure déployée
SAM crée automatiquement :
- ✅ **Fonction Lambda** avec runtime Python 3.9
- ✅ **Table DynamoDB** avec indexes
- ✅ **Bucket S3** avec notifications
- ✅ **Rôle IAM** avec permissions
- ✅ **CloudWatch Logs** pour le monitoring

## ⚡ Option 2: AWS CDK

### Installation CDK
```bash
# Installer CDK globalement
npm install -g aws-cdk

# Vérifier l'installation
cdk --version
```

### Déploiement
```bash
# 1. Naviguer dans le dossier infrastructure
cd infrastructure

# 2. Installer les dépendances Python
pip install -r requirements.txt

# 3. Initialiser CDK (première fois seulement)
cdk bootstrap aws://ACCOUNT-ID/us-west-2

# 4. Synthétiser le template
cdk synth

# 5. Déployer
cdk deploy --require-approval never
```

### Configuration CDK
Modifier `infrastructure/cdk-stack.py` :
```python
# Changer le modèle Bedrock
bedrock_model_id="meta.llama3-1-70b-instruct-v1:0"

# Changer le nom du bucket
bucket_name=f"factures-{account_id}-{region}"

# Ajuster les capacités DynamoDB
read_capacity=5
write_capacity=5
```

## 🛠️ Option 3: Déploiement manuel

### Étape 1: Préparer le package
```bash
# 1. Créer un répertoire pour le package
mkdir -p deployment-package
cd deployment-package

# 2. Installer les dépendances
pip install -r ../requirements.txt -t .

# 3. Copier le code source
cp -r ../src/* .
cp -r ../config/* .

# 4. Créer l'archive ZIP
zip -r ../deployment.zip .
```

### Étape 2: Créer les ressources AWS

#### 1. Créer le rôle IAM
```bash
# Créer le rôle
aws iam create-role \
  --role-name InvoiceExtractorRole \
  --assume-role-policy-document file://trust-policy.json

# Attacher les politiques
aws iam attach-role-policy \
  --role-name InvoiceExtractorRole \
  --policy-arn arn:aws:iam::aws:policy/AmazonS3FullAccess

aws iam attach-role-policy \
  --role-name InvoiceExtractorRole \
  --policy-arn arn:aws:iam::aws:policy/AmazonDynamoDBFullAccess

aws iam attach-role-policy \
  --role-name InvoiceExtractorRole \
  --policy-arn arn:aws:iam::aws:policy/AmazonBedrockFullAccess
```

#### 2. Créer la fonction Lambda
```bash
aws lambda create-function \
  --function-name invoice-extractor \
  --runtime python3.9 \
  --handler src.main.lambda_handler \
  --role arn:aws:iam::ACCOUNT-ID:role/InvoiceExtractorRole \
  --zip-file fileb://deployment.zip \
  --timeout 300 \
  --memory-size 512 \
  --environment "Variables={ \
    AWS_REGION=us-west-2, \
    BEDROCK_MODEL_ID=meta.llama3-1-70b-instruct-v1:0, \
    DYNAMODB_TABLE_NAME=invoices, \
    LOG_LEVEL=INFO \
  }"
```

#### 3. Créer le bucket S3
```bash
# Créer le bucket
aws s3 mb s3://factures-ACCOUNT-ID-us-west-2 --region us-west-2

# Configurer les notifications
aws s3api put-bucket-notification-configuration \
  --bucket factures-ACCOUNT-ID-us-west-2 \
  --notification-configuration '{
    "LambdaFunctionConfigurations": [
      {
        "LambdaFunctionArn": "arn:aws:lambda:us-west-2:ACCOUNT-ID:function:invoice-extractor",
        "Events": ["s3:ObjectCreated:*"],
        "Filter": {
          "Key": {
            "FilterRules": [
              {"Name": "suffix", "Value": ".pdf"}
            ]
          }
        }
      }
    ]
  }'
```

#### 4. Donner l'accès S3 à Lambda
```bash
aws lambda add-permission \
  --function-name invoice-extractor \
  --statement-id s3-invoke \
  --action lambda:InvokeFunction \
  --principal s3.amazonaws.com \
  --source-arn arn:aws:s3:::factures-ACCOUNT-ID-us-west-2
```

## ✅ Post-déploiement

### Vérification
```bash
# 1. Vérifier la fonction Lambda
aws lambda get-function --function-name invoice-extractor

# 2. Vérifier la table DynamoDB
aws dynamodb describe-table --table-name invoices

# 3. Vérifier le bucket S3
aws s3 ls s3://factures-ACCOUNT-ID-us-west-2/

# 4. Tester avec un fichier
aws s3 cp test_factures/facture.pdf s3://factures-ACCOUNT-ID-us-west-2/incoming/
```

### Monitoring
```bash
# Voir les logs en temps réel
aws logs tail /aws/lambda/invoice-extractor --follow

# Voir les métriques CloudWatch
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Duration \
  --dimensions Name=FunctionName,Value=invoice-extractor \
  --start-time $(date -u -v-1H +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 300 \
  --statistics Average
```

### Configuration des alertes
```bash
# Créer une alarme pour les erreurs
aws cloudwatch put-metric-alarm \
  --alarm-name InvoiceExtractor-Errors \
  --metric-name Errors \
  --namespace AWS/Lambda \
  --statistic Sum \
  --period 300 \
  --threshold 1 \
  --comparison-operator GreaterThanThreshold \
  --dimensions Name=FunctionName,Value=invoice-extractor \
  --evaluation-periods 1 \
  --alarm-actions arn:aws:sns:us-west-2:ACCOUNT-ID:AlertsTopic
```

## 🔄 Mise à jour

### Mise à jour avec SAM
```bash
# 1. Mettre à jour le code
git pull origin main

# 2. Reconstruire et déployer
sam build
sam deploy

# 3. Option: déployer une version spécifique
sam deploy --parameter-overrides BedrockModelId=anthropic.claude-3-5-sonnet-20241022-v2:0
```

### Mise à jour avec CDK
```bash
cd infrastructure
cdk deploy
```

### Mise à jour manuelle
```bash
# 1. Recréer le package
./scripts/build-package.sh

# 2. Mettre à jour la fonction Lambda
aws lambda update-function-code \
  --function-name invoice-extractor \
  --zip-file fileb://deployment.zip

# 3. Mettre à jour la configuration
aws lambda update-function-configuration \
  --function-name invoice-extractor \
  --environment "Variables={BEDROCK_MODEL_ID=anthropic.claude-3-5-sonnet-20241022-v2:0}"
```

## 🔍 Dépannage

### Problème : "Lambda timeout"
**Solution** :
```bash
# Augmenter le timeout
aws lambda update-function-configuration \
  --function-name invoice-extractor \
  --timeout 600  # 10 minutes

# Augmenter la mémoire
aws lambda update-function-configuration \
  --function-name invoice-extractor \
  --memory-size 1024  # 1GB
```

### Problème : "S3 trigger not working"
**Solution** :
```bash
# Vérifier les permissions
aws lambda get-policy --function-name invoice-extractor

# Réattacher la permission
aws lambda remove-permission \
  --function-name invoice-extractor \
  --statement-id s3-invoke

aws lambda add-permission \
  --function-name invoice-extractor \
  --statement-id s3-invoke \
  --action lambda:InvokeFunction \
  --principal s3.amazonaws.com \
  --source-arn arn:aws:s3:::factures-ACCOUNT-ID-us-west-2
```

### Problème : "DynamoDB throttling"
**Solution** :
```bash
# Augmenter les capacités
aws dynamodb update-table \
  --table-name invoices \
  --provisioned-throughput ReadCapacityUnits=10,WriteCapacityUnits=10

# Ou passer en mode On-Demand
aws dynamodb update-table \
  --table-name invoices \
  --billing-mode PAY_PER_REQUEST
```

### Problème : "Bedrock access denied"
**Solution** :
```bash
# Vérifier les permissions IAM
aws iam get-role --role-name InvoiceExtractorRole

# Ajouter la permission Bedrock
aws iam attach-role-policy \
  --role-name InvoiceExtractorRole \
  --policy-arn arn:aws:iam::aws:policy/AmazonBedrockFullAccess
```

## 📊 Coûts estimés

### Coûts mensuels (1000 factures)
| Service | Coût estimé | Facteur de coût |
|---------|-------------|-----------------|
| **AWS Bedrock** | $2-5 | $0.00105/token (Llama 3.1 70B) |
| **AWS Lambda** | $0.20 | 300s × 1024MB × 1000 invocations |
| **Amazon S3** | $0.50 | 1000 fichiers × 200KB × 30 jours |
| **DynamoDB** | $1-2 | 5 RCU/WCU provisionnés |
| **CloudWatch** | $0.50 | Logs et métriques |
| **Total** | **$4-8/mois** | |

### Optimisation des coûts
1. **Utiliser Claude 3 Haiku** : ~75% moins cher que Sonnet
2. **Limiter les tokens** : Configurer `BEDROCK_MAX_TOKENS=500`
3. **DynamoDB On-Demand** : Pour un trafic variable
4. **S3 Lifecycle** : Archiver les anciennes factures après 30 jours

## 🎯 Bonnes pratiques

### Sécurité
1. **Utiliser des rôles IAM** avec le principe de moindre privilège
2. **Chiffrer les données** S3 et DynamoDB
3. **Utiliser VPC** pour l'isolation réseau
4. **Auditer les logs** CloudTrail régulièrement

### Performance
1. **Augmenter la mémoire Lambda** pour les PDF complexes
2. **Utiliser des indexes DynamoDB** pour les requêtes fréquentes
3. **Configurer S3 multipart upload** pour les gros fichiers
4. **Mettre en cache** les résultats fréquents

### Maintenance
1. **Mettre à jour régulièrement** les dépendances
2. **Monitorer les coûts** avec AWS Cost Explorer
3. **Configurer des sauvegardes** DynamoDB
4. **Documenter les changements** dans un CHANGELOG

## 📞 Support

### Ressources
- **Documentation AWS** : https://docs.aws.amazon.com/
- **Forum AWS** : https://repost.aws/
- **GitHub Issues** : https://github.com/votre-repo/issues

### Escalation
1. **Vérifier les logs** CloudWatch
2. **Tester localement** avec `test_models_simple.py`
3. **Consulter** la documentation de dépannage
4. **Ouvrir un ticket** AWS Support si nécessaire

---

**Dernière mise à jour** : Janvier 2026  
**Version du guide** : 2.0.0  
**Environnements supportés** : AWS us-west-2, Python 3.8+  
**Statut** : Production Ready ✅
