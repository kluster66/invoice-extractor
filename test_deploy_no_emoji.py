#!/usr/bin/env python3
"""
Script de test de déploiement CloudFormation - version sans émojis
"""

import subprocess
import sys
import json
import os

def run_command(command, description=None):
    """Exécute une commande shell et retourne le résultat."""
    if description:
        print(f"\n{description}...")
    
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='ignore'
        )
        
        if result.returncode != 0:
            print(f"ERREUR: Commande échouée")
            if result.stderr:
                print(f"Details: {result.stderr[:500]}")
            return False, result.stderr
        
        return True, result.stdout
    
    except Exception as e:
        print(f"Exception: {e}")
        return False, str(e)

def check_aws_cli():
    """Vérifie que AWS CLI est configuré."""
    print("1. Verification de la configuration AWS...")
    
    success, output = run_command("aws sts get-caller-identity")
    if not success:
        print("ERREUR: AWS CLI n'est pas configuré")
        return False
    
    try:
        identity = json.loads(output)
        account_id = identity.get('Account', 'N/A')
        print(f"OK: AWS CLI configuré - Compte: {account_id}")
        return True
    except:
        print("OK: AWS CLI configuré")
        return True

def validate_template():
    """Valide le template CloudFormation."""
    print("\n2. Validation du template CloudFormation...")
    
    template_path = "cloudformation-template-final.yaml"
    if not os.path.exists(template_path):
        print(f"ERREUR: Template non trouvé: {template_path}")
        return False
    
    success, output = run_command(
        f"aws cloudformation validate-template --template-body file://{template_path} --region us-west-2"
    )
    
    if success:
        print("OK: Template CloudFormation valide")
        return True
    else:
        print("ERREUR: Template CloudFormation invalide")
        return False

def check_bedrock_access():
    """Vérifie l'accès à AWS Bedrock."""
    print("\n3. Verification de l'accès à AWS Bedrock...")
    
    success, output = run_command(
        "aws bedrock list-foundation-models --region us-west-2 --query 'modelSummaries[].modelId' --output json"
    )
    
    if success:
        try:
            models = json.loads(output)
            if models:
                print(f"OK: Accès Bedrock - {len(models)} modèles disponibles")
                return True
            else:
                print("ATTENTION: Aucun modèle Bedrock trouvé")
                return False
        except:
            print("OK: Accès Bedrock")
            return True
    else:
        print("ATTENTION: Impossible d'accéder à Bedrock")
        print("Conseil: Activez Bedrock dans la console AWS")
        return True

def create_lambda_package():
    """Crée le package ZIP pour la fonction Lambda."""
    print("\n4. Creation du package Lambda...")
    
    # Créer un répertoire temporaire pour le package
    package_dir = "lambda_package_deploy"
    
    try:
        # Nettoyer l'ancien package
        if os.path.exists(package_dir):
            import shutil
            shutil.rmtree(package_dir)
        
        # Créer le répertoire
        os.makedirs(package_dir, exist_ok=True)
        
        # Copier le code source depuis src_propre
        src_dir = "src_propre"
        if not os.path.exists(src_dir):
            print(f"ERREUR: Répertoire source non trouvé: {src_dir}")
            return False, None
        
        import shutil
        for item in os.listdir(src_dir):
            src_path = os.path.join(src_dir, item)
            dst_path = os.path.join(package_dir, item)
            
            if os.path.isfile(src_path):
                shutil.copy2(src_path, dst_path)
            elif os.path.isdir(src_path):
                shutil.copytree(src_path, dst_path, dirs_exist_ok=True)
        
        print(f"OK: Code source copié depuis {src_dir}")
        
        # Créer le fichier ZIP
        import zipfile
        zip_path = "invoice-extractor-lambda.zip"
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(package_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, package_dir)
                    zipf.write(file_path, arcname)
        
        file_size = os.path.getsize(zip_path) / 1024 / 1024
        print(f"OK: Package ZIP créé: {zip_path} ({file_size:.2f} MB)")
        
        # Nettoyer
        shutil.rmtree(package_dir)
        
        return True, zip_path
    
    except Exception as e:
        print(f"ERREUR: Création du package: {e}")
        return False, None

def check_stack_exists():
    """Vérifie si la stack existe déjà."""
    print("\n5. Verification de l'existence de la stack...")
    
    stack_name = "invoice-extractor"
    
    success, output = run_command(
        f"aws cloudformation describe-stacks --stack-name {stack_name} --region us-west-2"
    )
    
    if success:
        print(f"ATTENTION: La stack '{stack_name}' existe déjà")
        return True
    else:
        print(f"OK: La stack '{stack_name}' n'existe pas")
        return False

def main():
    """Fonction principale."""
    print("=" * 60)
    print("TEST DE DEPLOIEMENT CLOUDFORMATION")
    print("=" * 60)
    
    # Exécuter les vérifications
    print("\nEXECUTION DES VERIFICATIONS...")
    
    # 1. Vérifier AWS CLI
    if not check_aws_cli():
        return 1
    
    # 2. Valider le template
    if not validate_template():
        return 1
    
    # 3. Vérifier Bedrock
    check_bedrock_access()
    
    # 4. Créer le package
    success, zip_path = create_lambda_package()
    if not success:
        return 1
    
    # 5. Vérifier si la stack existe
    stack_exists = check_stack_exists()
    
    if stack_exists:
        print("\nATTENTION: La stack existe déjà")
        print("Pour déployer à nouveau, vous devez d'abord la supprimer:")
        print("  aws cloudformation delete-stack --stack-name invoice-extractor --region us-west-2")
        print("\nOu utiliser le script de nettoyage:")
        print("  .\\cleanup-aws-simple.ps1")
    else:
        print("\nTOUTES LES VERIFICATIONS SONT OK")
        print("\nPour déployer la stack, exécutez:")
        print("  aws cloudformation create-stack ^")
        print("    --stack-name invoice-extractor ^")
        print("    --template-body file://cloudformation-template-final.yaml ^")
        print("    --parameters ParameterKey=EnvironmentName,ParameterValue=prod ^")
        print("                  ParameterKey=BedrockModelId,ParameterValue=meta.llama3-1-70b-instruct-v1:0 ^")
        print("    --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM ^")
        print("    --region us-west-2")
    
    print("\n" + "=" * 60)
    print("RESUME:")
    print(f"- Package Lambda créé: {zip_path}")
    print("- Template CloudFormation valide")
    print("- AWS CLI configuré")
    print("- Région: us-west-2")
    print("=" * 60)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
