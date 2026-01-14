# Script de nettoyage AWS SIMPLE et ROBUSTE
# Supprime tout en gérant les erreurs silencieusement

param(
    [string]$Region = "us-west-2"
)

Write-Host "🧹 Nettoyage AWS Simple - Région: $Region" -ForegroundColor Cyan
Write-Host "Ce script supprime TOUTES les ressources liées à invoice-extractor" -ForegroundColor Yellow
Write-Host "" 

$confirmation = Read-Host "⚠️  Continuer? (oui/non)"
if ($confirmation -ne "oui") {
    Write-Host "❌ Opération annulée" -ForegroundColor Red
    exit 0
}

# Configuration des ressources
$resources = @{
    "Stack CloudFormation" = @{
        Name = "invoice-extractor-final"
        DeleteCommand = "aws cloudformation delete-stack --stack-name invoice-extractor-final --region $Region"
        CheckCommand = "aws cloudformation describe-stacks --stack-name invoice-extractor-final --region $Region 2>&1 | Out-Null"
    }
    "Bucket S3" = @{
        Name = "invoice-extractor-bucket-1736604000"
        DeleteCommand = "aws s3 rb s3://invoice-extractor-bucket-1736604000 --region $Region --force 2>&1"
        CheckCommand = "aws s3api head-bucket --bucket invoice-extractor-bucket-1736604000 --region $Region 2>&1 | Out-Null"
        PreDelete = "aws s3 rm s3://invoice-extractor-bucket-1736604000 --recursive --region $Region 2>&1 | Out-Null"
    }
    "Table DynamoDB" = @{
        Name = "invoices-extractor"
        DeleteCommand = "aws dynamodb delete-table --table-name invoices-extractor --region $Region 2>&1"
        CheckCommand = "aws dynamodb describe-table --table-name invoices-extractor --region $Region 2>&1 | Out-Null"
    }
    "Fonction Lambda" = @{
        Name = "invoice-extractor-lambda"
        DeleteCommand = "aws lambda delete-function --function-name invoice-extractor-lambda --region $Region 2>&1"
        CheckCommand = "aws lambda get-function --function-name invoice-extractor-lambda --region $Region 2>&1 | Out-Null"
    }
    "Logs CloudWatch" = @{
        Name = "/aws/lambda/invoice-extractor-lambda"
        DeleteCommand = "aws logs delete-log-group --log-group-name /aws/lambda/invoice-extractor-lambda --region $Region 2>&1"
        CheckCommand = "aws logs describe-log-groups --log-group-name-prefix /aws/lambda/invoice-extractor-lambda --region $Region 2>&1 | Out-Null"
    }
    "Rôle IAM" = @{
        Name = "invoice-extractor-role"
        DeleteCommand = {
            # D'abord détacher toutes les politiques
            $policies = aws iam list-attached-role-policies --role-name invoice-extractor-role --region $Region --query 'AttachedPolicies[].PolicyArn' --output text 2>&1
            if ($LASTEXITCODE -eq 0 -and $policies) {
                foreach ($policy in $policies.Split("`t")) {
                    if ($policy) {
                        aws iam detach-role-policy --role-name invoice-extractor-role --policy-arn $policy --region $Region 2>&1 | Out-Null
                    }
                }
            }
            # Puis supprimer le rôle
            aws iam delete-role --role-name invoice-extractor-role --region $Region 2>&1
        }
        CheckCommand = "aws iam get-role --role-name invoice-extractor-role --region $Region 2>&1 | Out-Null"
    }
}

# Vérifier AWS CLI
Write-Host "🔍 Vérification AWS CLI..." -ForegroundColor Cyan
aws sts get-caller-identity 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ AWS CLI non configuré" -ForegroundColor Red
    exit 1
}
Write-Host "✅ AWS CLI OK" -ForegroundColor Green

# Nettoyer chaque ressource
foreach ($resourceType in $resources.Keys) {
    $resource = $resources[$resourceType]
    Write-Host "`n🔧 Traitement: $resourceType ($($resource.Name))..." -ForegroundColor Cyan
    
    # Vérifier si la ressource existe
    Invoke-Expression $resource.CheckCommand
    $exists = $LASTEXITCODE -eq 0
    
    if (-not $exists) {
        Write-Host "  ℹ️  Non trouvé(e) ou déjà supprimé(e)" -ForegroundColor Gray
        continue
    }
    
    Write-Host "  ✅ Existe, suppression en cours..." -ForegroundColor Yellow
    
    # Pré-nettoyage si défini (pour S3)
    if ($resource.PreDelete) {
        Write-Host "  🧹 Pré-nettoyage..." -ForegroundColor Gray
        Invoke-Expression $resource.PreDelete | Out-Null
    }
    
    # Suppression
    try {
        if ($resource.DeleteCommand -is [scriptblock]) {
            # Pour le rôle IAM qui a un scriptblock
            & $resource.DeleteCommand
        } else {
            Invoke-Expression $resource.DeleteCommand
        }
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  ✅ Supprimé(e) avec succès" -ForegroundColor Green
        } else {
            Write-Host "  ⚠️  Échec de suppression (peut être verrouillé)" -ForegroundColor Yellow
        }
    } catch {
        Write-Host "  ⚠️  Erreur: $_" -ForegroundColor Yellow
    }
    
    # Petite pause entre les suppressions
    Start-Sleep -Milliseconds 500
}

Write-Host "`n🎉 Nettoyage terminé !" -ForegroundColor Green
Write-Host "`n📋 Vérification finale..." -ForegroundColor Cyan

# Vérifier ce qui reste
$remaining = @()
foreach ($resourceType in $resources.Keys) {
    $resource = $resources[$resourceType]
    Invoke-Expression $resource.CheckCommand
    if ($LASTEXITCODE -eq 0) {
        $remaining += "$resourceType ($($resource.Name))"
    }
}

if ($remaining.Count -eq 0) {
    Write-Host "✅ Toutes les ressources ont été supprimées !" -ForegroundColor Green
} else {
    Write-Host "⚠️  Ressources restantes :" -ForegroundColor Red
    foreach ($item in $remaining) {
        Write-Host "  • $item" -ForegroundColor Yellow
    }
    Write-Host "`n💡 Essayez de supprimer manuellement via la console AWS" -ForegroundColor Cyan
}

Write-Host "`n🚀 Prêt pour un nouveau déploiement !" -ForegroundColor Yellow
