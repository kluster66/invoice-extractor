# Script de déploiement PowerShell pour l'outil d'extraction de factures

param(
    [string]$Environment = "dev",
    [string]$Region = "us-east-1"
)

$ErrorActionPreference = "Stop"

# Configuration
$StackName = "invoice-extractor-$Environment"
$Timestamp = Get-Date -Format "yyyyMMddHHmmss"
$BucketName = "invoice-input-bucket-$Environment-$Timestamp"
$TableName = "invoices-$Environment"

Write-Host "🔧 Déploiement de l'outil d'extraction de factures" -ForegroundColor Cyan
Write-Host "Environnement: $Environment"
Write-Host "Région: $Region"
Write-Host "Stack CloudFormation: $StackName"

# Vérifier que AWS CLI est configuré
try {
    $CallerIdentity = aws sts get-caller-identity 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "AWS CLI non configuré"
    }
    Write-Host "✅ AWS CLI configuré" -ForegroundColor Green
} catch {
    Write-Host "❌ AWS CLI n'est pas configuré. Veuillez configurer vos credentials." -ForegroundColor Red
    exit 1
}

# Vérifier l'accès à Bedrock
Write-Host "🔍 Vérification de l'accès à AWS Bedrock..." -ForegroundColor Cyan
try {
    aws bedrock list-foundation-models --region $Region > $null 2>&1
    Write-Host "✅ Accès Bedrock OK" -ForegroundColor Green
} catch {
    Write-Host "⚠️  Attention: Impossible d'accéder à Bedrock. Vérifiez les permissions IAM." -ForegroundColor Yellow
    $Response = Read-Host "Continuer malgré tout? (y/n)"
    if ($Response -notmatch "^[Yy]$") {
        exit 1
    }
}

# Créer le package de déploiement
Write-Host "📦 Création du package de déploiement..." -ForegroundColor Cyan
Remove-Item -Path "package" -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Path "package" -Force > $null

# Installer les dépendances
Write-Host "📥 Installation des dépendances..." -ForegroundColor Cyan
pip install -r requirements.txt -t package/

# Copier le code source
Write-Host "📄 Copie du code source..." -ForegroundColor Cyan
Copy-Item -Path "src\*" -Destination "package\" -Recurse -Force
Copy-Item -Path "config\config.py" -Destination "package\config\" -Force

# Créer le fichier ZIP
Write-Host "🗜️  Création de l'archive ZIP..." -ForegroundColor Cyan
Compress-Archive -Path "package\*" -DestinationPath "invoice-extractor.zip" -Force

# Créer un bucket S3 pour le code Lambda
$AccountId = (aws sts get-caller-identity --query Account --output text).Trim()
$CodeBucket = "lambda-code-$Environment-$AccountId"
Write-Host "🪣 Création du bucket S3 pour le code: $CodeBucket" -ForegroundColor Cyan

try {
    aws s3api head-bucket --bucket $CodeBucket --region $Region 2>&1 > $null
    Write-Host "✅ Bucket S3 existe déjà" -ForegroundColor Green
} catch {
    aws s3 mb "s3://$CodeBucket" --region $Region
    Write-Host "✅ Bucket S3 créé" -ForegroundColor Green
}

# Uploader le code Lambda
Write-Host "⬆️  Upload du code Lambda..." -ForegroundColor Cyan
aws s3 cp invoice-extractor.zip "s3://$CodeBucket/" --region $Region

# Déployer avec CloudFormation
Write-Host "🚀 Déploiement avec CloudFormation..." -ForegroundColor Cyan

# Préparer les paramètres
$Parameters = @(
    "ParameterKey=EnvironmentName,ParameterValue=$Environment",
    "ParameterKey=BucketName,ParameterValue=$BucketName",
    "ParameterKey=TableName,ParameterValue=$TableName"
) -join " "

# Vérifier si la stack existe déjà
try {
    aws cloudformation describe-stacks --stack-name $StackName --region $Region 2>&1 > $null
    Write-Host "📝 Mise à jour de la stack existante..." -ForegroundColor Yellow
    aws cloudformation update-stack `
        --stack-name $StackName `
        --template-body file://cloudformation-template.yaml `
        --parameters $Parameters `
        --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM `
        --region $Region
    
    Write-Host "⏳ Attente de la mise à jour de la stack..." -ForegroundColor Cyan
    aws cloudformation wait stack-update-complete --stack-name $StackName --region $Region
} catch {
    Write-Host "🆕 Création d'une nouvelle stack..." -ForegroundColor Green
    aws cloudformation create-stack `
        --stack-name $StackName `
        --template-body file://cloudformation-template.yaml `
        --parameters $Parameters `
        --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM `
        --region $Region
    
    Write-Host "⏳ Attente de la création de la stack..." -ForegroundColor Cyan
    aws cloudformation wait stack-create-complete --stack-name $StackName --region $Region
}

# Récupérer le nom de la fonction Lambda
Write-Host "🔍 Récupération des informations de déploiement..." -ForegroundColor Cyan
$Outputs = aws cloudformation describe-stacks `
    --stack-name $StackName `
    --region $Region `
    --query "Stacks[0].Outputs" `
    --output json | ConvertFrom-Json

$LambdaFunctionName = ($Outputs | Where-Object { $_.OutputKey -eq "LambdaFunctionName" }).OutputValue

# Mettre à jour la fonction Lambda avec le vrai code
Write-Host "🔄 Mise à jour du code Lambda..." -ForegroundColor Cyan
aws lambda update-function-code `
    --function-name $LambdaFunctionName `
    --s3-bucket $CodeBucket `
    --s3-key invoice-extractor.zip `
    --region $Region

Write-Host "✅ Mise à jour du code Lambda terminée" -ForegroundColor Green

# Afficher les outputs
Write-Host ""
Write-Host "🎉 Déploiement terminé avec succès!" -ForegroundColor Green
Write-Host ""
Write-Host "📋 Outputs CloudFormation:" -ForegroundColor Cyan
aws cloudformation describe-stacks `
    --stack-name $StackName `
    --region $Region `
    --query "Stacks[0].Outputs" `
    --output table

Write-Host ""
Write-Host "🔗 URLs et informations:" -ForegroundColor Cyan
Write-Host "- Bucket S3 pour upload: $BucketName"
Write-Host "- Table DynamoDB: $TableName"
Write-Host "- Fonction Lambda: $LambdaFunctionName"
Write-Host ""
Write-Host "📤 Pour uploader une facture:" -ForegroundColor Yellow
Write-Host "aws s3 cp votre-facture.pdf s3://$BucketName/"
Write-Host ""
Write-Host "📊 Pour vérifier les données extraites:" -ForegroundColor Yellow
Write-Host "aws dynamodb scan --table-name $TableName --region $Region --max-items 10"
Write-Host ""
Write-Host "🧹 Pour nettoyer (supprimer toutes les ressources):" -ForegroundColor Yellow
Write-Host "aws cloudformation delete-stack --stack-name $StackName --region $Region"

# Nettoyer les fichiers temporaires
Remove-Item -Path "package" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -Path "invoice-extractor.zip" -Force -ErrorAction SilentlyContinue
Write-Host ""
Write-Host "🧽 Fichiers temporaires nettoyés" -ForegroundColor Green
