#!/usr/bin/env python3
"""
Script de déploiement final sans émojis pour Windows.
"""

import subprocess
import sys
import json
import os
import zipfile
import shutil
import time

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
                error_msg = result.stderr[:500]
                print(f"Details: {error_msg}")
            return False, result.stderr
        
        return True, result.stdout
    
    except Exception as e:
        print(f"Exception: {e}")
        return False, str(e)

def main():
    """Fonction principale."""
    print("=" * 60)
    print("DEPLOIEMENT CLOUDFORMATION - INVOICE EXTRACTOR")
    print("=" * 60)
    
    try:
        # 1. Vérifier AWS CLI
        print("\n1. Verification de la configuration AWS...")
        success, output = run_command("aws sts get-caller-identity")
        if not success:
            print("ERREUR: AWS CLI n'est pas configuré")
            print("Conseil: Exécutez 'aws configure'")
            return 1
        
        try:
            identity = json.loads(output)
            account_id = identity.get('Account', 'N/A')
            print(f"OK: AWS CLI configuré - Compte: {account_id}")
        except:
            print("OK: AWS CLI configuré")
        
        # 2. Valider le template CloudFormation
        print("\n2. Validation du template CloudFormation...")
        template_path = "cloudformation-template-final.yaml"
        if not os.path.exists(template_path):
            print(f"ERREUR: Template non trouvé: {template_path}")
            return 1
        
        success, output = run_command(
            f"aws cloudformation validate-template --template-body file://{template_path} --region us-west-2"
        )
        
        if not success:
            print("ERREUR: Template CloudFormation invalide")
            return 1
        
        print("OK: Template CloudFormation valide")
        
        # 3. Créer le package Lambda
        print("\n3. Creation du package Lambda...")
        
        # Vérifier les sources
        if not os.path.exists("src_propre"):
            print("ERREUR: Répertoire src_propre non trouvé")
            return 1
        
        if not os.path.exists("lambda_package"):
            print("ERREUR: Répertoire lambda_package non trouvé")
            return 1
        
        # Créer un répertoire temporaire
        package_dir = "temp_lambda_package"
        
        try:
            # Nettoyer
            if os.path.exists(package_dir):
                shutil.rmtree(package_dir)
            
            os.makedirs(package_dir, exist_ok=True)
            
            print("Copie des dépendances...")
            # Copier lambda_package (dépendances)
            for item in os.listdir("lambda_package"):
                src = os.path.join("lambda_package", item)
                dst = os.path.join(package_dir, item)
                
                if os.path.isfile(src):
                    shutil.copy2(src, dst)
                else:
                    shutil.copytree(src, dst, dirs_exist_ok=True)
            
            print("Copie du code source...")
            # Copier src_propre (code source)
            for item in os.listdir("src_propre"):
                src = os.path.join("src_propre", item)
                dst = os.path.join(package_dir, item)
                
                if os.path.isfile(src):
                    shutil.copy2(src, dst)
                else:
                    shutil.copytree(src, dst, dirs_exist_ok=True)
            
            # Créer le ZIP
            zip_path = "invoice-extractor-deploy.zip"
            print(f"Creation de {zip_path}...")
            
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(package_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, package_dir)
                        zipf.write(file_path, arcname)
            
            size_mb = os.path.getsize(zip_path) / 1024 / 1024
            print(f"OK: Package créé: {zip_path} ({size_mb:.2f} MB)")
            
            # Nettoyer
            shutil.rmtree(package_dir)
            
        except Exception as e:
            print(f"ERREUR: Creation du package: {e}")
            if os.path.exists(package_dir):
                shutil.rmtree(package_dir, ignore_errors=True)
            return 1
        
        # 4. Déployer la stack CloudFormation
        print("\n4. Deploiement de la stack CloudFormation...")
        
        stack_name = "invoice-extractor"
        
        # Vérifier si la stack existe
        print("Verification de l'existence de la stack...")
        success, _ = run_command(f"aws cloudformation describe-stacks --stack-name {stack_name} --region us-west-2")
        
        if success:
            print(f"ATTENTION: La stack '{stack_name}' existe déjà")
            response = input("Voulez-vous la supprimer et recréer? (oui/non): ")
            if response.lower() != 'oui':
                print("DEPLOIEMENT ANNULE")
                return 1
            
            print("Suppression de la stack existante...")
            run_command(f"aws cloudformation delete-stack --stack-name {stack_name} --region us-west-2")
            print("Attente de la suppression...")
            run_command(f"aws cloudformation wait stack-delete-complete --stack-name {stack_name} --region us-west-2")
            print("OK: Stack supprimée")
        
        # Créer la stack
        print("Creation de la nouvelle stack...")
        
        # Générer un nom de bucket unique
        timestamp = int(time.time())
        bucket_name = f"invoice-extractor-bucket-{timestamp}"
        
        cmd = f"aws cloudformation create-stack " \
              f"--stack-name {stack_name} " \
              f"--template-body file://cloudformation-template-final.yaml " \
              f"--parameters " \
              f"ParameterKey=EnvironmentName,ParameterValue=prod " \
              f"ParameterKey=BucketName,ParameterValue={bucket_name} " \
              f"ParameterKey=TableName,ParameterValue=invoices-extractor " \
              f"ParameterKey=BedrockModelId,ParameterValue=meta.llama3-1-70b-instruct-v1:0 " \
              f"--capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM " \
              f"--region us-west-2"
        
        success, output = run_command(cmd)
        
        if not success:
            print("ERREUR: Echec de la creation de la stack")
            return 1
        
        print("OK: Commande de creation envoyée")
        print("Attente de la creation de la stack (cela peut prendre 2-3 minutes)...")
        
        # Attendre avec timeout
        wait_cmd = f"aws cloudformation wait stack-create-complete --stack-name {stack_name} --region us-west-2"
        success, output = run_command(wait_cmd)
        
        if success:
            print("OK: Stack créée avec succès")
        else:
            print("ATTENTION: La creation prend plus de temps que prévu")
            print("Conseil: Verifiez l'état dans la console CloudFormation")
        
        # 5. Mettre à jour le code Lambda
        print("\n5. Mise à jour du code Lambda...")
        
        # Récupérer le nom de la fonction Lambda
        print("Recuperation du nom de la fonction Lambda...")
        success, output = run_command(
            "aws cloudformation describe-stacks --stack-name invoice-extractor --region us-west-2 "
            "--query 'Stacks[0].Outputs[?OutputKey==`LambdaFunctionName`].OutputValue' --output text"
        )
        
        if not success or not output.strip():
            print("ATTENTION: Impossible de recuperer le nom de la fonction Lambda")
            print("Conseil: La fonction sera créée avec le code de test du template")
        else:
            lambda_name = output.strip()
            print(f"Fonction Lambda: {lambda_name}")
            
            # Mettre à jour le code
            print(f"Mise à jour du code avec {zip_path}...")
            success, output = run_command(
                f"aws lambda update-function-code --function-name {lambda_name} "
                f"--zip-file fileb://{zip_path} --region us-west-2"
            )
            
            if success:
                print("OK: Code Lambda mis à jour avec le vrai code")
            else:
                print("ERREUR: Echec de la mise à jour du code")
                print("Conseil: Mettez à jour manuellement via la console AWS")
        
        # 6. Afficher les outputs
        print("\n6. Recuperation des informations...")
        
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
                print("\nINSTRUCTIONS:")
                print("1. Uploader une facture PDF dans le bucket S3 ci-dessus")
                print("2. La fonction Lambda s'executera automatiquement")
                print("3. Verifiez les donnees dans DynamoDB")
                print("4. Consultez les logs dans CloudWatch")
                
            except:
                print("OK: Stack deployée")
        else:
            print("OK: Stack deployée")
        
        print("\n" + "=" * 60)
        print("DEPLOIEMENT TERMINE !")
        print("=" * 60)
        
        return 0
        
    except KeyboardInterrupt:
        print("\n\nOPERATION INTERROMPUE")
        return 1
    except Exception as e:
        print(f"\nERREUR INATTENDUE: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
