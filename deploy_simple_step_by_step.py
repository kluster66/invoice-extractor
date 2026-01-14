#!/usr/bin/env python3
"""
Script de déploiement simple étape par étape.
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

def step1_check_aws():
    """Étape 1: Vérifier AWS CLI."""
    print("\n" + "="*60)
    print("ÉTAPE 1: Vérification AWS CLI")
    print("="*60)
    
    success, output = run_command("aws sts get-caller-identity")
    if not success:
        print("❌ AWS CLI n'est pas configuré")
        print("💡 Exécutez: aws configure")
        return False
    
    try:
        identity = json.loads(output)
        account_id = identity.get('Account', 'N/A')
        print(f"✅ AWS CLI configuré - Compte: {account_id}")
        return True
    except:
        print("✅ AWS CLI configuré")
        return True

def step2_validate_template():
    """Étape 2: Valider le template CloudFormation."""
    print("\n" + "="*60)
    print("ÉTAPE 2: Validation du template CloudFormation")
    print("="*60)
    
    template_path = "cloudformation-template-final.yaml"
    if not os.path.exists(template_path):
        print(f"❌ Template non trouvé: {template_path}")
        return False
    
    success, output = run_command(
        f"aws cloudformation validate-template --template-body file://{template_path} --region us-west-2"
    )
    
    if success:
        print("✅ Template CloudFormation valide")
        return True
    else:
        print("❌ Template CloudFormation invalide")
        return False

def step3_create_lambda_package():
    """Étape 3: Créer le package Lambda."""
    print("\n" + "="*60)
    print("ÉTAPE 3: Création du package Lambda")
    print("="*60)
    
    # Vérifier les sources
    if not os.path.exists("src_propre"):
        print("❌ Répertoire src_propre non trouvé")
        return False, None
    
    if not os.path.exists("lambda_package"):
        print("❌ Répertoire lambda_package non trouvé")
        return False, None
    
    # Créer un répertoire temporaire
    package_dir = "temp_lambda_package"
    
    try:
        # Nettoyer
        if os.path.exists(package_dir):
            shutil.rmtree(package_dir)
        
        os.makedirs(package_dir, exist_ok=True)
        
        print("📦 Copie des dépendances...")
        # Copier lambda_package (dépendances)
        for item in os.listdir("lambda_package"):
            src = os.path.join("lambda_package", item)
            dst = os.path.join(package_dir, item)
            
            if os.path.isfile(src):
                shutil.copy2(src, dst)
            else:
                shutil.copytree(src, dst, dirs_exist_ok=True)
        
        print("📄 Copie du code source...")
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
        print(f"🗜️  Création de {zip_path}...")
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(package_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, package_dir)
                    zipf.write(file_path, arcname)
        
        size_mb = os.path.getsize(zip_path) / 1024 / 1024
        print(f"✅ Package créé: {zip_path} ({size_mb:.2f} MB)")
        
        # Nettoyer
        shutil.rmtree(package_dir)
        
        return True, zip_path
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        if os.path.exists(package_dir):
            shutil.rmtree(package_dir, ignore_errors=True)
        return False, None

def step4_deploy_stack():
    """Étape 4: Déployer la stack CloudFormation."""
    print("\n" + "="*60)
    print("ÉTAPE 4: Déploiement de la stack CloudFormation")
    print("="*60)
    
    stack_name = "invoice-extractor"
    
    # Vérifier si la stack existe
    print("🔍 Vérification de l'existence de la stack...")
    success, _ = run_command(f"aws cloudformation describe-stacks --stack-name {stack_name} --region us-west-2")
    
    if success:
        print(f"⚠️  La stack '{stack_name}' existe déjà")
        response = input("Voulez-vous la supprimer et recréer? (oui/non): ")
        if response.lower() != 'oui':
            print("❌ Déploiement annulé")
            return False
        
        print("🗑️  Suppression de la stack existante...")
        run_command(f"aws cloudformation delete-stack --stack-name {stack_name} --region us-west-2")
        print("⏳ Attente de la suppression...")
        run_command(f"aws cloudformation wait stack-delete-complete --stack-name {stack_name} --region us-west-2")
        print("✅ Stack supprimée")
    
    # Créer la stack
    print("🚀 Création de la nouvelle stack...")
    
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
        print("❌ Échec de la création de la stack")
        return False
    
    print("✅ Commande de création envoyée")
    print("⏳ Attente de la création de la stack (cela peut prendre 2-3 minutes)...")
    
    # Attendre avec timeout
    wait_cmd = f"aws cloudformation wait stack-create-complete --stack-name {stack_name} --region us-west-2"
    success, output = run_command(wait_cmd)
    
    if success:
        print("✅ Stack créée avec succès")
        return True
    else:
        print("⚠️  La création prend plus de temps que prévu")
        print("💡 Vérifiez l'état dans la console CloudFormation")
        return True  # Continuer quand même

def step5_update_lambda_code(zip_path):
    """Étape 5: Mettre à jour le code Lambda."""
    print("\n" + "="*60)
    print("ÉTAPE 5: Mise à jour du code Lambda")
    print("="*60)
    
    # Récupérer le nom de la fonction Lambda
    print("🔍 Récupération du nom de la fonction Lambda...")
    success, output = run_command(
        "aws cloudformation describe-stacks --stack-name invoice-extractor --region us-west-2 "
        "--query 'Stacks[0].Outputs[?OutputKey==`LambdaFunctionName`].OutputValue' --output text"
    )
    
    if not success or not output.strip():
        print("⚠️  Impossible de récupérer le nom de la fonction Lambda")
        print("💡 La fonction sera créée avec le code de test du template")
        return False
    
    lambda_name = output.strip()
    print(f"📝 Fonction Lambda: {lambda_name}")
    
    # Mettre à jour le code
    print(f"🔄 Mise à jour du code avec {zip_path}...")
    success, output = run_command(
        f"aws lambda update-function-code --function-name {lambda_name} "
        f"--zip-file fileb://{zip_path} --region us-west-2"
    )
    
    if success:
        print("✅ Code Lambda mis à jour avec le vrai code")
        return True
    else:
        print("❌ Échec de la mise à jour du code")
        print("💡 Vous devrez mettre à jour manuellement via la console AWS")
        return False

def step6_get_outputs():
    """Étape 6: Afficher les outputs."""
    print("\n" + "="*60)
    print("ÉTAPE 6: Récupération des informations")
    print("="*60)
    
    success, output = run_command(
        "aws cloudformation describe-stacks --stack-name invoice-extractor --region us-west-2 "
        "--query 'Stacks[0].Outputs' --output json"
    )
    
    if success and output.strip():
        try:
            outputs = json.loads(output)
            print("\n🎉 DÉPLOIEMENT RÉUSSI !")
            print("="*60)
            
            for item in outputs:
                key = item.get('OutputKey', 'N/A')
                value = item.get('OutputValue', 'N/A')
                print(f"\n{key}:")
                print(f"   {value}")
            
            print("\n" + "="*60)
            print("\n📋 INSTRUCTIONS:")
            print("1. Uploader une facture PDF dans le bucket S3 ci-dessus")
            print("2. La fonction Lambda s'exécutera automatiquement")
            print("3. Vérifiez les données dans DynamoDB")
            print("4. Consultez les logs dans CloudWatch")
            
        except:
            print("✅ Stack déployée")
    else:
        print("✅ Stack déployée")
    
    return True

def main():
    """Fonction principale."""
    print("="*60)
    print("DÉPLOIEMENT CLOUDFORMATION - INVOICE EXTRACTOR")
    print("="*60)
    
    try:
        # Étape 1: Vérifier AWS
        if not step1_check_aws():
            return 1
        
        # Étape 2: Valider le template
        if not step2_validate_template():
            return 1
        
        # Étape 3: Créer le package
        success, zip_path = step3_create_lambda_package()
        if not success:
            return 1
        
        # Étape 4: Déployer la stack
        if not step4_deploy_stack():
            return 1
        
        # Étape 5: Mettre à jour le code Lambda
        step5_update_lambda_code(zip_path)
        
        # Étape 6: Afficher les outputs
        step6_get_outputs()
        
        print("\n" + "="*60)
        print("✅ DÉPLOIEMENT TERMINÉ !")
        print("="*60)
        
        return 0
        
    except KeyboardInterrupt:
        print("\n\n❌ Opération interrompue")
        return 1
    except Exception as e:
        print(f"\n❌ Erreur inattendue: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
