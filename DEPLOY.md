# Guide de déploiement - Invoice Extractor

Ce guide explique comment déployer l'outil d'extraction de factures PDF sur AWS.

## 📋 Prérequis

### 1. Compte AWS
- Compte AWS avec accès aux services suivants :
  - AWS Bedrock (avec modèles activés)
  - AWS Lambda
  - Amazon S3
  - Amazon DynamoDB
  - AWS CloudFormation
  - AWS IAM
  - Amazon CloudWatch

### 2. Configuration locale
```bash
# Installer AWS CLI
# Télécharger depuis https://aws.amazon.com/cli/

# Configurer AWS CLI
aws configure
# Entrer :
# - AWS Access Key ID
# - AWS Secret Access Key
# - Default region: us-west-2
# - Default output format: json

# Vérifier la configuration
aws sts get-caller-identity
```

### 3. Environnement Python
```bash
# Python 3.8 ou supérieur
python --version

# Installer les dépendances
pip install -r requirements.txt
```

## 🚀 Déploiement automatique (recommandé)

### Option 1 : Script de déploiement complet
```bash
# Exécuter le script de déploiement
python deploy.py
```

Le script effectue automatiquement :
1. ✅ Vérification de la configuration AWS
2. ✅ Validation du template CloudFormation
3. ✅ Création du package Lambda
4. ✅ Upload du code vers S3
5. ✅ Déploiement de la stack CloudFormation
6. ✅ Configuration des notifications S3
7. ✅ Affichage des URLs de monitoring

### Option 2 : Déploiement étape par étape

#### Étape 1 : Préparer le code Lambda
```bash
# Créer le package ZIP
python -c "
import zipfile
import os

# Créer un package minimal
with zipfile.ZipFile('invoice-extractor-lambda.zip', 'w') as zipf:
    # Ajouter le code source
    for root, dirs, files in os.walk('src_propre'):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, 'src_propre')
                zipf.write(file_path, arcname)
    
    # Ajouter les dépendances minimales
    os.system('pip install boto3 botocore PyPDF2 python-dotenv typing_extensions -t temp_deps --no-deps')
    for root, dirs, files in os.walk('temp_deps'):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, 'temp_deps')
                zipf.write(file_path, arcname)
    
    os.system('rm -rf temp_deps')
"
```

#### Étape 2 : Déployer l'infrastructure
```bash
# Déployer la stack CloudFormation
aws cloudformation create-stack \
  --stack-name invoice-extractor \
  --template-body file://cloudformation-template-final.yaml \
  --parameters \
    ParameterKey=EnvironmentName,ParameterValue=prod \
    ParameterKey=BedrockModelId,ParameterValue=meta.llama3-1-70b-instruct-v1:0 \
  --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM \
  --region us-west-2

# Attendre la création (2-3 minutes)
aws cloudformation wait stack-create-complete \
  --stack-name invoice-extractor \
  --region us-west-2
```

#### Étape 3 : Uploader le code Lambda
```bash
# Récupérer le nom du bucket de déploiement
DEPLOYMENT_BUCKET=$(aws cloudformation describe-stacks \
  --stack-name invoice-extractor \
  --region us-west-2 \
  --query 'Stacks[0].Outputs[?OutputKey==`DeploymentBucketName`].OutputValue' \
  --output text)

# Uploader le code
aws s3 cp invoice-extractor-lambda.zip s3://$DEPLOYMENT_BUCKET/ --region us-west-2

# Mettre à jour la fonction Lambda
aws lambda update-function-code \
  --function-name invoice-extractor-prod \
  --s3-bucket $DEPLOYMENT_BUCKET \
  --s3-key invoice-extractor-lambda.zip \
  --region us-west-2
```

## 🧪 Test du déploiement

### Test 1 : Uploader une facture
```bash
# Récupérer le nom du bucket
BUCKET_NAME=$(aws cloudformation describe-stacks \
  --stack-name invoice-extractor \
  --region us-west-2 \
  --query 'Stacks[0].Outputs[?OutputKey==`BucketName`].OutputValue' \
  --output text)

# Uploader un fichier de test
aws s3 cp test_factures/2140\ 1902095741\ 210515\ TELEFONICA\ MG\ PLVT.pdf \
  s3://$BUCKET_NAME/ --region us-west-2
```

### Test 2 : Vérifier les logs
```bash
# Vérifier les logs CloudWatch
aws logs tail /aws/lambda/invoice-extractor-prod --follow --region us-west-2

# Ou voir les derniers logs
aws logs filter-log-events \
  --log-group-name /aws/lambda/invoice-extractor-prod \
  --region us-west-2 \
  --limit 20 \
  --query 'events[].message'
```

### Test 3 : Vérifier les données
```bash
# Vérifier les données dans DynamoDB
aws dynamodb scan \
  --table-name invoices-extractor \
  --region us-west-2 \
  --query 'Items'
```

## 🔧 Configuration avancée

### Changer le modèle Bedrock
```bash
# Mettre à jour la stack avec un nouveau modèle
aws cloudformation update-stack \
  --stack-name invoice-extractor \
  --template-body file://cloudformation-template-final.yaml \
  --parameters \
    ParameterKey=EnvironmentName,ParameterValue=prod \
    ParameterKey=BedrockModelId,ParameterValue=anthropic.claude-3-5-sonnet-20241022-v2:0 \
  --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM \
  --region us-west-2
```

### Modèles supportés
- `meta.llama3-1-70b-instruct-v1:0` (recommandé, pas d'activation)
- `anthropic.claude-3-5-sonnet-20241022-v2:0`
- `anthropic.claude-3-haiku-20240307-v1:0`
- `amazon.titan-text-express-v1`

### Augmenter les ressources Lambda
Modifier le template CloudFormation :
```yaml
InvoiceExtractorLambda:
  Type: AWS::Lambda::Function
  Properties:
    MemorySize: 2048  # Augmenter la mémoire (MB)
    Timeout: 300      # Augmenter le timeout (secondes)
```

## 🐛 Dépannage

### Erreurs courantes

#### 1. "Model access not granted"
```bash
# Solution 1 : Utiliser Llama 3.1 (pas d'activation requise)
# Solution 2 : Activer le modèle dans la console AWS Bedrock
```

#### 2. "User is not authorized to perform: dynamodb:DescribeTable"
```bash
# Ajouter la permission manuellement
aws iam put-role-policy \
  --role-name invoice-extractor-LambdaExecutionRole-* \
  --policy-name DynamoDBDescribeTable \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Action": "dynamodb:DescribeTable",
      "Resource": "arn:aws:dynamodb:us-west-2:*:table/invoices-extractor"
    }]
  }' \
  --region us-west-2
```

#### 3. Lambda ne s'exécute pas sur upload S3
```bash
# Vérifier la configuration des notifications
aws s3api get-bucket-notification-configuration \
  --bucket invoice-extractor-bucket-* \
  --region us-west-2

# Reconfigurer si nécessaire
aws s3api put-bucket-notification-configuration \
  --bucket invoice-extractor-bucket-* \
  --notification-configuration '{
    "LambdaFunctionConfigurations": [{
      "LambdaFunctionArn": "arn:aws:lambda:us-west-2:*:function:invoice-extractor-prod",
      "Events": ["s3:ObjectCreated:*"],
      "Filter": {
        "Key": {"FilterRules": [{"Name": "suffix", "Value": ".pdf"}]}
      }
    }]
  }' \
  --region us-west-2
```

### Monitoring

#### Logs CloudWatch
```bash
# Suivre les logs en temps réel
aws logs tail /aws/lambda/invoice-extractor-prod --follow

# Voir les erreurs récentes
aws logs filter-log-events \
  --log-group-name /aws/lambda/invoice-extractor-prod \
  --filter-pattern "ERROR" \
  --limit 10
```

#### Métriques Lambda
```bash
# Voir les métriques
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Invocations \
  --dimensions Name=FunctionName,Value=invoice-extractor-prod \
  --start-time $(date -d '1 hour ago' +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date +%Y-%m-%dT%H:%M:%SZ) \
  --period 300 \
  --statistics Sum
```

## 🔄 Mise à jour

### Mettre à jour le code
```bash
# Recréer le package
python deploy.py

# Ou mettre à jour manuellement
aws lambda update-function-code \
  --function-name invoice-extractor-prod \
  --zip-file fileb://invoice-extractor-lambda.zip \
  --region us-west-2
```

### Mettre à jour la configuration
```bash
# Mettre à jour la stack
aws cloudformation update-stack \
  --stack-name invoice-extractor \
  --template-body file://cloudformation-template-final.yaml \
  --parameters \
    ParameterKey=EnvironmentName,ParameterValue=prod \
    ParameterKey=BedrockModelId,ParameterValue=meta.llama3-1-70b-instruct-v1:0 \
  --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM \
  --region us-west-2
```

## 🧹 Nettoyage

### Supprimer toutes les ressources
```bash
# Supprimer la stack CloudFormation
aws cloudformation delete-stack \
  --stack-name invoice-extractor \
  --region us-west-2

# Attendre la suppression
aws cloudformation wait stack-delete-complete \
  --stack-name invoice-extractor \
  --region us-west-2

# Supprimer manuellement les buckets S3 (si nécessaire)
aws s3 rb s3://invoice-extractor-bucket-* --force
aws s3 rb s3://invoice-extractor-deployment-bucket-* --force
```

### Script de nettoyage
```powershell
# Sous Windows
powershell ./cleanup-aws-simple.ps1

# Sous Linux/Mac
./cleanup-aws.sh
```

## 📞 Support

### En cas de problème
1. **Vérifier les logs CloudWatch**
2. **Tester avec un modèle différent** (Llama 3.1 recommandé)
3. **Vérifier les permissions IAM**
4. **Consulter la documentation AWS**

### Ressources utiles
- [Console AWS CloudFormation](https://us-west-2.console.aws.amazon.com/cloudformation)
- [Console AWS Lambda](https://us-west-2.console.aws.amazon.com/lambda)
- [Console AWS Bedrock](https://us-west-2.console.aws.amazon.com/bedrock)
- [Documentation AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/)

---

**Note** : Ce déploiement utilise la région `us-west-2` par défaut.  
Pour utiliser une autre région, modifiez le template CloudFormation et les commandes AWS CLI.
