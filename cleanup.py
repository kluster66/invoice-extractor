#!/usr/bin/env python3
"""
Script de nettoyage AWS pour Invoice Extractor.
Supprime toutes les ressources AWS créées par le déploiement.
"""

import subprocess
import sys
import json
import time

def run_command(command):
    """Exécute une commande shell."""
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)

def cleanup_cloudformation():
    """Nettoie la stack CloudFormation."""
    print("\n1. Nettoyage de la stack CloudFormation...")
    
    stack_name = "invoice-extractor"
    region = "us-west-2"
    
    # Vérifier si la stack existe
    success, output, error = run_command(
        f"aws cloudformation describe-stacks --stack-name {stack_name} --region {region}"
    )
    
    if not success:
        print("   INFO: Stack non trouvee")
        return True
    
    print(f"   Stack trouvee: {stack_name}")
    
    # Vider les buckets S3 avant suppression
    print("   Vidage des buckets S3...")
    
    # Récupérer les outputs
    success, outputs, error = run_command(
        f"aws cloudformation describe-stacks --stack-name {stack_name} --region {region} "
        f"--query 'Stacks[0].Outputs' --output json"
    )
    
    if success and outputs.strip():
        try:
            outputs_list = json.loads(outputs)
            for output_item in outputs_list:
                key = output_item.get('OutputKey', '')
                value = output_item.get('OutputValue', '')
                
                if key in ['BucketName', 'DeploymentBucketName'] and value:
                    print(f"   Vidage du bucket: {value}")
                    run_command(f"aws s3 rm s3://{value} --recursive --region {region}")
        except:
            pass
    
    # Supprimer la stack
    print("   Suppression de la stack...")
    success, output, error = run_command(
        f"aws cloudformation delete-stack --stack-name {stack_name} --region {region}"
    )
    
    if success:
        print("   OK: Suppression initiee")
        
        # Attendre
        print("   Attente de la suppression...")
        run_command(
            f"aws cloudformation wait stack-delete-complete --stack-name {stack_name} --region {region}"
        )
        
        print("   OK: Stack supprimee")
        return True
    else:
        print(f"   ERREUR: {error}")
        return False

def cleanup_s3_buckets():
    """Nettoie les buckets S3."""
    print("\n2. Nettoyage des buckets S3...")
    
    region = "us-west-2"
    
    # Lister les buckets
    success, output, error = run_command(
        f"aws s3api list-buckets --region {region} --query 'Buckets[?contains(Name, \"invoice-extractor\")].Name' --output json"
    )
    
    if not success or not output.strip() or output.strip() == '[]':
        print("   INFO: Aucun bucket trouve")
        return True
    
    try:
        buckets = json.loads(output)
        for bucket in buckets:
            print(f"   Suppression du bucket: {bucket}")
            
            # Vider le bucket
            run_command(f"aws s3 rm s3://{bucket} --recursive --region {region}")
            
            # Supprimer le bucket
            success, _, _ = run_command(
                f"aws s3api delete-bucket --bucket {bucket} --region {region}"
            )
            
            if success:
                print(f"   OK: Bucket supprime: {bucket}")
            else:
                print(f"   ATTENTION: Impossible de supprimer: {bucket}")
        
        return True
    except:
        print("   INFO: Aucun bucket a supprimer")
        return True

def cleanup_dynamodb_tables():
    """Nettoie les tables DynamoDB."""
    print("\n3. Nettoyage des tables DynamoDB...")
    
    region = "us-west-2"
    
    # Lister les tables
    success, output, error = run_command(
        f"aws dynamodb list-tables --region {region} --query 'TableNames[?contains(@, \"invoice\")]' --output json"
    )
    
    if not success or not output.strip() or output.strip() == '[]':
        print("   INFO: Aucune table trouvee")
        return True
    
    try:
        tables = json.loads(output)
        for table in tables:
            print(f"   Suppression de la table: {table}")
            
            success, _, _ = run_command(
                f"aws dynamodb delete-table --table-name {table} --region {region}"
            )
            
            if success:
                print(f"   OK: Table supprimee: {table}")
            else:
                print(f"   ATTENTION: Impossible de supprimer: {table}")
        
        return True
    except:
        print("   INFO: Aucune table a supprimer")
        return True

def cleanup_lambda_functions():
    """Nettoie les fonctions Lambda."""
    print("\n4. Nettoyage des fonctions Lambda...")
    
    region = "us-west-2"
    
    # Lister les fonctions
    success, output, error = run_command(
        f"aws lambda list-functions --region {region} --query 'Functions[?contains(FunctionName, \"invoice-extractor\")].FunctionName' --output json"
    )
    
    if not success or not output.strip() or output.strip() == '[]':
        print("   INFO: Aucune fonction trouvee")
        return True
    
    try:
        functions = json.loads(output)
        for function in functions:
            print(f"   Suppression de la fonction: {function}")
            
            success, _, _ = run_command(
                f"aws lambda delete-function --function-name {function} --region {region}"
            )
            
            if success:
                print(f"   OK: Fonction supprimee: {function}")
            else:
                print(f"   ATTENTION: Impossible de supprimer: {function}")
        
        return True
    except:
        print("   INFO: Aucune fonction a supprimer")
        return True

def cleanup_cloudwatch_logs():
    """Nettoie les groupes de logs CloudWatch."""
    print("\n5. Nettoyage des groupes de logs CloudWatch...")
    
    region = "us-west-2"
    
    # Lister les groupes de logs
    success, output, error = run_command(
        f"aws logs describe-log-groups --region {region} --query 'logGroups[?contains(logGroupName, \"invoice-extractor\")].logGroupName' --output json"
    )
    
    if not success or not output.strip() or output.strip() == '[]':
        print("   INFO: Aucun groupe de logs trouve")
        return True
    
    try:
        log_groups = json.loads(output)
        for log_group in log_groups:
            print(f"   Suppression du groupe de logs: {log_group}")
            
            success, _, _ = run_command(
                f"aws logs delete-log-group --log-group-name {log_group} --region {region}"
            )
            
            if success:
                print(f"   OK: Groupe de logs supprime: {log_group}")
            else:
                print(f"   ATTENTION: Impossible de supprimer: {log_group}")
        
        return True
    except:
        print("   INFO: Aucun groupe de logs a supprimer")
        return True

def main():
    """Fonction principale."""
    print("=" * 60)
    print("NETTOYAGE AWS - INVOICE EXTRACTOR")
    print("=" * 60)
    
    try:
        # Vérifier AWS CLI
        print("\nVerification de la configuration AWS...")
        success, output, error = run_command("aws sts get-caller-identity")
        if not success:
            print("ERREUR: AWS CLI non configure ou credentials invalides")
            print("CONSEIL: Executez 'aws configure' pour configurer AWS CLI")
            return 1
        
        # Nettoyer toutes les ressources
        all_success = True
        
        all_success &= cleanup_cloudformation()
        all_success &= cleanup_s3_buckets()
        all_success &= cleanup_dynamodb_tables()
        all_success &= cleanup_lambda_functions()
        all_success &= cleanup_cloudwatch_logs()
        
        print("\n" + "=" * 60)
        
        if all_success:
            print("OK: NETTOYAGE TERMINE AVEC SUCCES !")
            print("\nResume :")
            print("- Stack CloudFormation supprimee")
            print("- Buckets S3 supprimes")
            print("- Tables DynamoDB supprimees")
            print("- Fonctions Lambda supprimees")
            print("- Groupes de logs CloudWatch supprimes")
            print("\nVous pouvez maintenant redeployer avec : python deploy.py")
        else:
            print("ATTENTION: NETTOYAGE PARTIEL")
            print("\nCertaines ressources n'ont pas pu etre supprimees.")
            print("Verifiez manuellement dans la console AWS.")
        
        print("\n" + "=" * 60)
        
        return 0 if all_success else 1
        
    except KeyboardInterrupt:
        print("\n\nERREUR: Nettoyage interrompu par l'utilisateur")
        return 1
    except Exception as e:
        print(f"\nERREUR: Erreur inattendue: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
