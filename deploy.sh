#!/bin/bash
# Script de déploiement pour l'outil d'extraction de factures

set -e  # Arrêter en cas d'erreur

# Configuration
ENVIRONMENT=${1:-"dev"}
REGION=${2:-"us-east-1"}
STACK_NAME="invoice-extractor-$ENVIRONMENT"
BUCKET_NAME="invoice-input-bucket-$ENVIRONMENT-$(date +%s)"
TABLE_NAME="invoices-$ENVIRONMENT"

echo "🔧 Déploiement de l'outil d'extraction de factures"
echo "Environnement: $ENVIRONMENT"
echo "Région: $REGION"
echo "Stack CloudFormation: $STACK_NAME"

# Vérifier que AWS CLI est configuré
if ! aws sts get-caller-identity > /dev/null 2>&1; then
    echo "❌ AWS CLI n'est pas configuré. Veuillez configurer vos credentials."
    exit 1
fi

# Vérifier l'accès à Bedrock
echo "🔍 Vérification de l'accès à AWS Bedrock..."
if ! aws bedrock list-foundation-models --region $REGION > /dev/null 2>&1; then
    echo "⚠️  Attention: Impossible d'accéder à Bedrock. Vérifiez les permissions IAM."
    read -p "Continuer malgré tout? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Créer le package de déploiement
echo "📦 Création du package de déploiement..."
rm -rf package 2>/dev/null || true
mkdir -p package

# Installer les dépendances
echo "📥 Installation des dépendances..."
pip install -r requirements.txt -t package/

# Copier le code source
echo "📄 Copie du code source..."
cp -r src/* package/
cp config/config.py package/config/

# Créer le fichier ZIP
echo "🗜️  Création de l'archive ZIP..."
cd package
zip -r ../invoice-extractor.zip .
cd ..

# Créer un bucket S3 pour le code Lambda (si nécessaire)
CODE_BUCKET="lambda-code-$ENVIRONMENT-$(aws sts get-caller-identity --query Account --output text)"
echo "🪣 Création du bucket S3 pour le code: $CODE_BUCKET"

if ! aws s3api head-bucket --bucket "$CODE_BUCKET" --region $REGION 2>/dev/null; then
    aws s3 mb s3://$CODE_BUCKET --region $REGION
    echo "✅ Bucket S3 créé"
else
    echo "✅ Bucket S3 existe déjà"
fi

# Uploader le code Lambda
echo "⬆️  Upload du code Lambda..."
aws s3 cp invoice-extractor.zip s3://$CODE_BUCKET/ --region $REGION

# Déployer avec CloudFormation
echo "🚀 Déploiement avec CloudFormation..."

# Préparer les paramètres
PARAMETERS="ParameterKey=EnvironmentName,ParameterValue=$ENVIRONMENT \
            ParameterKey=BucketName,ParameterValue=$BUCKET_NAME \
            ParameterKey=TableName,ParameterValue=$TABLE_NAME"

# Vérifier si la stack existe déjà
if aws cloudformation describe-stacks --stack-name $STACK_NAME --region $REGION > /dev/null 2>&1; then
    echo "📝 Mise à jour de la stack existante..."
    aws cloudformation update-stack \
        --stack-name $STACK_NAME \
        --template-body file://cloudformation-template.yaml \
        --parameters $PARAMETERS \
        --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM \
        --region $REGION
    
    echo "⏳ Attente de la mise à jour de la stack..."
    aws cloudformation wait stack-update-complete \
        --stack-name $STACK_NAME \
        --region $REGION
else
    echo "🆕 Création d'une nouvelle stack..."
    aws cloudformation create-stack \
        --stack-name $STACK_NAME \
        --template-body file://cloudformation-template.yaml \
        --parameters $PARAMETERS \
        --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM \
        --region $REGION
    
    echo "⏳ Attente de la création de la stack..."
    aws cloudformation wait stack-create-complete \
        --stack-name $STACK_NAME \
        --region $REGION
fi

# Mettre à jour la fonction Lambda avec le vrai code
echo "🔄 Mise à jour du code Lambda..."
LAMBDA_FUNCTION_NAME=$(aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --region $REGION \
    --query "Stacks[0].Outputs[?OutputKey=='LambdaFunctionName'].OutputValue" \
    --output text)

aws lambda update-function-code \
    --function-name $LAMBDA_FUNCTION_NAME \
    --s3-bucket $CODE_BUCKET \
    --s3-key invoice-extractor.zip \
    --region $REGION

echo "✅ Mise à jour du code Lambda terminée"

# Afficher les outputs
echo ""
echo "🎉 Déploiement terminé avec succès!"
echo ""
echo "📋 Outputs CloudFormation:"
aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --region $REGION \
    --query "Stacks[0].Outputs" \
    --output table

echo ""
echo "🔗 URLs et informations:"
echo "- Bucket S3 pour upload: $BUCKET_NAME"
echo "- Table DynamoDB: $TABLE_NAME"
echo "- Fonction Lambda: $LAMBDA_FUNCTION_NAME"
echo ""
echo "📤 Pour uploader une facture:"
echo "aws s3 cp votre-facture.pdf s3://$BUCKET_NAME/"
echo ""
echo "📊 Pour vérifier les données extraites:"
echo "aws dynamodb scan --table-name $TABLE_NAME --region $REGION --max-items 10"
echo ""
echo "🧹 Pour nettoyer (supprimer toutes les ressources):"
echo "aws cloudformation delete-stack --stack-name $STACK_NAME --region $REGION"

# Nettoyer les fichiers temporaires
rm -rf package invoice-extractor.zip 2>/dev/null || true
echo ""
echo "🧽 Fichiers temporaires nettoyés"
