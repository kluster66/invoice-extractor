# Script PowerShell non-interactif pour créer la stack CloudFormation

$timestamp = Get-Date -UFormat %s
$bucketName = "invoice-extractor-bucket-$timestamp"
$stackName = "invoice-extractor-stack"
$region = "us-west-2"

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "CREATION DE LA STACK CLOUDFORMATION" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Stack: $stackName" -ForegroundColor Yellow
Write-Host "Region: $region" -ForegroundColor Yellow
Write-Host "Bucket: $bucketName" -ForegroundColor Yellow
Write-Host "Modele: meta.llama3-1-70b-instruct-v1:0" -ForegroundColor Yellow
Write-Host ""

Write-Host "Creation de la stack en cours..." -ForegroundColor Green

# Créer la stack
$result = aws cloudformation create-stack `
    --stack-name $stackName `
    --template-body file://cloudformation-template-simple.yaml `
    --parameters `
        ParameterKey=EnvironmentName,ParameterValue=prod `
        ParameterKey=BucketName,ParameterValue=$bucketName `
        ParameterKey=TableName,ParameterValue=invoices `
        ParameterKey=BedrockModelId,ParameterValue=meta.llama3-1-70b-instruct-v1:0 `
    --capabilities CAPABILITY_IAM `
    --region $region `
    --tags Key=Project,Value=InvoiceExtractor Key=Environment,Value=Production

if ($LASTEXITCODE -eq 0) {
    Write-Host "`nStack creee avec succes !" -ForegroundColor Green
    Write-Host "Verification du statut..." -ForegroundColor Yellow
    
    # Attendre et vérifier le statut
    $maxAttempts = 60
    for ($i = 1; $i -le $maxAttempts; $i++) {
        Write-Host "Verification... tentative $i/$maxAttempts" -ForegroundColor Gray
        
        $stackInfo = aws cloudformation describe-stacks --stack-name $stackName --region $region 2>$null | ConvertFrom-Json
        
        if ($stackInfo -and $stackInfo.Stacks) {
            $status = $stackInfo.Stacks[0].StackStatus
            Write-Host "Statut: $status" -ForegroundColor Yellow
            
            if ($status -eq "CREATE_COMPLETE") {
                Write-Host "`n✅ Stack creee avec succes !" -ForegroundColor Green
                
                # Afficher les outputs
                if ($stackInfo.Stacks[0].Outputs) {
                    Write-Host "`nOutputs:" -ForegroundColor Cyan
                    foreach ($output in $stackInfo.Stacks[0].Outputs) {
                        Write-Host "  $($output.OutputKey): $($output.OutputValue)" -ForegroundColor White
                    }
                }
                
                Write-Host "`n✅ Deploiement termine !" -ForegroundColor Green
                exit 0
            }
            elseif ($status -match "FAILED|ROLLBACK") {
                Write-Host "`n❌ Stack en echec: $status" -ForegroundColor Red
                
                # Afficher les evenements d'erreur
                Write-Host "`nEvenements recents:" -ForegroundColor Red
                aws cloudformation describe-stack-events --stack-name $stackName --region $region --max-items 10 | ConvertFrom-Json | Select-Object -First 5 StackEvents | ForEach-Object {
                    Write-Host "  $($_.LogicalResourceId): $($_.ResourceStatus) - $($_.ResourceStatusReason)" -ForegroundColor Red
                }
                exit 1
            }
        }
        
        Start-Sleep -Seconds 30
    }
    
    Write-Host "`n❌ Timeout lors de l'attente de la stack" -ForegroundColor Red
    exit 1
} else {
    Write-Host "`n❌ Erreur lors de la creation de la stack" -ForegroundColor Red
    Write-Host "Erreur: $result" -ForegroundColor Red
    exit 1
}
