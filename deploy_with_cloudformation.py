#!/usr/bin/env python3
"""
Script de déploiement avec CloudFormation (sans CDK ni SAM)
"""

import os
import sys
import subprocess
import json
import time
from pathlib import Path

def check_aws_cli():
    """Vérifier si AWS CLI est installé et configuré"""
    try:
        result = subprocess.run(
            ["aws", "sts", "get-caller-identity"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            print("[OK] AWS CLI configuré")
            identity = json.loads(result.stdout)
            print(f"  Compte: {identity.get('Account')}")
            print(f"  UserId: {identity.get('UserId')}")
            print(f"  ARN: {identity.get('Arn')}")
            return True
        else:
            print("[ERREUR] AWS CLI non configuré ou erreur d'authentification")
            print(f"Erreur: {result.stderr}")
            return False
    except FileNotFoundError:
        print("[ERREUR] AWS CLI non installé")
        print("Installez AWS CLI: https://aws.amazon.com/cli/")
        return False

def get_aws_region():
    """Obtenir la région AWS configurée"""
    try:
        result = subprocess.run(
            ["aws", "configure", "get", "region"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            region = result.stdout.strip()
            print(f"[INFO] Région AWS: {region}")
            return region
        else:
            print("[INFO] Utilisation de la région par défaut: us-west-2")
            return "us-west-2"
    except:
        return "us-west-2"

def validate_template():
    """Valider le template CloudFormation"""
    print("[INFO] Validation du template CloudFormation...")
    region = get_aws_region()
    
    try:
        result = subprocess.run(
            [
                "aws", "cloudformation", "validate-template",
                "--template-body", f"file://{os.path.abspath('cloudformation-template.yaml')}",
                "--region", region
            ],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print("[OK] Template CloudFormation valide")
            return True
        else:
            print("[ERREUR] Template invalide")
            print(f"Erreur: {result.stderr}")
            return False
    except FileNotFoundError:
        print("[ERREUR] AWS CLI non trouvé")
        return False

def create_stack():
    """Créer la stack CloudFormation"""
    print("[INFO] Création de la stack CloudFormation...")
    region = get_aws_region()
    
    stack_name = "invoice-extractor-stack"
    
    # Paramètres
    parameters = [
        f"ParameterKey=EnvironmentName,ParameterValue=prod",
        f"ParameterKey=BucketName,ParameterValue=invoice-extractor-bucket-{int(time.time())}",
        f"ParameterKey=TableName,ParameterValue=invoices",
        f"ParameterKey=BedrockModelId,ParameterValue=meta.llama3-1-70b-instruct-v1:0",
        f"ParameterKey=LambdaMemory,ParameterValue=1024",
        f"ParameterKey=LambdaTimeout,ParameterValue=300"
    ]
    
    try:
        print(f"[INFO] Création de la stack: {stack_name}")
        print(f"[INFO] Région: {region}")
        
        cmd = [
            "aws", "cloudformation", "create-stack",
            "--stack-name", stack_name,
            "--template-body", f"file://{os.path.abspath('cloudformation-template.yaml')}",
            "--parameters"
        ] + parameters + [
            "--capabilities", "CAPABILITY_IAM",
            "--region", region,
            "--tags", "Key=Project,Value=InvoiceExtractor", "Key=Environment,Value=Production"
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            response = json.loads(result.stdout)
            stack_id = response.get("StackId")
            print(f"[OK] Stack créée avec succès")
            print(f"[INFO] Stack ID: {stack_id}")
            print(f"[INFO] Vérifiez le statut avec: aws cloudformation describe-stacks --stack-name {stack_name}")
            
            # Attendre la création
            print("[INFO] Attente de la création de la stack...")
            wait_for_stack(stack_name, "CREATE_COMPLETE")
            return True
        else:
            print("[ERREUR] Erreur lors de la création de la stack")
            print(f"Erreur: {result.stderr}")
            return False
    except Exception as e:
        print(f"[ERREUR] Exception: {e}")
        return False

def update_stack():
    """Mettre à jour la stack CloudFormation"""
    print("[INFO] Mise à jour de la stack CloudFormation...")
    region = get_aws_region()
    
    stack_name = "invoice-extractor-stack"
    
    # Paramètres (mêmes que pour la création)
    parameters = [
        f"ParameterKey=EnvironmentName,ParameterValue=prod",
        f"ParameterKey=BucketName,UsePreviousValue=true",
        f"ParameterKey=TableName,ParameterValue=invoices",
        f"ParameterKey=BedrockModelId,ParameterValue=meta.llama3-1-70b-instruct-v1:0",
        f"ParameterKey=LambdaMemory,ParameterValue=1024",
        f"ParameterKey=LambdaTimeout,ParameterValue=300"
    ]
    
    try:
        print(f"[INFO] Mise à jour de la stack: {stack_name}")
        
        cmd = [
            "aws", "cloudformation", "update-stack",
            "--stack-name", stack_name,
            "--template-body", f"file://{os.path.abspath('cloudformation-template.yaml')}",
            "--parameters"
        ] + parameters + [
            "--capabilities", "CAPABILITY_IAM",
            "--region", region
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            response = json.loads(result.stdout)
            stack_id = response.get("StackId")
            print(f"[OK] Stack mise à jour avec succès")
            print(f"[INFO] Stack ID: {stack_id}")
            
            # Attendre la mise à jour
            print("[INFO] Attente de la mise à jour de la stack...")
            wait_for_stack(stack_name, "UPDATE_COMPLETE")
            return True
        else:
            # Si la stack n'existe pas, on la crée
            if "does not exist" in result.stderr:
                print("[INFO] Stack n'existe pas, création...")
                return create_stack()
            elif "No updates are to be performed" in result.stderr:
                print("[INFO] Aucune mise à jour nécessaire")
                return True
            else:
                print("[ERREUR] Erreur lors de la mise à jour")
                print(f"Erreur: {result.stderr}")
                return False
    except Exception as e:
        print(f"[ERREUR] Exception: {e}")
        return False

def wait_for_stack(stack_name, expected_status):
    """Attendre qu'une stack atteigne un statut spécifique"""
    region = get_aws_region()
    max_attempts = 60  # 30 minutes max (30s * 60)
    
    for attempt in range(max_attempts):
        try:
            result = subprocess.run(
                [
                    "aws", "cloudformation", "describe-stacks",
                    "--stack-name", stack_name,
                    "--region", region
                ],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                stacks = json.loads(result.stdout).get("Stacks", [])
                if stacks:
                    stack_status = stacks[0].get("StackStatus")
                    print(f"[INFO] Statut de la stack: {stack_status} (tentative {attempt + 1}/{max_attempts})")
                    
                    if stack_status == expected_status:
                        print(f"[OK] Stack {expected_status}")
                        return True
                    elif "FAILED" in stack_status or "ROLLBACK" in stack_status:
                        print(f"[ERREUR] Stack en échec: {stack_status}")
                        return False
                    
                    # Vérifier les événements récents
                    if attempt % 5 == 0:  # Toutes les 5 tentatives
                        show_recent_events(stack_name)
                
                time.sleep(30)  # Attendre 30 secondes
            else:
                print(f"[INFO] En attente... (tentative {attempt + 1}/{max_attempts})")
                time.sleep(30)
                
        except Exception as e:
            print(f"[INFO] En attente... (tentative {attempt + 1}/{max_attempts})")
            time.sleep(30)
    
    print("[ERREUR] Timeout lors de l'attente de la stack")
    return False

def show_recent_events(stack_name):
    """Afficher les événements récents de la stack"""
    region = get_aws_region()
    
    try:
        result = subprocess.run(
            [
                "aws", "cloudformation", "describe-stack-events",
                "--stack-name", stack_name,
                "--region", region,
                "--max-items", "5"
            ],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            events = json.loads(result.stdout).get("StackEvents", [])
            print("[INFO] Événements récents:")
            for event in events[:3]:  # 3 derniers événements
                resource = event.get("LogicalResourceId", "Unknown")
                status = event.get("ResourceStatus", "Unknown")
                reason = event.get("ResourceStatusReason", "")
                print(f"  - {resource}: {status} {reason}")
    except:
        pass  # Ignorer les erreurs

def delete_stack():
    """Supprimer la stack CloudFormation"""
    print("[INFO] Suppression de la stack CloudFormation...")
    region = get_aws_region()
    
    stack_name = "invoice-extractor-stack"
    
    try:
        print(f"[INFO] Suppression de la stack: {stack_name}")
        
        result = subprocess.run(
            [
                "aws", "cloudformation", "delete-stack",
                "--stack-name", stack_name,
                "--region", region
            ],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print("[OK] Commande de suppression envoyée")
            print("[INFO] La suppression peut prendre quelques minutes...")
            return True
        else:
            print("[ERREUR] Erreur lors de la suppression")
            print(f"Erreur: {result.stderr}")
            return False
    except Exception as e:
        print(f"[ERREUR] Exception: {e}")
        return False

def describe_stack():
    """Décrire la stack CloudFormation"""
    print("[INFO] Description de la stack CloudFormation...")
    region = get_aws_region()
    
    stack_name = "invoice-extractor-stack"
    
    try:
        result = subprocess.run(
            [
                "aws", "cloudformation", "describe-stacks",
                "--stack-name", stack_name,
                "--region", region
            ],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            stacks = json.loads(result.stdout).get("Stacks", [])
            if stacks:
                stack = stacks[0]
                print(f"[INFO] Stack: {stack.get('StackName')}")
                print(f"[INFO] Statut: {stack.get('StackStatus')}")
                print(f"[INFO] Créée: {stack.get('CreationTime')}")
                
                # Afficher les outputs
                outputs = stack.get("Outputs", [])
                if outputs:
                    print("[INFO] Outputs:")
                    for output in outputs:
                        print(f"  - {output.get('OutputKey')}: {output.get('OutputValue')}")
                
                # Afficher les paramètres
                parameters = stack.get("Parameters", [])
                if parameters:
                    print("[INFO] Paramètres:")
                    for param in parameters:
                        print(f"  - {param.get('ParameterKey')}: {param.get('ParameterValue')}")
            else:
                print("[INFO] Stack non trouvée")
            return True
        else:
            if "does not exist" in result.stderr:
                print("[INFO] Stack n'existe pas")
            else:
                print("[ERREUR] Erreur lors de la description")
                print(f"Erreur: {result.stderr}")
            return False
    except Exception as e:
        print(f"[ERREUR] Exception: {e}")
        return False

def main():
    """Fonction principale"""
    print("=" * 60)
    print("DÉPLOIEMENT INVOICE EXTRACTOR AVEC CLOUDFORMATION")
    print("=" * 60)
    
    # Vérifier les prérequis
    if not check_aws_cli():
        sys.exit(1)
    
    # Menu principal
    while True:
        print("\n" + "=" * 60)
        print("MENU PRINCIPAL - CLOUDFORMATION")
        print("=" * 60)
        print("1. Valider le template")
        print("2. Créer la stack")
        print("3. Mettre à jour la stack")
        print("4. Décrire la stack")
        print("5. Supprimer la stack")
        print("0. Quitter")
        print("=" * 60)
        
        choice = input("\nChoisissez une option (0-5): ").strip()
        
        if choice == "1":
            validate_template()
        elif choice == "2":
            print("\n[ATTENTION] Vous allez créer des ressources AWS facturables")
            confirm = input("Confirmez-vous la création ? (oui/non): ").strip().lower()
            if confirm == "oui":
                create_stack()
        elif choice == "3":
            print("\n[ATTENTION] Vous allez mettre à jour des ressources AWS")
            confirm = input("Confirmez-vous la mise à jour ? (oui/non): ").strip().lower()
            if confirm == "oui":
                update_stack()
        elif choice == "4":
            describe_stack()
        elif choice == "5":
            print("\n[ATTENTION] Vous allez supprimer toutes les ressources AWS")
            confirm = input("Confirmez-vous la suppression ? (oui/non): ").strip().lower()
            if confirm == "oui":
                delete_stack()
        elif choice == "0":
            print("Au revoir !")
            break
        else:
            print("Option invalide")

if __name__ == "__main__":
    main()
