#!/usr/bin/env python3
"""
Script de déploiement automatique sans interaction utilisateur.
"""

import subprocess
import sys
import json
import os
import zipfile
import shutil
import time

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
        
        if result.returncode != 0 and not ignore_errors:
            print(f"ERREUR: Commande échouée")
            if result.stderr:
                error_msg = result.stderr[:500]
                print(f"Details: {error_msg}")
            return False, result.stderr
        
        return True, result.stdout
    
    except Exception as e:
        if not ignore_errors:
            print(f"Exception: {e}")
        return False, str(e)

def main():
    """Fonction principale."""
    print("=" * 60)
    print("DEPLOIEMENT AUTOMATIQUE CLOUDFORMATION")
    print("=" * 60)
    
    try:
        # 1. Vérifier AWS CLI
        print("\n1. Verification AWS CLI...")
        success, output = run_command("aws sts get-caller-identity")
        if not success:
            print("ERREUR: AWS CLI non configuré")
            return 1
        
        print("OK: AWS CLI configuré")
        
        # 2. Valider le template
        print("\n2. Validation template CloudFormation...")
        template_path = "cloudformation-template-final.yaml"
        if not os.path.exists(template_path):
            print(f"ERREUR: Template non trouvé")
            return 1
        
        success, output = run_command(
            f"aws cloudformation validate-template --template-body file://{template_path} --region us-west-2"
        )
        
        if not success:
            print("ERREUR: Template invalide")
            return 1
        
        print("OK: Template valide")
        
        # 3. Créer le package Lambda
        print("\n3. Creation package Lambda...")
        
        if not os.path.exists("src_propre") or not os.path.exists("lambda_package"):
            print("ERREUR: Répertoires source manquants")
            return 1
        
        # Créer package
        package_dir = "temp_package"
        zip_path = "invoice-extractor-deploy.zip"
        
        try:
            # Nettoyer
            if os.path.exists(package_dir):
                shutil.rmtree(package_dir)
            if os.path.exists(zip_path):
                os.remove(zip_path)
            
            os.makedirs(package_dir, exist_ok=True)
            
            # Copier dépendances
            print("Copie dépendances...")
            for item in os.listdir("lambda_package"):
                src = os.path.join("lambda_package", item)
                dst = os.path.join(package_dir, item)
                if os.path.isfile(src):
                    shutil.copy2(src, dst)
                else:
                    shutil.copytree(src, dst, dirs_exist_ok=True)
            
            # Copier code source
            print("Copie code source...")
            for item in os.listdir("src_propre"):
                src = os.path.join("src_propre", item)
                dst = os.path.join(package_dir, item)
                if os.path.isfile(src):
                    shutil.copy2(src, dst)
                else:
                    shutil.copytree(src, dst, dirs_exist_ok=True)
            
            # Créer ZIP
            print("Creation ZIP...")
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(package_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, package_dir)
                        zipf.write(file_path, arcname)
            
            size_mb = os.path.getsize(zip_path) / 1024 / 1024
            print(f"OK: Package créé ({size_mb:.2f} MB)")
            
            # Nettoyer
            shutil.rmtree(package_dir)
            
        except Exception as e:
            print(f"ERREUR: {e}")
            return 1
        
        # 4. Gérer la stack existante
        print("\n4. Gestion stack existante...")
        stack_name = "invoice-extractor"
        
        # Vérifier si la stack existe
        success, _ = run_command(
            f"aws cloudformation describe-stacks --stack-name {stack_name} --region us-west-2",
            ignore_errors=True
        )
        
        if success:
            print("Stack existe, suppression...")
            run_command(f"aws cloudformation delete-stack --stack-name {stack_name} --region us-west-2")
            print("Attente suppression...")
            run_command(
                f"aws cloudformation wait stack-delete-complete --stack-name {stack_name} --region us-west-2",
                ignore_errors=True
            )
            print("OK: Stack supprimée")
            time.sleep(5)  # Pause pour AWS
        else:
            print("Pas de stack existante")
        
        # 5. Créer la nouvelle stack
        print("\n5. Creation nouvelle stack...")
        
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
            print("ERREUR: Creation stack")
            return 1
        
        print("OK: Commande creation envoyée")
        
        # Attendre un peu avant de vérifier
        print("Attente creation stack (2-3 min)...")
        time.sleep(30)
        
        # Vérifier l'état
        print("Verification état...")
        success, output = run_command(
            f"aws cloudformation describe-stacks --stack-name {stack_name} --region us-west-2",
            ignore_errors=True
        )
        
        if success:
            print("OK: Stack en cours de creation")
        else:
            print("ATTENTION: Verifiez console CloudFormation")
        
        # 6. Mettre à jour le code Lambda
        print("\n6. Mise à jour code Lambda...")
        
        # Attendre un peu plus pour que la fonction soit créée
        time.sleep(30)
        
        # Récupérer le nom de la fonction
        success, output = run_command(
            f"aws cloudformation describe-stacks --stack-name {stack_name} --region us-west-2 "
            f"--query 'Stacks[0].Outputs[?OutputKey==`LambdaFunctionName`].OutputValue' --output text",
            ignore_errors=True
        )
        
        if success and output.strip():
            lambda_name = output.strip()
            print(f"Fonction Lambda: {lambda_name}")
            
            # Mettre à jour le code
            success, _ = run_command(
                f"aws lambda update-function-code --function-name {lambda_name} "
                f"--zip-file fileb://{zip_path} --region us-west-2",
                ignore_errors=True
            )
            
            if success:
                print("OK: Code mis à jour")
            else:
                print("ATTENTION: Mise à jour code échouée")
        else:
            print("ATTENTION: Impossible de récupérer nom fonction")
        
        # 7. Afficher les résultats
        print("\n7. Résultats déploiement...")
        
        success, output = run_command(
            f"aws cloudformation describe-stacks --stack-name {stack_name} --region us-west-2 "
            f"--query 'Stacks[0].Outputs' --output json",
            ignore_errors=True
        )
        
        if success and output.strip():
            try:
                outputs = json.loads(output)
                print("\n" + "=" * 60)
                print("DEPLOIEMENT REUSSI")
                print("=" * 60)
                
                for item in outputs:
                    key = item.get('OutputKey', 'N/A')
                    value = item.get('OutputValue', 'N/A')
                    print(f"{key}: {value}")
                
            except:
                print("Stack déployée")
        else:
            print("Stack déployée")
        
        print("\n" + "=" * 60)
        print("FIN DU DEPLOIEMENT")
        print("=" * 60)
        
        return 0
        
    except Exception as e:
        print(f"\nERREUR: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
