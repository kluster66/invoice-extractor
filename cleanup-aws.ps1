# Script de nettoyage AWS pour l'outil d'extraction de factures
# Supprime toutes les ressources créées par CloudFormation

param(
    [string]$Region = "us-west-2",
    [switch]$Force = $false
)

$ErrorActionPreference = "Stop"

# Configuration
$StackName = "invoice-extractor-final"
$BucketName = "invoice-extractor-bucket-1736604000"
$TableName = "invoices-extractor"
$LambdaFunctionName = "invoice-extractor-lambda"
$IAMRoleName = "invoice-extractor-role"
$LogGroupName = "/aws/lambda/invoice-extractor-lambda"

Write-Host "🧹 Nettoyage des ressources AWS pour l'outil d'extraction de factures" -ForegroundColor Cyan
Write-Host "Région: $Region" -ForegroundColor Yellow
Write-Host "" 

if (-not $Force) {
    $confirmation = Read-Host "⚠️  Cette action supprimera TOUTES les ressources AWS. Continuer? (oui/non)"
    if ($confirmation -ne "oui") {
        Write-Host "❌ Opération annulée" -ForegroundColor Red
        exit 0
    }
}

try {
    # 1. Vérifier que AWS CLI est configuré
    Write-Host "🔍 Vérification de la configuration AWS..." -ForegroundColor Cyan
    $CallerIdentity = aws sts get-caller-identity 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "AWS CLI non configuré ou credentials invalides"
    }
    Write-Host "✅ AWS CLI configuré" -ForegroundColor Green
    
    # 2. Supprimer la stack CloudFormation (cela supprime automatiquement certaines ressources)
    Write-Host "🗑️  Suppression de la stack CloudFormation: $StackName..." -ForegroundColor Cyan
    try {
        aws cloudformation describe-stacks --stack-name $StackName --region $Region 2>&1 > $null
        Write-Host "📋 Stack trouvée, suppression en cours..." -ForegroundColor Yellow
        
        aws cloudformation delete-stack --stack-name $StackName --region $Region
        Write-Host "⏳ Attente de la suppression de la stack..." -ForegroundColor Cyan
        aws cloudformation wait stack-delete-complete --stack-name $StackName --region $Region
        Write-Host "✅ Stack CloudFormation supprimée" -ForegroundColor Green
    } catch {
        Write-Host "ℹ️  Stack CloudFormation non trouvée ou déjà supprimée" -ForegroundColor Yellow
    }
    
    # 3. Vider et supprimer le bucket S3 (CloudFormation ne le fait pas automatiquement)
    Write-Host "🪣 Nettoyage du bucket S3: $BucketName..." -ForegroundColor Cyan
    try {
        # Vérifier si le bucket existe
        aws s3api head-bucket --bucket $BucketName --region $Region 2>&1 > $null
        
        # Vider le bucket
        Write-Host "🧹 Vidage du bucket..." -ForegroundColor Yellow
        aws s3 rm "s3://$BucketName" --recursive --region $Region 2>&1 > $null
        
        # Supprimer le bucket
        Write-Host "🗑️  Suppression du bucket..." -ForegroundColor Yellow
        aws s3 rb "s3://$BucketName" --region $Region --force
        Write-Host "✅ Bucket S3 supprimé" -ForegroundColor Green
    } catch {
        Write-Host "ℹ️  Bucket S3 non trouvé ou déjà supprimé" -ForegroundColor Yellow
    }
    
    # 4. Supprimer la table DynamoDB
    Write-Host "🗃️  Suppression de la table DynamoDB: $TableName..." -ForegroundColor Cyan
    try {
        aws dynamodb describe-table --table-name $TableName --region $Region 2>&1 > $null
        aws dynamodb delete-table --table-name $TableName --region $Region
        Write-Host "⏳ Attente de la suppression de la table..." -ForegroundColor Cyan
        # Attendre que la table soit supprimée
        Start-Sleep -Seconds 10
        Write-Host "✅ Table DynamoDB supprimée" -ForegroundColor Green
    } catch {
        Write-Host "ℹ️  Table DynamoDB non trouvée ou déjà supprimée" -ForegroundColor Yellow
    }
    
    # 5. Supprimer la fonction Lambda
    Write-Host "⚡ Suppression de la fonction Lambda: $LambdaFunctionName..." -ForegroundColor Cyan
    try {
        aws lambda get-function --function-name $LambdaFunctionName --region $Region 2>&1 > $null
        aws lambda delete-function --function-name $LambdaFunctionName --region $Region
        Write-Host "✅ Fonction Lambda supprimée" -ForegroundColor Green
    } catch {
        Write-Host "ℹ️  Fonction Lambda non trouvée ou déjà supprimée" -ForegroundColor Yellow
    }
    
    # 6. Supprimer les logs CloudWatch
    Write-Host "📊 Suppression des logs CloudWatch: $LogGroupName..." -ForegroundColor Cyan
    try {
        aws logs describe-log-groups --log-group-name-prefix $LogGroupName --region $Region 2>&1 > $null
        aws logs delete-log-group --log-group-name $LogGroupName --region $Region
        Write-Host "✅ Logs CloudWatch supprimés" -ForegroundColor Green
    } catch {
        Write-Host "ℹ️  Logs CloudWatch non trouvés ou déjà supprimés" -ForegroundColor Yellow
    }
    
    # 7. Supprimer le rôle IAM (doit être fait après les autres ressources)
    Write-Host "👤 Suppression du rôle IAM: $IAMRoleName..." -ForegroundColor Cyan
    try {
        # Vérifier si le rôle existe
        aws iam get-role --role-name $IAMRoleName --region $Region 2>&1 > $null
        
        # Détacher les politiques attachées
        Write-Host "🔓 Détachement des politiques IAM..." -ForegroundColor Yellow
        $attachedPolicies = aws iam list-attached-role-policies --role-name $IAMRoleName --region $Region --query 'AttachedPolicies[].PolicyArn' --output text
        
        foreach ($policyArn in $attachedPolicies) {
            if ($policyArn) {
                Write-Host "  Détachement: $policyArn" -ForegroundColor Gray
                aws iam detach-role-policy --role-name $IAMRoleName --policy-arn $policyArn --region $Region
            }
        }
        
        # Supprimer le rôle
        Write-Host "🗑️  Suppression du rôle..." -ForegroundColor Yellow
        aws iam delete-role --role-name $IAMRoleName --region $Region
        Write-Host "✅ Rôle IAM supprimé" -ForegroundColor Green
    } catch {
        Write-Host "ℹ️  Rôle IAM non trouvé ou déjà supprimé" -ForegroundColor Yellow
    }
    
    Write-Host "" 
    Write-Host "🎉 Nettoyage terminé avec succès !" -ForegroundColor Green
    Write-Host "" 
    Write-Host "📋 Résumé des ressources supprimées :" -ForegroundColor Cyan
    Write-Host "  • Stack CloudFormation: $StackName" -ForegroundColor White
    Write-Host "  • Bucket S3: $BucketName" -ForegroundColor White
    Write-Host "  • Table DynamoDB: $TableName" -ForegroundColor White
    Write-Host "  • Fonction Lambda: $LambdaFunctionName" -ForegroundColor White
    Write-Host "  • Rôle IAM: $IAMRoleName" -ForegroundColor White
    Write-Host "  • Logs CloudWatch: $LogGroupName" -ForegroundColor White
    Write-Host "" 
    Write-Host "🚀 Vous pouvez maintenant tester un nouveau déploiement avec CloudFormation" -ForegroundColor Yellow
    
} catch {
    Write-Host "❌ Erreur lors du nettoyage: $_" -ForegroundColor Red
    Write-Host "💡 Conseil: Vérifiez vos permissions IAM et que les ressources existent" -ForegroundColor Yellow
    exit 1
}
