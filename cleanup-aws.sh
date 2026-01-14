#!/bin/bash
# Script de nettoyage AWS pour l'outil d'extraction de factures
# Supprime toutes les ressources créées par CloudFormation

set -e

# Configuration
REGION="us-west-2"
STACK_NAME="invoice-extractor-final"
BUCKET_NAME="invoice-extractor-bucket-1736604000"
TABLE_NAME="invoices-extractor"
LAMBDA_FUNCTION_NAME="invoice-extractor-lambda"
IAM_ROLE_NAME="invoice-extractor-role"
LOG_GROUP_NAME="/aws/lambda/invoice-extractor-lambda"

echo "🧹 Nettoyage des ressources AWS pour l'outil d'extraction de factures"
echo "Région: $REGION"
echo ""

# Demander confirmation
read -p "⚠️  Cette action supprimera TOUTES les ressources AWS. Continuer? (oui/non): " CONFIRMATION
if [[ "$CONFIRMATION" != "oui" ]]; then
    echo "❌ Opération annulée"
    exit 0
fi

# Fonction pour vérifier si une commande a réussi
check_command() {
    if [ $? -ne 0 ]; then
        echo "ℹ️  $1 non trouvé(e) ou déjà supprimé(e)"
        return 1
    fi
    return 0
}

echo "🔍 Vérification de la configuration AWS..."
aws sts get-caller-identity > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "❌ AWS CLI non configuré ou credentials invalides"
    exit 1
fi
echo "✅ AWS CLI configuré"

# 1. Supprimer la stack CloudFormation
echo "🗑️  Suppression de la stack CloudFormation: $STACK_NAME..."
if aws cloudformation describe-stacks --stack-name "$STACK_NAME" --region "$REGION" > /dev/null 2>&1; then
    echo "📋 Stack trouvée, suppression en cours..."
    aws cloudformation delete-stack --stack-name "$STACK_NAME" --region "$REGION"
    echo "⏳ Attente de la suppression de la stack..."
    aws cloudformation wait stack-delete-complete --stack-name "$STACK_NAME" --region "$REGION"
    echo "✅ Stack CloudFormation supprimée"
else
    echo "ℹ️  Stack CloudFormation non trouvée ou déjà supprimée"
fi

# 2. Vider et supprimer le bucket S3
echo "🪣 Nettoyage du bucket S3: $BUCKET_NAME..."
if aws s3api head-bucket --bucket "$BUCKET_NAME" --region "$REGION" > /dev/null 2>&1; then
    echo "🧹 Vidage du bucket..."
    aws s3 rm "s3://$BUCKET_NAME" --recursive --region "$REGION" > /dev/null 2>&1 || true
    
    echo "🗑️  Suppression du bucket..."
    aws s3 rb "s3://$BUCKET_NAME" --region "$REGION" --force
    echo "✅ Bucket S3 supprimé"
else
    echo "ℹ️  Bucket S3 non trouvé ou déjà supprimé"
fi

# 3. Supprimer la table DynamoDB
echo "🗃️  Suppression de la table DynamoDB: $TABLE_NAME..."
if aws dynamodb describe-table --table-name "$TABLE_NAME" --region "$REGION" > /dev/null 2>&1; then
    aws dynamodb delete-table --table-name "$TABLE_NAME" --region "$REGION"
    echo "⏳ Attente de la suppression de la table..."
    sleep 10
    echo "✅ Table DynamoDB supprimée"
else
    echo "ℹ️  Table DynamoDB non trouvée ou déjà supprimée"
fi

# 4. Supprimer la fonction Lambda
echo "⚡ Suppression de la fonction Lambda: $LAMBDA_FUNCTION_NAME..."
if aws lambda get-function --function-name "$LAMBDA_FUNCTION_NAME" --region "$REGION" > /dev/null 2>&1; then
    aws lambda delete-function --function-name "$LAMBDA_FUNCTION_NAME" --region "$REGION"
    echo "✅ Fonction Lambda supprimée"
else
    echo "ℹ️  Fonction Lambda non trouvée ou déjà supprimée"
fi

# 5. Supprimer les logs CloudWatch
echo "📊 Suppression des logs CloudWatch: $LOG_GROUP_NAME..."
if aws logs describe-log-groups --log-group-name-prefix "$LOG_GROUP_NAME" --region "$REGION" > /dev/null 2>&1; then
    aws logs delete-log-group --log-group-name "$LOG_GROUP_NAME" --region "$REGION"
    echo "✅ Logs CloudWatch supprimés"
else
    echo "ℹ️  Logs CloudWatch non trouvés ou déjà supprimés"
fi

# 6. Supprimer le rôle IAM
echo "👤 Suppression du rôle IAM: $IAM_ROLE_NAME..."
if aws iam get-role --role-name "$IAM_ROLE_NAME" --region "$REGION" > /dev/null 2>&1; then
    echo "🔓 Détachement des politiques IAM..."
    
    # Détacher toutes les politiques attachées
    ATTACHED_POLICIES=$(aws iam list-attached-role-policies --role-name "$IAM_ROLE_NAME" --region "$REGION" --query 'AttachedPolicies[].PolicyArn' --output text)
    
    for POLICY_ARN in $ATTACHED_POLICIES; do
        if [ -n "$POLICY_ARN" ]; then
            echo "  Détachement: $POLICY_ARN"
            aws iam detach-role-policy --role-name "$IAM_ROLE_NAME" --policy-arn "$POLICY_ARN" --region "$REGION" || true
        fi
    done
    
    echo "🗑️  Suppression du rôle..."
    aws iam delete-role --role-name "$IAM_ROLE_NAME" --region "$REGION"
    echo "✅ Rôle IAM supprimé"
else
    echo "ℹ️  Rôle IAM non trouvé ou déjà supprimé"
fi

echo ""
echo "🎉 Nettoyage terminé avec succès !"
echo ""
echo "📋 Résumé des ressources supprimées :"
echo "  • Stack CloudFormation: $STACK_NAME"
echo "  • Bucket S3: $BUCKET_NAME"
echo "  • Table DynamoDB: $TABLE_NAME"
echo "  • Fonction Lambda: $LAMBDA_FUNCTION_NAME"
echo "  • Rôle IAM: $IAM_ROLE_NAME"
echo "  • Logs CloudWatch: $LOG_GROUP_NAME"
echo ""
echo "🚀 Vous pouvez maintenant tester un nouveau déploiement avec CloudFormation"
