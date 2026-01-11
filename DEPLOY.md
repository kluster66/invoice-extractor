# Guide de Déploiement - Invoice Extractor

Ce guide explique comment déployer l'extracteur de factures sur AWS.

## 📋 Table des matières

1. [Prérequis](#-prérequis)
2. [⚠️ Problème SAM avec Python 3.14](#⚠️-problème-sam-avec-python-314)
3. [Option 1: CloudFormation direct (recommandé)](#-option-1-cloudformation-direct-recommandé)
4. [Option 2: AWS SAM](#-option-2-aws-sam)
5. [Option 3: AWS CDK](#-option-3-aws-cdk)
6. [Option 4: Déploiement manuel](#-option-4-déploiement-manuel)
7. [Post-déploiement](#-post-déploiement)
8. [Mise à jour](#-mise-à-jour)
9. [Dépannage](#-dépannage)

## 📋 Prérequis

### 1. Compte AWS
- Compte AWS avec accès administrateur
- Région supportée (us-west-2 recommandée)

### 2. Outils locaux
```bash
# AWS CLI (obligatoire)
aws --version  # >= 2.13.0

# Python
python --version  # >= 3.8

# Optionnel selon la méthode
sam --version     # Pour SAM (⚠️ nécessite Python ≤3.13)
cdk --version     # Pour CDK (nécessite Node.js)
```

### 3. Permissions IAM
L'utilisateur doit avoir les permissions :
- `IAM:*` (création de rôles)
- `Lambda:*` (création de fonctions)
- `S3:*` (création de buckets)
- `DynamoDB:*` (création de tables)
- `CloudFormation:*` (pour SAM/CDK)
- `Bedrock:*` (accès aux modèles)

## ⚠️ Problème SAM avec Python 3.14

**AWS SAM CLI a une incompatibilité avec Python 3.14** (Pydantic v1).

### Solutions :

**A. Utiliser CloudFormation direct (recommandé)**
```bash
python deploy_with_cloudformation.py
```

**B. Utiliser Python 3.12 pour SAM**
```bash
# Installer Python 3.12
python3.12 -m venv venv
venv\Scripts\activate  # Windows
pip install aws-sam-cli
```

**C. Utiliser Docker avec SAM**
```bash
sam build --use-container
```

**D. Utiliser CDK (nécessite Node.js)**
```bash
npm install -g aws-cdk
cdk deploy
```

## 🚀 Option 1: CloudFormation direct (recommandé)

### Script de déploiement simplifié
```bash
# 1. Exécuter le script interactif
python deploy_with_cloudformation.py

# 2. Suivre le menu :
#    - Option 1 : Valider le template
#    - Option 2 : Créer la stack
#    - Option 3 : Mettre à jour la stack
#    - Option 4 : Décrire la stack
#    - Option 5 : Supprimer la stack
```

### Déploiement manuel avec CloudFormation
```bash
# 1. Valider le template
aws cloudformation validate-template \
  --template-body file://cloudformation-template.yaml \
  --region us-west-2

# 2. Créer la stack
aws cloudformation create-stack \
  --stack-name invoice-extractor-stack \
  --template-body file://cloudformation-template.yaml \
  --parameters \
    ParameterKey=EnvironmentName,ParameterValue=prod \
    ParameterKey=BucketName,ParameterValue=invoice-extractor-bucket-$(date +%s) \
    ParameterKey=TableName,ParameterValue=invoices \
    ParameterKey=BedrockModelId,ParameterValue=meta.llama3-1-70b-instruct-v1:0 \
  --capabilities CAPABILITY_IAM \
  --region us-west-2 \
  --tags Key=Project,Value=InvoiceExtractor Key=Environment,Value=Production

# 3. Suivre la création
aws cloudformation describe-stacks \
  --stack-name invoice-extractor-stack \
  --region us-west-2
```

### Avantages CloudFormation
- ✅ Pas besoin de SAM ou CDK
- ✅ Compatible avec Python 3.14
- ✅ Script de déploiement interactif inclus
- ✅ Template prêt à l'emploi

## ⚡ Option 2: AWS SAM

### Installation SAM (⚠️ Python ≤3.13 requis)
```bash
# macOS
brew tap aws/tap
brew install aws-sam-cli

# Windows (Chocolatey)
choco install aws-sam-cli

# Linux/Python
pip install aws-sam-cli
```

### Déploiement
```bash
# 1. Naviguer dans le projet
cd invoice-extractor

# 2. Construire l'application
sam build  # ⚠️ Échoue avec Python 3.14

# Alternative avec Docker
sam build --use-container

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

## 🔧 Option 3: AWS CDK

### Installation CDK (nécessite Node.js)
```bash
# Installer CDK globalement
npm install -g aws-cdk

# Vérifier l'installation
cdk --version
```

### Déploiement
```bash
# 1. Installer les dépendances Python
pip install aws-cdk-lib constructs

# 2. Synthétiser le template
cdk synth

# 3. Bootstrap (première fois seulement)
cdk bootstrap aws://ACCOUNT-ID/us-west-2

# 4. Déployer
cdk deploy --require-approval never

# Alternative : utiliser le script Python
python app.py
cdk deploy
```

### Script de déploiement CDK
```bash
# Utiliser le script inclus
python deploy_with_cdk_simple.py
```

## 🛠️ Option 4: Déploiement manuel

### Étape 1: Préparer le package
```bash
# 1. Créer un répertoire pour le package
mkdir -p deployment-package
cd deployment-package

# 2. Installer les dépendances
pip install -r ../requirements-lambda.txt -t .

# 3. Copier le code source
cp -r ../src_propre/* .

# 4. Créer l'archive ZIP
zip -r ../deployment.zip .
```

### Étape 2: Créer les ressources AWS

#### 1. Créer le rôle IAM
```bash
# Créer le rôle
aws iam create-role \
  --role-name InvoiceExtractorRole \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Service": "lambda.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }]
  }'

# Attacher les politiques
aws iam attach-role-policy \
  --role-name InvoiceExtractorRole \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

aws iam attach-role-policy \
  --role-name InvoiceExtractorRole \
  --policy-arn arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess

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
  --handler main.lambda_handler \
  --role arn:aws:iam::ACCOUNT-ID:role/InvoiceExtractorRole \
  --zip-file fileb://deployment.zip \
  --timeout 300 \
  --memory-size 1024 \
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
BUCKET_NAME="invoice-extractor-bucket-$(date +%s)"
aws s3 mb s3://$BUCKET_NAME --region us-west-2

# Configurer les notifications
aws s3api put-bucket-notification-configuration \
  --bucket $BUCKET_NAME \
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
  --source-arn arn:aws:s3:::$BUCKET_NAME
```

## ✅ Post-déploiement

### Vérification
```bash
# 1. Vérifier la fonction Lambda
aws lambda get-function --function-name invoice-extractor

# 2. Vérifier la table DynamoDB
aws dynamodb describe-table --table-name invoices

# 3. Vérifier le bucket S3
aws s3 ls s3://$BUCKET_NAME/

# 4. Tester avec un fichier
aws s3 cp test_factures/facture.pdf s3://$BUCKET_NAME/incoming/
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

## 🔄 Mise à jour

### Mise à jour avec CloudFormation
```bash
# Utiliser le script
python deploy_with_cloudformation.py
# Choisir l'option 3 (Mettre à jour la stack)

# Ou manuellement
aws cloudformation update-stack \
  --stack-name invoice-extractor-stack \
  --template-body file://cloudformation-template.yaml \
  --parameters \
    ParameterKey=EnvironmentName,ParameterValue=prod \
    ParameterKey=BucketName,UsePreviousValue=true \
    ParameterKey=TableName,ParameterValue=invoices \
    ParameterKey=BedrockModelId,ParameterValue=meta.llama3-1-70b-instruct-v1:0 \
  --capabilities CAPABILITY_IAM
```

### Mise à jour avec SAM
```bash
sam build
sam deploy
```

### Mise à jour manuelle
```bash
# 1. Recréer le package
./scripts/build-package.sh

# 2. Mettre à jour la fonction Lambda
aws lambda update-function-code \
  --function-name invoice-extractor \
  --zip-file fileb://deployment.zip
```

## 🔍 Dépannage

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
  --memory-size 2048  # 2GB
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
  --source-arn arn:aws:s3:::$BUCKET_NAME
```

### Problème : "Bedrock access denied"
**Solution** :
1. Aller dans AWS Console → Bedrock → Model access
2. Demander l'accès au modèle souhaité
3. Attendre l'approbation (quelques minutes à heures)

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

### Maintenance
1. **Mettre à jour régulièrement** les dépendances
2. **Monitorer les coûts** avec AWS Cost Explorer
3. **Configurer des sauvegardes** DynamoDB
4. **Documenter les changements** dans CHANGELOG.md

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
**Version du guide** : 2.0.1  
**Environnements supportés** : AWS us-west-2, Python 3.8+  
**Compatibilité SAM** : ⚠️ Nécessite Python ≤3.13  
**Option recommandée** : ✅ CloudFormation direct  
**Statut** : Production Ready ✅
