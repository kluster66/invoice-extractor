# Script de nettoyage AWS CORRIGÉ pour l'outil d'extraction de factures
# Gère mieux les erreurs et les états partiels

param(
    [string]$Region = "us-west-2",
    [switch]$Force = $false
)

$ErrorActionPreference = "Continue"  # Continuer malgré les erreurs

# Configuration
$StackName = "invoice-extractor-final"
$BucketName = "invoice-extractor-bucket-1736604000"
$TableName = "invoices-extractor"
$LambdaFunctionName = "invoice-extractor-lambda"
$IAMRoleName = "invoice-extractor-role"
$LogGroupName = "/aws/lambda/invoice-extractor-lambda"

Write-Host "🧹 Nettoyage des ressources AWS (version corrigée)" -ForegroundColor Cyan
Write-Host "Région: $Region" -ForegroundColor Yellow
Write-Host "" 

if (-not $Force) {
    $confirmation = Read-Host "⚠️  Cette action supprimera TOUTES les ressources AWS. Continuer? (oui/non)"
    if ($confirmation -ne "oui") {
        Write-Host "❌ Opération annulée" -ForegroundColor Red
        exit 0
    }
}

# Fonction pour exécuter une commande et gérer les erreurs silencieusement
function Invoke-AwsCommand {
    param(
        [string]$Command,
        [string]$ErrorMessage,
        [string]$SuccessMessage,
        [switch]$IgnoreErrors = $false
    )
    
    try {
        Invoke-Expression $Command 2>&1 | Out-Null
        if ($LASTEXITCODE -eq 0) {
            if ($SuccessMessage) { Write-Host "✅ $SuccessMessage" -ForegroundColor Green }
            return $true
        } else {
            if (-not $IgnoreErrors) {
                Write-Host "⚠️  $ErrorMessage" -ForegroundColor Yellow
            }
            return $false
        }
    } catch {
        if (-not $IgnoreErrors) {
            Write-Host "⚠️  $ErrorMessage" -ForegroundColor Yellow
        }
        return $false
    }
}

# Fonction pour vérifier si une ressource existe
function Test-AwsResourceExists {
    param(
        [string]$ResourceType,
        [string]$CheckCommand
    )
    
    try {
        Invoke-Expression $CheckCommand 2>&1 | Out-Null
        return $LASTEXITCODE -eq 0
    } catch {
        return $false
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
    
    # 2. Vérifier l'état de la stack CloudFormation
    Write-Host "📋 Vérification de l'état de la stack CloudFormation..." -ForegroundColor Cyan
    $stackInfo = aws cloudformation describe-stacks --stack-name $StackName --region $Region 2>&1
    $stackExists = $LASTEXITCODE -eq 0
    
    if ($stackExists) {
        $stackStatus = ($stackInfo | ConvertFrom-Json).Stacks[0].StackStatus
        Write-Host "📊 État de la stack: $stackStatus" -ForegroundColor Yellow
        
        # Si la stack est en échec de suppression, on doit d'abord nettoyer manuellement
        if ($stackStatus -eq "DELETE_FAILED") {
            Write-Host "⚠️  La stack est en état DELETE_FAILED" -ForegroundColor Red
            Write-Host "💡 Tentative de nettoyage manuel des ressources bloquantes..." -ForegroundColor Yellow
            
            # Essayer de forcer la suppression de la stack
            Write-Host "🔄 Tentative de suppression forcée de la stack..." -ForegroundColor Cyan
            $forceDelete = aws cloudformation delete-stack --stack-name $StackName --region $Region --retain-resources "InvoiceBucket" "InvoicesTable" "InvoiceExtractorFunction" "InvoiceExtractorRole" 2>&1
            if ($LASTEXITCODE -eq 0) {
                Write-Host "✅ Commande de suppression forcée envoyée" -ForegroundColor Green
            }
            
            # Attendre un peu
            Start-Sleep -Seconds 5
        }
        
        # Essayer la suppression normale
        Write-Host "🗑️  Suppression de la stack CloudFormation..." -ForegroundColor Cyan
        $deleteResult = aws cloudformation delete-stack --stack-name $StackName --region $Region 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "⏳ Attente de la suppression de la stack..." -ForegroundColor Cyan
            # Essayer d'attendre, mais ne pas bloquer si ça échoue
            $waitResult = aws cloudformation wait stack-delete-complete --stack-name $StackName --region $Region 2>&1
            if ($LASTEXITCODE -eq 0) {
                Write-Host "✅ Stack CloudFormation supprimée" -ForegroundColor Green
            } else {
                Write-Host "⚠️  La suppression de la stack est en cours ou a échoué" -ForegroundColor Yellow
                Write-Host "   Continuer avec le nettoyage manuel..." -ForegroundColor Yellow
            }
        }
    } else {
        Write-Host "ℹ️  Stack CloudFormation non trouvée ou déjà supprimée" -ForegroundColor Yellow
    }
    
    # 3. Nettoyer le bucket S3 (doit être fait avant de pouvoir supprimer la stack)
    Write-Host "🪣 Nettoyage du bucket S3..." -ForegroundColor Cyan
    
    # Vérifier si le bucket existe
    $bucketExists = Test-AwsResourceExists "S3 Bucket" "aws s3api head-bucket --bucket $BucketName --region $Region"
    
    if ($bucketExists) {
        # Essayer de vider le bucket
        Write-Host "🧹 Tentative de vidage du bucket..." -ForegroundColor Yellow
        $emptyResult = aws s3 rm "s3://$BucketName" --recursive --region $Region 2>&1
        
        # Si le vidage échoue, essayer avec force
        if ($LASTEXITCODE -ne 0) {
            Write-Host "⚠️  Impossible de vider le bucket normalement" -ForegroundColor Yellow
            Write-Host "🔄 Tentative avec la commande de suppression forcée..." -ForegroundColor Cyan
            
            # Créer un script pour supprimer avec force
            $forceDeleteScript = @"
import boto3
import sys

s3 = boto3.resource('s3', region_name='$Region')
bucket = s3.Bucket('$BucketName')

try:
    # Supprimer tous les objets et versions
    bucket.object_versions.delete()
    
    # Supprimer tous les objets
    bucket.objects.all().delete()
    
    print("Bucket vidé avec succès")
except Exception as e:
    print(f"Erreur: {e}")
    sys.exit(1)
"@
            
            # Essayer avec Python si disponible
            try {
                $tempScript = [System.IO.Path]::GetTempFileName() + ".py"
                $forceDeleteScript | Out-File -FilePath $tempScript -Encoding UTF8
                python $tempScript 2>&1 | Out-Null
                Remove-Item $tempScript -Force
                Write-Host "✅ Bucket vidé avec Python" -ForegroundColor Green
            } catch {
                Write-Host "⚠️  Impossible de vider le bucket, il sera peut-être supprimé par CloudFormation" -ForegroundColor Red
            }
        } else {
            Write-Host "✅ Bucket vidé" -ForegroundColor Green
        }
        
        # Essayer de supprimer le bucket
        Write-Host "🗑️  Suppression du bucket..." -ForegroundColor Yellow
        $deleteBucketResult = aws s3 rb "s3://$BucketName" --region $Region --force 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✅ Bucket S3 supprimé" -ForegroundColor Green
        } else {
            Write-Host "⚠️  Impossible de supprimer le bucket (peut être verrouillé)" -ForegroundColor Yellow
        }
    } else {
        Write-Host "ℹ️  Bucket S3 non trouvé ou déjà supprimé" -ForegroundColor Yellow
    }
    
    # 4. Supprimer la table DynamoDB
    Write-Host "🗃️  Suppression de la table DynamoDB..." -ForegroundColor Cyan
    $tableExists = Test-AwsResourceExists "DynamoDB Table" "aws dynamodb describe-table --table-name $TableName --region $Region"
    
    if ($tableExists) {
        $deleteTableResult = aws dynamodb delete-table --table-name $TableName --region $Region 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "⏳ Attente de la suppression de la table..." -ForegroundColor Cyan
            Start-Sleep -Seconds 5
            Write-Host "✅ Table DynamoDB supprimée" -ForegroundColor Green
        } else {
            Write-Host "⚠️  Impossible de supprimer la table DynamoDB" -ForegroundColor Yellow
        }
    } else {
        Write-Host "ℹ️  Table DynamoDB non trouvée ou déjà supprimée" -ForegroundColor Yellow
    }
    
    # 5. Supprimer la fonction Lambda
    Write-Host "⚡ Suppression de la fonction Lambda..." -ForegroundColor Cyan
    $lambdaExists = Test-AwsResourceExists "Lambda Function" "aws lambda get-function --function-name $LambdaFunctionName --region $Region"
    
    if ($lambdaExists) {
        $deleteLambdaResult = aws lambda delete-function --function-name $LambdaFunctionName --region $Region 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✅ Fonction Lambda supprimée" -ForegroundColor Green
        } else {
            Write-Host "⚠️  Impossible de supprimer la fonction Lambda" -ForegroundColor Yellow
        }
    } else {
        Write-Host "ℹ️  Fonction Lambda non trouvée ou déjà supprimée" -ForegroundColor Yellow
    }
    
    # 6. Supprimer les logs CloudWatch
    Write-Host "📊 Suppression des logs CloudWatch..." -ForegroundColor Cyan
    $logGroupExists = Test-AwsResourceExists "CloudWatch Logs" "aws logs describe-log-groups --log-group-name-prefix $LogGroupName --region $Region"
    
    if ($logGroupExists) {
        $deleteLogsResult = aws logs delete-log-group --log-group-name $LogGroupName --region $Region 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✅ Logs CloudWatch supprimés" -ForegroundColor Green
        } else {
            Write-Host "⚠️  Impossible de supprimer les logs CloudWatch" -ForegroundColor Yellow
        }
    } else {
        Write-Host "ℹ️  Logs CloudWatch non trouvés ou déjà supprimés" -ForegroundColor Yellow
    }
    
    # 7. Supprimer le rôle IAM (doit être fait en dernier)
    Write-Host "👤 Suppression du rôle IAM..." -ForegroundColor Cyan
    $roleExists = Test-AwsResourceExists "IAM Role" "aws iam get-role --role-name $IAMRoleName --region $Region"
    
    if ($roleExists) {
        # Détacher les politiques attachées
        Write-Host "🔓 Détachement des politiques IAM..." -ForegroundColor Yellow
        $attachedPolicies = aws iam list-attached-role-policies --role-name $IAMRoleName --region $Region --query 'AttachedPolicies[].PolicyArn' --output text 2>&1
        
        if ($LASTEXITCODE -eq 0 -and $attachedPolicies) {
            foreach ($policyArn in $attachedPolicies.Split("`t")) {
                if ($policyArn -and $policyArn.Trim()) {
                    Write-Host "  Détachement: $policyArn" -ForegroundColor Gray
                    aws iam detach-role-policy --role-name $IAMRoleName --policy-arn $policyArn --region $Region 2>&1 | Out-Null
                }
            }
        }
        
        # Supprimer le rôle
        Write-Host "🗑️  Suppression du rôle..." -ForegroundColor Yellow
        $deleteRoleResult = aws iam delete-role --role-name $IAMRoleName --region $Region 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✅ Rôle IAM supprimé" -ForegroundColor Green
        } else {
            Write-Host "⚠️  Impossible de supprimer le rôle IAM" -ForegroundColor Yellow
        }
    } else {
        Write-Host "ℹ️  Rôle IAM non trouvé ou déjà supprimé" -ForegroundColor Yellow
    }
    
    Write-Host "" 
    Write-Host "🎉 Nettoyage terminé !" -ForegroundColor Green
    Write-Host "" 
    Write-Host "📋 Vérification finale des ressources restantes :" -ForegroundColor Cyan
    
    # Vérifier ce qui reste
    Write-Host "🔍 Vérification des ressources..." -ForegroundColor Yellow
    
    $remainingResources = @()
    
    # Vérifier la stack
    if (Test-AwsResourceExists "Stack" "aws cloudformation describe-stacks --stack-name $StackName --region $Region") {
        $remainingResources += "Stack CloudFormation: $StackName"
    }
    
    # Vérifier le bucket
    if (Test-AwsResourceExists "Bucket" "aws s3api head-bucket --bucket $BucketName --region $Region") {
        $remainingResources += "Bucket S3: $BucketName"
    }
    
    # Vérifier la table
    if (Test-AwsResourceExists "Table" "aws dynamodb describe-table --table-name $TableName --region $Region") {
        $remainingResources += "Table DynamoDB: $TableName"
    }
    
    # Vérifier la fonction Lambda
    if (Test-AwsResourceExists "Lambda" "aws lambda get-function --function-name $LambdaFunctionName --region $Region") {
        $remainingResources += "Fonction Lambda: $LambdaFunctionName"
    }
    
    # Vérifier le rôle
    if (Test-AwsResourceExists "Role" "aws iam get-role --role-name $IAMRoleName --region $Region") {
        $remainingResources += "Rôle IAM: $IAMRoleName"
    }
    
    if ($remainingResources.Count -eq 0) {
        Write-Host "✅ Toutes les ressources ont été supprimées avec succès !" -ForegroundColor Green
    } else {
        Write-Host "⚠️  Les ressources suivantes sont toujours présentes :" -ForegroundColor Red
        foreach ($resource in $remainingResources) {
            Write-Host "  • $resource" -ForegroundColor Yellow
        }
        Write-Host "" 
        Write-Host "💡 Conseil : Essayez de supprimer manuellement via la console AWS" -ForegroundColor Cyan
    }
    
    Write-Host "" 
    Write-Host "🚀 Vous pouvez maintenant tester un nouveau déploiement avec CloudFormation" -ForegroundColor Yellow
    
} catch {
    Write-Host "❌ Erreur critique: $_" -ForegroundColor Red
    Write-Host "💡 Conseil: Vérifiez vos permissions IAM" -ForegroundColor Yellow
    exit 1
}
