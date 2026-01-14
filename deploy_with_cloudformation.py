#!/usr/bin/env python3
"""
Script de déploiement CloudFormation pour l'outil d'extraction de factures.
Ce script déploie la stack CloudFormation avec toutes les ressources AWS nécessaires.
"""

import subprocess
import sys
import json
import time
import os
from pathlib import Path

def run_command(command, description=None):
    """Exécute une commande shell et retourne le résultat."""
    if description:
        print(f"\n🔧 {description}...")
    
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
            print(f"⚠️  Commande échouée: {command}")
            if result.stderr:
                print(f"Erreur: {result.stderr[:500]}")
            return False, result.stderr
        
        return True, result.stdout
    
    except Exception as e:
        print(f"❌ Exception: {e}")
        return False, str(e)

def check_aws_cli():
    """Vérifie que AWS CLI est configuré."""
    print("🔍 Vérification de la configuration AWS...")
    
    success, output = run_command("aws sts get-caller-identity")
    if not success:
        print("❌ AWS CLI n'est pas configuré ou les credentials sont invalides.")
        print("💡 Exécutez 'aws configure' pour configurer vos credentials.")
        return False
    
    # Extraire l'ID du compte
    try:
        identity = json.loads(output)
        account_id = identity.get('Account', 'N/A')
        user_arn = identity.get('Arn', 'N/A')
        print(f"✅ AWS CLI configuré - Compte: {account_id}")
        print(f"   Utilisateur: {user_arn}")
        return True
    except:
        print("✅ AWS CLI configuré")
        return True

def validate_template():
    """Valide le template CloudFormation."""
    print("\n📋 Validation du template CloudFormation...")
    
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

def check_bedrock_access():
    """Vérifie l'accès à AWS Bedrock."""
    print("\n🤖 Vérification de l'accès à AWS Bedrock...")
    
    success, output = run_command(
        "aws bedrock list-foundation-models --region us-west-2 --query 'modelSummaries[].modelId' --output json"
    )
    
    if success:
        try:
            models = json.loads(output)
            if models:
                print(f"✅ Accès Bedrock OK - {len(models)} modèles disponibles")
                
                # Afficher quelques modèles populaires
                popular_models = [
                    "anthropic.claude-3-5-sonnet",
                    "meta.llama3-1-70b-instruct",
                    "amazon.titan-text-express"
                ]
                
                available_popular = []
                for model in popular_models:
                    if any(model in m for m in models):
                        available_popular.append(model)
                
                if available_popular:
                    print(f"   Modèles populaires disponibles: {', '.join(available_popular)}")
                return True
            else:
                print("⚠️  Aucun modèle Bedrock trouvé")
                return False
        except:
            print("✅ Accès Bedrock OK")
            return True
    else:
        print("⚠️  Impossible d'accéder à Bedrock. Vérifiez les permissions IAM.")
        print("💡 Vous devrez peut-être activer Bedrock dans la console AWS.")
        return True  # Continuer quand même, l'utilisateur pourra activer plus tard

def create_lambda_package():
    """Crée le package ZIP pour la fonction Lambda."""
    print("\n📦 Création du package Lambda...")
    
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
            print(f"❌ Répertoire source non trouvé: {src_dir}")
            return False
        
        import shutil
        for item in os.listdir(src_dir):
            src_path = os.path.join(src_dir, item)
            dst_path = os.path.join(package_dir, item)
            
            if os.path.isfile(src_path):
                shutil.copy2(src_path, dst_path)
            elif os.path.isdir(src_path):
                shutil.copytree(src_path, dst_path, dirs_exist_ok=True)
        
        print(f"✅ Code source copié depuis {src_dir}")
        
        # Créer le fichier ZIP
        import zipfile
        zip_path = "invoice-extractor-lambda.zip"
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(package_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, package_dir)
                    zipf.write(file_path, arcname)
        
        print(f"✅ Package ZIP créé: {zip_path} ({os.path.getsize(zip_path) / 1024 / 1024:.2f} MB)")
        
        # Nettoyer
        shutil.rmtree(package_dir)
        
        return True, zip_path
    
    except Exception as e:
        print(f"❌ Erreur lors de la création du package: {e}")
        return False, None

def upload_lambda_code(bucket_name, zip_path):
    """Upload le code Lambda vers S3."""
    print(f"\n⬆️  Upload du code Lambda vers S3: {bucket_name}...")
    
    success, output = run_command(
        f"aws s3 cp {zip_path} s3://{bucket_name}/invoice-extractor-lambda.zip --region us-west-2"
    )
    
    if success:
        print("✅ Code Lambda uploadé vers S3")
        return True
    else:
        print("❌ Échec de l'upload vers S3")
        return False

def deploy_stack():
    """Déploie la stack CloudFormation."""
    print("\n🚀 Déploiement de la stack CloudFormation...")
    
    stack_name = "invoice-extractor"
    template_path = "cloudformation-template-final.yaml"
    
    # Vérifier si la stack existe déjà
    success, output = run_command(
        f"aws cloudformation describe-stacks --stack-name {stack_name} --region us-west-2",
        "Vérification de l'existence de la stack"
    )
    
    if success:
        # Stack existe, demander confirmation pour mise à jour
        print(f"⚠️  La stack '{stack_name}' existe déjà.")
        response = input("Voulez-vous la mettre à jour? (oui/non): ")
        
        if response.lower() != 'oui':
            print("❌ Déploiement annulé")
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
    
    print(f"\n🔨 {action.capitalize()} de la stack '{stack_name}'...")
    success, output = run_command(cmd)
    
    if not success:
        print(f"❌ Échec de la {action} de la stack")
        return False
    
    print(f"✅ Commande de {action} envoyée avec succès")
    
    # Attendre la complétion
    print(f"\n⏳ Attente de la {action} de la stack...")
    
    wait_cmd = f"aws cloudformation wait stack-{command.replace('stack', '')}-complete " \
               f"--stack-name {stack_name} --region us-west-2"
    
    success, output = run_command(wait_cmd)
    
    if success:
        print(f"✅ Stack {action}ée avec succès")
        return True
    else:
        print(f"⚠️  La {action} de la stack a pris trop de temps ou a échoué")
        print("💡 Vérifiez l'état dans la console CloudFormation")
        return True  # Retourner True quand même pour afficher les outputs

def get_stack_outputs():
    """Récupère les outputs de la stack CloudFormation."""
    print("\n📊 Récupération des informations de déploiement...")
    
    stack_name = "invoice-extractor"
    
    success, output = run_command(
        f"aws cloudformation describe-stacks --stack-name {stack_name} --region us-west-2 "
        f"--query 'Stacks[0].Outputs' --output json"
    )
    
    if success and output.strip():
        try:
            outputs = json.loads(output)
            print("\n🎉 DÉPLOIEMENT RÉUSSI !")
            print("=" * 50)
            
            for item in outputs:
                key = item.get('OutputKey', 'N/A')
                value = item.get('OutputValue', 'N/A')
                description = item.get('Description', '')
                
                print(f"\n🔗 {key}:")
                print(f"   {value}")
                if description:
                    print(f"   📝 {description}")
            
            print("\n" + "=" * 50)
            
            # Afficher les instructions d'utilisation
            print("\n📋 INSTRUCTIONS D'UTILISATION:")
            print("1. Uploader une facture PDF dans le bucket S3")
            print("2. La fonction Lambda s'exécutera automatiquement")
            print("3. Vérifier les données extraites dans DynamoDB")
            print("4. Consulter les logs dans CloudWatch")
            
            return True
            
        except json.JSONDecodeError:
            print("⚠️  Impossible de parser les outputs JSON")
            return True
    else:
        print("ℹ️  Aucun output trouvé pour la stack")
        return True

def test_deployment():
    """Teste le déploiement en uploadant un fichier de test."""
    print("\n🧪 Test du déploiement...")
    
    # Récupérer le nom du bucket depuis les outputs
    success, output = run_command(
        "aws cloudformation describe-stacks --stack-name invoice-extractor --region us-west-2 "
        "--query 'Stacks[0].Outputs[?OutputKey==`InvoiceBucketName`].OutputValue' --output text"
    )
    
    if success and output.strip():
        bucket_name = output.strip()
        print(f"📦 Bucket S3: {bucket_name}")
        
        # Vérifier s'il y a un fichier de test
        test_file = "test_factures/2140 1902095741 210515 TELEFONICA MG PLVT.pdf"
        if os.path.exists(test_file):
            print(f"📄 Fichier de test trouvé: {test_file}")
            
            response = input("Voulez-vous uploader ce fichier pour tester? (oui/non): ")
            if response.lower() == 'oui':
                print(f"\n⬆️  Upload du fichier de test vers S3...")
                
                success, upload_output = run_command(
                    f'aws s3 cp "{test_file}" s3://{bucket_name}/ --region us-west-2'
                )
                
                if success:
                    print("✅ Fichier uploadé avec succès")
                    print("\n⏳ La fonction Lambda devrait s'exécuter dans quelques secondes...")
                    print("💡 Vérifiez les logs CloudWatch pour voir l'extraction")
                else:
                    print("❌ Échec de l'upload du fichier")
        else:
            print("ℹ️  Aucun fichier de test trouvé")
    else:
        print("ℹ️  Impossible de récupérer le nom du bucket")

def main():
    """Fonction principale."""
    print("=" * 60)
    print("🚀 DÉPLOIEMENT CLOUDFORMATION - Invoice Extractor")
    print("=" * 60)
    
    # Vérifier les prérequis
    if not check_aws_cli():
        return 1
    
    # Menu principal
    print("\n📋 MENU DE DÉPLOIEMENT:")
    print("1. Valider le template CloudFormation")
    print("2. Vérifier l'accès à AWS Bedrock")
    print("3. Créer le package Lambda")
    print("4. Déployer la stack complète")
    print("5. Tester le déploiement")
    print("6. Tout faire (recommandé)")
    print("0. Quitter")
    
    try:
        choice = input("\n👉 Votre choix: ")
        
        if choice == "0":
            print("👋 Au revoir!")
            return 0
        
        elif choice == "1":
            validate_template()
            
        elif choice == "2":
            check_bedrock_access()
            
        elif choice == "3":
            success, zip_path = create_lambda_package()
            if success:
                print(f"\n💡 Le package est prêt: {zip_path}")
                print("   Vous pouvez maintenant déployer la stack (option 4)")
            
        elif choice == "4":
            # Valider d'abord
            if not validate_template():
                print("❌ Impossible de déployer un template invalide")
                return 1
            
            # Créer le package
            success, zip_path = create_lambda_package()
            if not success:
                print("❌ Impossible de créer le package Lambda")
                return 1
            
            # Déployer la stack
            if deploy_stack():
                get_stack_outputs()
            
        elif choice == "5":
            test_deployment()
            
        elif choice == "6":
            # Tout faire en séquence
            print("\n🔨 LANCEMENT DU DÉPLOIEMENT COMPLET...")
            
            # 1. Vérifier AWS CLI
            if not check_aws_cli():
                return 1
            
            # 2. Valider le template
            if not validate_template():
                return 1
            
            # 3. Vérifier Bedrock (avertissement seulement)
            check_bedrock_access()
            
            # 4. Créer le package
            success, zip_path = create_lambda_package()
            if not success:
                return 1
            
            # 5. Déployer la stack
            if deploy_stack():
                # 6. Afficher les outputs
                get_stack_outputs()
                
                # 7. Tester
                response = input("\n🧪 Voulez-vous tester avec un fichier de test? (oui/non): ")
                if response.lower() == 'oui':
                    test_deployment()
            
        else:
            print("❌ Choix invalide")
            return 1
        
        print("\n✅ Opération terminée")
        return 0
        
    except KeyboardInterrupt:
        print("\n\n❌ Opération interrompue par l'utilisateur")
        return 1
    except Exception as e:
        print(f"\n❌ Erreur inattendue: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
