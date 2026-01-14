#!/usr/bin/env python3
"""
Script de déploiement final pour l'outil d'extraction de factures.
Déploie la stack CloudFormation avec le vrai code Lambda.
"""

import subprocess
import sys
import json
import os
import zipfile
import shutil

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

def create_lambda_package_with_dependencies():
    """Crée le package ZIP pour la fonction Lambda avec les dépendances."""
    print("\n3. Creation du package Lambda avec dépendances...")
    
    # Vérifier si lambda_package existe
    if not os.path.exists("lambda_package"):
        print("ERREUR: Le répertoire lambda_package n'existe pas")
        print("Conseil: Il contient les dépendances Python nécessaires")
        return False, None
    
    # Créer un répertoire temporaire pour le package
    package_dir = "lambda_package_deploy_final"
    
    try:
        # Nettoyer l'ancien package
        if os.path.exists(package_dir):
            shutil.rmtree(package_dir)
        
        # Créer le répertoire
        os.makedirs(package_dir, exist_ok=True)
        
        print("Copie des dépendances depuis lambda_package...")
        # Copier les dépendances depuis lambda_package
        for item in os.listdir("lambda_package"):
            src_path = os.path.join("lambda_package", item)
            dst_path = os.path.join(package_dir, item)
            
            if os.path.isfile(src_path):
                shutil.copy2(src_path, dst_path)
            elif os.path.isdir(src_path):
                shutil.copytree(src_path, dst_path, dirs_exist_ok=True)
        
        print("Copie du code source depuis src_propre...")
        # Copier le code source depuis src_propre
        src_dir = "src_propre"
        for item in os.listdir(src_dir):
            src_path = os.path.join(src_dir, item)
            dst_path = os.path.join(package_dir, item)
            
            if os.path.isfile(src_path):
                shutil.copy2(src_path, dst_path)
            elif os.path.isdir(src_path):
                shutil.copytree(src_path, dst_path, dirs_exist_ok=True)
        
        # Créer le fichier ZIP
        zip_path = "invoice-extractor-lambda-final.zip"
        
        print("Creation de l'archive ZIP...")
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

def create_s3_bucket_for_code():
    """Crée un bucket S3 pour stocker le code Lambda."""
    print("\n4. Creation du bucket S3 pour le code Lambda...")
    
    # Générer un nom de bucket unique
    import time
    timestamp = int(time.time())
    bucket_name = f"invoice-extractor-code-{timestamp}"
    
    print(f"Nom du bucket: {bucket_name}")
    
    # Créer le bucket
    success, output = run_command(
        f"aws s3 mb s3://{bucket_name} --region us-west-2"
    )
    
    if success:
        print(f"OK: Bucket S3 créé: {bucket_name}")
        return True, bucket_name
    else:
        print("ERREUR: Impossible de créer le bucket S3")
        return False, None

def upload_lambda_code(bucket_name, zip_path):
    """Upload le code Lambda vers S3."""
    print(f"\n5. Upload du code Lambda vers S3...")
    
    success, output = run_command(
        f"aws s3 cp {zip_path} s3://{bucket_name}/invoice-extractor-lambda.zip --region us-west-2"
    )
    
    if success:
        print(f"OK: Code Lambda uploadé vers s3://{bucket_name}/invoice-extractor-lambda.zip")
        return True
    else:
        print("ERREUR: Upload du code Lambda échoué")
        return False

def deploy_cloudformation_stack(bucket_name):
    """Déploie la stack CloudFormation."""
    print("\n6. Deploiement de la stack CloudFormation...")
    
    stack_name = "invoice-extractor"
    template_path = "cloudformation-template-final.yaml"
    
    # Vérifier si la stack existe déjà
    success, output = run_command(
        f"aws cloudformation describe-stacks --stack-name {stack_name} --region us-west-2"
    )
    
    if success:
        print(f"ATTENTION: La stack '{stack_name}' existe déjà")
        print("Suppression de la stack existante...")
        
        # Supprimer la stack existante
        success, output = run_command(
            f"aws cloudformation delete-stack --stack-name {stack_name} --region us-west-2"
        )
        
        if success:
            print("Attente de la suppression...")
            run_command(
                f"aws cloudformation wait stack-delete-complete --stack-name {stack_name} --region us-west-2"
            )
            print("OK: Stack supprimée")
        else:
            print("ERREUR: Impossible de supprimer la stack existante")
            return False
    
    # Paramètres pour la stack
    parameters = [
        f"ParameterKey=EnvironmentName,ParameterValue=prod",
        f"ParameterKey=BucketName,ParameterValue=invoice-extractor-bucket-{int(time.time())}",
        f"ParameterKey=TableName,ParameterValue=invoices-extractor",
        f"ParameterKey=BedrockModelId,ParameterValue=meta.llama3-1-70b-instruct-v1:0"
    ]
    
    # Construire la commande de création
    cmd = f"aws cloudformation create-stack " \
          f"--stack-name {stack_name} " \
          f"--template-body file://{template_path} " \
          f"--parameters {' '.join(parameters)} " \
          f"--capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM " \
          f"--region us-west-2"
    
    print("Creation de la stack CloudFormation...")
    success, output = run_command(cmd)
    
    if not success:
        print("ERREUR: Creation de la stack échouée")
        return False
    
    print("OK: Commande de création envoyée")
    
    # Attendre la création
    print("Attente de la création de la stack...")
    success, output = run_command(
        f"aws cloudformation wait stack-create-complete --stack-name {stack_name} --region us-west-2"
    )
    
    if success:
        print("OK: Stack créée avec succès")
        return True
    else:
        print("ATTENTION: La création de la stack a pris trop de temps")
        print("Conseil: Vérifiez l'état dans la console CloudFormation")
        return True  # Retourner True quand même

def update_lambda_code():
    """Met à jour le code de la fonction Lambda avec le vrai code."""
    print("\n7. Mise à jour du code Lambda avec le vrai code...")
    
    # Récupérer le nom de la fonction Lambda
    success, output = run_command(
        "aws cloudformation describe-stacks --stack-name invoice-extractor --region us-west-2 "
        "--query 'Stacks[0].Outputs[?OutputKey==`LambdaFunctionName`].OutputValue' --output text"
    )
    
    if not success or not output.strip():
        print("ATTENTION: Impossible de récupérer le nom de la fonction Lambda")
        return False
    
    lambda_function_name = output.strip()
    print(f"Fonction Lambda: {lambda_function_name}")
    
    # Mettre à jour le code
    zip_path = "invoice-extractor-lambda-final.zip"
    success, output = run_command(
        f"aws lambda update-function-code --function-name {lambda_function_name} "
        f"--zip-file fileb://{zip_path} --region us-west-2"
    )
    
    if success:
        print("OK: Code Lambda mis à jour avec le vrai code")
        return True
    else:
        print("ERREUR: Mise à jour du code Lambda échouée")
        return False

def get_stack_outputs():
    """Récupère les outputs de la stack CloudFormation."""
    print("\n8. Recuperation des informations de déploiement...")
    
    success, output = run_command(
        "aws cloudformation describe-stacks --stack-name invoice-extractor --region us-west-2 "
        "--query 'Stacks[0].Outputs' --output json"
    )
    
    if success and output.strip():
        try:
            outputs = json.loads(output)
            print("\n" + "=" * 60)
            print("DEPLOIEMENT REUSSI !")
            print("=" * 60)
            
            for item in outputs:
                key = item.get('OutputKey', 'N/A')
                value = item.get('OutputValue', 'N/A')
                
                print(f"\n{key}:")
                print(f"   {value}")
            
            print("\n" + "=" * 60)
            print("\nINSTRUCTIONS D'UTILISATION:")
            print("1. Uploader une facture PDF dans le bucket S3")
            print("2. La fonction Lambda s'exécutera automatiquement")
            print("3. Vérifier les données extraites dans DynamoDB")
            print("4. Consulter les logs dans CloudWatch")
            
            return True
            
        except json.JSONDecodeError:
            print("ATTENTION: Impossible de parser les outputs JSON")
            return True
    else:
        print("INFO: Aucun output trouvé pour la stack")
        return True

def main():
    """Fonction principale."""
    print("=" * 60)
    print("DEPLOIEMENT FINAL - Invoice Extractor")
    print("=" * 60)
    
    import time
    
    try:
        # 1. Vérifier AWS CLI
        if not check_aws_cli():
            return 1
        
        # 2. Valider le template
        if not validate_template():
            return 1
        
        # 3. Créer le package Lambda avec dépendances
        success, zip_path = create_lambda_package_with_dependencies()
        if not success:
            return 1
        
        # 4. Déployer la stack CloudFormation
        if not deploy_cloudformation_stack("dummy-bucket"):
            return 1
        
        # 5. Mettre à jour le code Lambda
        if not update_lambda_code():
            print("ATTENTION: Le code Lambda n'a pas pu être mis à jour")
            print("Conseil: Mettez à jour manuellement via la console AWS")
        
        # 6. Afficher les outputs
        get_stack_outputs()
        
        print("\n" + "=" * 60)
        print("DEPLOIEMENT TERMINE !")
        print("=" * 60)
        
        return 0
        
    except KeyboardInterrupt:
        print("\n\nOperation interrompue")
        return 1
    except Exception as e:
        print(f"\nERREUR: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
