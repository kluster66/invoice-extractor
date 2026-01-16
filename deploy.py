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

# Region par défaut
AWS_REGION = "us-west-2"

def run_command(command, description=None, ignore_errors=False):
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
            if not ignore_errors:
                print(f"ERREUR: Commande échouée: {command}")
                if result.stderr:
                    print(f"Details: {result.stderr[:500]}")
            return False, result.stderr
        
        return True, result.stdout
    
    except Exception as e:
        print(f"EXCEPTION: {e}")
        return False, str(e)

def check_aws_cli():
    """Vérifie que AWS CLI est configuré et retourne l'Account ID."""
    print("Verification de la configuration AWS...")
    
    success, output = run_command("aws sts get-caller-identity")
    if not success:
        print("ERREUR: AWS CLI n'est pas configuré ou les credentials sont invalides.")
        print("CONSEIL: Exécutez 'aws configure' pour configurer vos credentials.")
        return None
    
    # Extraire l'ID du compte
    try:
        identity = json.loads(output)
        account_id = identity.get('Account')
        user_arn = identity.get('Arn', 'N/A')
        print(f"OK: AWS CLI configuré - Compte: {account_id}")
        return account_id
    except:
        print("ERREUR: Impossible de parser l'identité AWS")
        return None

def validate_template():
    """Valide le template CloudFormation."""
    print("\nValidation du template CloudFormation...")
    
    template_path = "cloudformation-template-final.yaml"
    if not os.path.exists(template_path):
        print(f"ERREUR: Template non trouvé: {template_path}")
        return False
    
    success, output = run_command(
        f"aws cloudformation validate-template --template-body file://{template_path} --region {AWS_REGION}"
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
                f"python -m pip install {dep} --target {package_dir} --no-deps"
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

def ensure_s3_bucket(bucket_name):
    """Vérifie l'existence du bucket ou le crée s'il n'existe pas."""
    print(f"\nVérification du bucket de déploiement: {bucket_name}...")
    
    # Vérifier si le bucket existe
    success, output = run_command(f"aws s3api head-bucket --bucket {bucket_name}")
    
    if success:
        print(f"OK: Le bucket {bucket_name} existe déjà")
        return True
    
    # Si échec, vérifier si c'est parce qu'il n'existe pas (404) ou accès interdit (403)
    if "403" in output:
        print(f"ERREUR: Le bucket {bucket_name} existe mais vous n'avez pas les droits ou il appartient à un autre compte.")
        return False
        
    # Créer le bucket
    print(f"Création du bucket {bucket_name}...")
    if AWS_REGION == "us-east-1":
        cmd = f"aws s3 mb s3://{bucket_name}"
    else:
        cmd = f"aws s3 mb s3://{bucket_name} --region {AWS_REGION}"
        
    success, output = run_command(cmd)
    
    if success:
        print("OK: Bucket créé avec succès")
        # Activer le versioning pour sécurité
        run_command(f"aws s3api put-bucket-versioning --bucket {bucket_name} --versioning-configuration Status=Enabled")
        return True
    else:
        print(f"ERREUR: Impossible de créer le bucket: {output}")
        return False

def upload_to_s3(bucket_name, zip_path):
    """Upload le package Lambda vers S3."""
    print(f"\nUpload du package Lambda vers S3: {bucket_name}...")
    
    success, output = run_command(
        f"aws s3 cp {zip_path} s3://{bucket_name}/invoice-extractor-lambda.zip --region {AWS_REGION}"
    )
    
    if success:
        print("OK: Package uploadé vers S3")
        return True
    else:
        print("ERREUR: Echec de l'upload vers S3")
        return False

def deploy_cloudformation_stack(lambda_code_bucket, lambda_code_key):
    """Déploie la stack CloudFormation."""
    print("\nDeploiement de la stack CloudFormation...")
    
    stack_name = "invoice-extractor"
    template_path = "cloudformation-template-final.yaml"
    
    # Vérifier si la stack existe déjà
    success, output = run_command(
        f"aws cloudformation describe-stacks --stack-name {stack_name} --region {AWS_REGION} --output json",
        ignore_errors=True
    )
    
    command = "create-stack"
    action = "création"
    
    if success:
        try:
            stack_info = json.loads(output)
            status = stack_info['Stacks'][0]['StackStatus']
            print(f"Statut actuel de la stack: {status}")
            
            if status == 'ROLLBACK_COMPLETE':
                print("ATTENTION: La stack est en état ROLLBACK_COMPLETE (probablement suite à un échec de création).")
                print("Elle doit être supprimée avant de pouvoir être recréée.")
                response = input("Voulez-vous supprimer la stack existante? (oui/non): ")
                
                if response.lower() == 'oui':
                    print("Suppression de la stack...")
                    run_command(f"aws cloudformation delete-stack --stack-name {stack_name} --region {AWS_REGION}")
                    print("Attente de la suppression (cela peut prendre 1-2 minutes)...")
                    run_command(f"aws cloudformation wait stack-delete-complete --stack-name {stack_name} --region {AWS_REGION}")
                    print("Stack supprimée.")
                    # On continue avec create-stack
                else:
                    print("ANNULATION: Impossible de procéder sans supprimer la stack corrompue.")
                    return False
            
            elif status in ['CREATE_COMPLETE', 'UPDATE_COMPLETE', 'UPDATE_ROLLBACK_COMPLETE']:
                # Stack exists and is healthy-ish, ask for update
                print(f"ATTENTION: La stack '{stack_name}' existe déjà.")
                response = input("Voulez-vous la mettre à jour? (oui/non): ")
                
                if response.lower() != 'oui':
                    print("ANNULATION: Déploiement annulé")
                    return False
                
                command = "update-stack"
                action = "mise à jour"
            else:
                 print(f"ATTENTION: La stack est dans un état inattendu: {status}")
                 response = input("Voulez-vous essayer de la mettre à jour quand même? (oui/non): ")
                 if response.lower() == 'oui':
                     command = "update-stack"
                     action = "mise à jour"
                 else:
                     return False
                     
        except Exception as e:
            print(f"ERREUR lors de la lecture du statut de la stack: {e}")
            # On assume qu'on peut update ou create? Safer to stop.
            return False
    
    # Paramètres pour la stack
    # Générer un nom de bucket unique pour les inputs
    account_id = lambda_code_bucket.split('-')[-2] # Hacky retrieval from the deploy bucket name which includes ID
    # Better: we passed account_id to main, maybe we should pass it here or just regenerate it. 
    # Let's simple check aws cli again or make it global/arg. 
    # To keep it simple, let's use the one from deploy bucket if possible or just rely on a unique name generation.
    
    import random
    import string
    
    # We will generate a suffix or use account ID if we can get it easily. 
    # Getting Account ID again to be safe.
    success_id, output_id = run_command("aws sts get-caller-identity --query Account --output text")
    current_account_id = output_id.strip() if success_id else "unknown"
    
    input_bucket_name = f"invoice-input-{current_account_id}-{AWS_REGION}"
    
    parameters = [
        "ParameterKey=EnvironmentName,ParameterValue=prod",
        "ParameterKey=BedrockModelId,ParameterValue=meta.llama3-1-70b-instruct-v1:0",
        f"ParameterKey=LambdaCodeBucket,ParameterValue={lambda_code_bucket}",
        f"ParameterKey=LambdaCodeKey,ParameterValue={lambda_code_key}",
        f"ParameterKey=BucketName,ParameterValue={input_bucket_name}"
    ]
    
    # Construire la commande
    cmd = f"aws cloudformation {command} " \
          f"--stack-name {stack_name} " \
          f"--template-body file://{template_path} " \
          f"--parameters {' '.join(parameters)} " \
          f"--capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM " \
          f"--region {AWS_REGION}"
    
    print(f"\n{action.capitalize()} de la stack '{stack_name}'...")
    print(f"Bucket de données: {input_bucket_name}")
    success, output = run_command(cmd)
    
    if not success:
        print(f"ERREUR: Echec de la {action} de la stack")
        if "No updates are to be performed" in output:
            print("INFO: Aucune modification détectée.")
            return True
        return False
    
    print(f"OK: Commande de {action} envoyée avec succès")
    
    # Attendre la complétion
    print(f"\nAttente de la {action} de la stack (cela peut prendre 2-3 minutes)...")
    
    wait_cmd = f"aws cloudformation wait stack-{command.replace('stack', '')}complete " \
               f"--stack-name {stack_name} --region {AWS_REGION}"
    
    success, output = run_command(wait_cmd)
    
    if success:
        print(f"OK: Stack {action}ée avec succès")
        return True
    else:
        print(f"ERREUR: La {action} de la stack a échoué")
        print("Analyse des erreurs...")
        
        # Récupérer les événements d'erreur
        events_cmd = f"aws cloudformation describe-stack-events --stack-name {stack_name} --region {AWS_REGION} " \
                     f"--query \"StackEvents[?ResourceStatus=='CREATE_FAILED' || ResourceStatus=='UPDATE_FAILED'].{{Resource:LogicalResourceId, Reason:ResourceStatusReason}}\" " \
                     f"--output json"
        
        success_evt, output_evt = run_command(events_cmd)
        if success_evt:
            try:
                events = json.loads(output_evt)
                print("\nRAISONS DE L'ECHEC:")
                for evt in events:
                    print(f"- {evt.get('Resource')}: {evt.get('Reason')}")
            except:
                print(f"Raw error output: {output_evt}")
        
        return False

def get_stack_outputs():
    """Récupère les outputs de la stack CloudFormation."""
    print("\nRecuperation des informations de déploiement...")
    
    stack_name = "invoice-extractor"
    
    success, output = run_command(
        f"aws cloudformation describe-stacks --stack-name {stack_name} --region {AWS_REGION} "
        f"--query \"Stacks[0].Outputs\" --output json"
    )
    
    if success and output and output.strip() and output.strip() != 'null':
        try:
            outputs = json.loads(output)
            if not outputs:
                print("INFO: Aucun output trouvé (possible échec précédent)")
                return False
                
            print("\n" + "=" * 60)
            print("DEPLOIEMENT REUSSI !")
            print("=" * 60)
            
            for item in outputs:
                if isinstance(item, dict):
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
            print(f"ATTENTION: Impossible de parser les outputs JSON: {output[:100]}...")
            return False
        except Exception as e:
            print(f"ATTENTION: Erreur lors de l'affichage des outputs: {e}")
            return False
    else:
        print("INFO: Aucun output trouvé pour la stack")
        return False

def test_deployment():
    """Teste le déploiement en uploadant un fichier de test."""
    print("\nTest du déploiement...")
    
    # Récupérer le nom du bucket depuis les outputs
    success, output = run_command(
        f"aws cloudformation describe-stacks --stack-name invoice-extractor --region {AWS_REGION} "
        "--query \"Stacks[0].Outputs[?OutputKey=='BucketName'].OutputValue\" --output text"
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
                    f'aws s3 cp "{test_file}" s3://{bucket_name}/ --region {AWS_REGION}'
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
        account_id = check_aws_cli()
        if not account_id:
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
        
        # 4. Gérer le bucket de déploiement et uploader
        print("\n4. Gestion des artifacts de déploiement...")
        
        # Définir un nom de bucket stable basé sur l'Account ID
        deploy_bucket = f"invoice-extractor-deploy-{account_id}-{AWS_REGION}"
        
        if not ensure_s3_bucket(deploy_bucket):
            print("ATTENTION: Impossible d'utiliser le bucket automatique.")
            deploy_bucket = input("Entrez le nom d'un bucket S3 existant pour le code: ")
        
        if not upload_to_s3(deploy_bucket, zip_path):
            return 1
            
        # 5. Déployer la stack CloudFormation
        print("\n5. Deploiement de l'infrastructure...")
        
        # Generer une clé unique avec timestamp pour forcer la mise à jour Lambda
        import time
        timestamp = int(time.time())
        zip_key = f"invoice-extractor-lambda-{timestamp}.zip"
        
        # Upload avec le nom unique
        print(f"Upload vers S3 avec la clé: {zip_key}")
        upload_success, _ = run_command(
            f"aws s3 cp {zip_path} s3://{deploy_bucket}/{zip_key} --region {AWS_REGION}"
        )
        
        if not upload_success:
            print("ERREUR: Echec de l'upload vers S3")
            return 1
            
        # On passe maintenant les infos du bucket de code
        if not deploy_cloudformation_stack(deploy_bucket, zip_key):
            return 1
        
        # 6. Afficher les résultats
        print("\n6. Recuperation des informations...")
        get_stack_outputs()
        
        # 7. Nettoyer
        cleanup()
        
        # 8. Tester (optionnel)
        print("\n7. Test du déploiement...")
        # On ne demande que si on est en mode interactif (input)
        # Mais ici on garde le comportement original
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
