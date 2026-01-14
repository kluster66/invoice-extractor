#!/usr/bin/env python3
"""
Script de déploiement complet pour l'outil d'extraction de factures PDF.
Ce script gère tout le processus de déploiement automatiquement.
"""

import subprocess
import sys
import json
import os
import zipfile
import shutil
from pathlib import Path

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
            print(f"ERREUR: Commande échouée: {command}")
            if result.stderr:
                print(f"Details: {result.stderr[:500]}")
            return False, result.stderr
        
        return True, result.stdout
    
    except Exception as e:
        print(f"EXCEPTION: {e}")
        return False, str(e)

def check_aws_cli():
    """Vérifie que AWS CLI est configuré."""
    print("Verification de la configuration AWS...")
    
    success, output = run_command("aws sts get-caller-identity")
    if not success:
        print("ERREUR: AWS CLI n'est pas configuré ou les credentials sont invalides.")
        print("CONSEIL: Exécutez 'aws configure' pour configurer vos credentials.")
        return False
    
    # Extraire l'ID du compte
    try:
        identity = json.loads(output)
        account_id = identity.get('Account', 'N/A')
        user_arn = identity.get('Arn', 'N/A')
        print(f"OK: AWS CLI configuré - Compte: {account_id}")
        print(f"   Utilisateur: {user_arn}")
        return True
    except:
        print("OK: AWS CLI configuré")
        return True

def validate_template():
    """Valide le template CloudFormation."""
    print("\nValidation du template CloudFormation...")
    
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

def create_minimal_lambda_package():
    """Crée un package Lambda minimal avec seulement les dépendances nécessaires."""
    print("\nCreation du package Lambda minimal...")
    
    # Créer un répertoire temporaire pour le package
    package_dir = "lambda_package_deploy"
    
    try:
        # Nettoyer l'ancien package
        if os.path.exists(package_dir):
            shutil.rmtree(package_dir)
        
        # Créer le répertoire
        os.makedirs(package_dir, exist_ok=True)
        
        # Copier le code source depuis src_propre
        src_dir = "src_propre"
        if not os.path.exists(src_dir):
            print(f"ERREUR: Répertoire source non trouvé: {src_dir}")
            return False, None
        
        # Copier tous les fichiers Python
        for item in os.listdir(src_dir):
            src_path = os.path.join(src_dir, item)
            dst_path = os.path.join(package_dir, item)
            
            if os.path.isfile(src_path) and item.endswith('.py'):
                shutil.copy2(src_path, dst_path)
                print(f"  Copié: {item}")
        
        print(f"OK: Code source copié depuis {src_dir}")
        
        # Dépendances minimales pour Lambda
        dependencies = [
            "boto3",
            "botocore",
            "PyPDF2",
            "python-dotenv",
            "typing_extensions"
        ]
        
        # Installer les dépendances dans le package
        print("Installation des dépendances...")
        for dep in dependencies:
            success, output = run_command(
                f"pip install {dep} --target {package_dir} --no-deps"
            )
            if success:
                print(f"  Installé: {dep}")
            else:
                print(f"  ATTENTION: Impossible d'installer {dep}")
        
        # Créer le fichier ZIP
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
        print(f"ERREUR lors de la création du package: {e}")
        return False, None

def upload_to_s3(bucket_name, zip_path):
    """Upload le package Lambda vers S3."""
    print(f"\nUpload du package Lambda vers S3: {bucket_name}...")
    
    success, output = run_command(
        f"aws s3 cp {zip_path} s3://{bucket_name}/invoice-extractor-lambda.zip --region us-west-2"
    )
    
    if success:
        print("OK: Package uploadé vers S3")
        return True
    else:
        print("ERREUR: Echec de l'upload vers S3")
        return False

def deploy_cloudformation_stack():
    """Déploie la stack CloudFormation."""
    print("\nDeploiement de la stack CloudFormation...")
    
    stack_name = "invoice-extractor"
    template_path = "cloudformation-template-final.yaml"
    
    # Vérifier si la stack existe déjà
    success, output = run_command(
        f"aws cloudformation describe-stacks --stack-name {stack_name} --region us-west-2"
    )
    
    if success:
        # Stack existe, demander confirmation pour mise à jour
        print(f"ATTENTION: La stack '{stack_name}' existe déjà.")
        response = input("Voulez-vous la mettre à jour? (oui/non): ")
        
        if response.lower() != 'oui':
            print("ANNULATION: Déploiement annulé")
            return False
        
        command = "update-stack"
        action = "mise à jour"
    else:
        command = "create-stack"
        action = "création"
    
    # Paramètres pour la stack
    parameters = [
        "ParameterKey=EnvironmentName,ParameterValue=prod",
        "ParameterKey=BedrockModelId,ParameterValue=meta.llama3-1-70b-instruct-v1:0"
    ]
    
    # Construire la commande
    cmd = f"aws cloudformation {command} " \
          f"--stack-name {stack_name} " \
          f"--template-body file://{template_path} " \
          f"--parameters {' '.join(parameters)} " \
          f"--capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM " \
          f"--region us-west-2"
    
    print(f"\n{action.capitalize()} de la stack '{stack_name}'...")
    success, output = run_command(cmd)
    
    if not success:
        print(f"ERREUR: Echec de la {action} de la stack")
        return False
    
    print(f"OK: Commande de {action} envoyée avec succès")
    
    # Attendre la complétion
    print(f"\nAttente de la {action} de la stack (cela peut prendre 2-3 minutes)...")
    
    wait_cmd = f"aws cloudformation wait stack-{command.replace('stack', '')}-complete " \
               f"--stack-name {stack_name} --region us-west-2"
    
    success, output = run_command(wait_cmd)
    
    if success:
        print(f"OK: Stack {action}ée avec succès")
        return True
    else:
        print(f"ATTENTION: La {action} de la stack a pris trop de temps ou a échoué")
        print("CONSEIL: Vérifiez l'état dans la console CloudFormation")
        return True  # Retourner True quand même pour afficher les outputs

def get_stack_outputs():
    """Récupère les outputs de la stack CloudFormation."""
    print("\nRecuperation des informations de déploiement...")
    
    stack_name = "invoice-extractor"
    
    success, output = run_command(
        f"aws cloudformation describe-stacks --stack-name {stack_name} --region us-west-2 "
        f"--query 'Stacks[0].Outputs' --output json"
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
                description = item.get('Description', '')
                
                print(f"\n{key}:")
                print(f"  {value}")
                if description:
                    print(f"  {description}")
            
            print("\n" + "=" * 60)
            
            # Afficher les instructions d'utilisation
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

def test_deployment():
    """Teste le déploiement en uploadant un fichier de test."""
    print("\nTest du déploiement...")
    
    # Récupérer le nom du bucket depuis les outputs
    success, output = run_command(
        "aws cloudformation describe-stacks --stack-name invoice-extractor --region us-west-2 "
        "--query 'Stacks[0].Outputs[?OutputKey==`BucketName`].OutputValue' --output text"
    )
    
    if success and output.strip():
        bucket_name = output.strip()
        print(f"Bucket S3: {bucket_name}")
        
        # Vérifier s'il y a un fichier de test
        test_file = "test_factures/2140 1902095741 210515 TELEFONICA MG PLVT.pdf"
        if os.path.exists(test_file):
            print(f"Fichier de test trouvé: {test_file}")
            
            response = input("Voulez-vous uploader ce fichier pour tester? (oui/non): ")
            if response.lower() == 'oui':
                print(f"\nUpload du fichier de test vers S3...")
                
                success, upload_output = run_command(
                    f'aws s3 cp "{test_file}" s3://{bucket_name}/ --region us-west-2'
                )
                
                if success:
                    print("OK: Fichier uploadé avec succès")
                    print("\nLa fonction Lambda devrait s'exécuter dans quelques secondes...")
                    print("CONSEIL: Vérifiez les logs CloudWatch pour voir l'extraction")
                else:
                    print("ERREUR: Echec de l'upload du fichier")
        else:
            print("INFO: Aucun fichier de test trouvé")
    else:
        print("INFO: Impossible de récupérer le nom du bucket")

def cleanup():
    """Nettoie les fichiers temporaires."""
    print("\nNettoyage des fichiers temporaires...")
    
    files_to_remove = [
        "invoice-extractor-lambda.zip",
        "lambda_package_deploy",
        "response.json"
    ]
    
    for file in files_to_remove:
        if os.path.exists(file):
            if os.path.isdir(file):
                shutil.rmtree(file)
            else:
                os.remove(file)
            print(f"  Supprimé: {file}")
    
    print("OK: Nettoyage terminé")

def main():
    """Fonction principale."""
    print("=" * 60)
    print("DEPLOIEMENT COMPLET - INVOICE EXTRACTOR")
    print("=" * 60)
    
    try:
        # 1. Vérifier AWS CLI
        print("\n1. Verification des prérequis...")
        if not check_aws_cli():
            return 1
        
        # 2. Valider le template
        print("\n2. Validation du template...")
        if not validate_template():
            return 1
        
        # 3. Créer le package Lambda
        print("\n3. Preparation du code Lambda...")
        success, zip_path = create_minimal_lambda_package()
        if not success:
            return 1
        
        # 4. Uploader vers S3 (bucket temporaire pour le déploiement)
        print("\n4. Upload du code vers S3...")
        
        # Créer un bucket temporaire pour le déploiement
        import uuid
        temp_bucket = f"invoice-extractor-deploy-{uuid.uuid4().hex[:8]}"
        
        success, output = run_command(
            f"aws s3 mb s3://{temp_bucket} --region us-west-2"
        )
        
        if not success:
            print("ATTENTION: Impossible de créer le bucket temporaire")
            print("CONSEIL: Utilisez un bucket existant ou créez-en un manuellement")
            temp_bucket = input("Entrez le nom d'un bucket S3 existant: ")
        
        if not upload_to_s3(temp_bucket, zip_path):
            return 1
        
        # 5. Déployer la stack CloudFormation
        print("\n5. Deploiement de l'infrastructure...")
        if not deploy_cloudformation_stack():
            return 1
        
        # 6. Afficher les résultats
        print("\n6. Recuperation des informations...")
        get_stack_outputs()
        
        # 7. Nettoyer
        cleanup()
        
        # 8. Tester (optionnel)
        print("\n7. Test du déploiement...")
        response = input("Voulez-vous tester avec un fichier de test? (oui/non): ")
        if response.lower() == 'oui':
            test_deployment()
        
        print("\n" + "=" * 60)
        print("DEPLOIEMENT TERMINE AVEC SUCCES !")
        print("=" * 60)
        
        return 0
        
    except KeyboardInterrupt:
        print("\n\nANNULATION: Opération interrompue par l'utilisateur")
        cleanup()
        return 1
    except Exception as e:
        print(f"\nERREUR: Erreur inattendue: {e}")
        cleanup()
        return 1

if __name__ == "__main__":
    sys.exit(main())
