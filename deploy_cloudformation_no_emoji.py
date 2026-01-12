#!/usr/bin/env python3
"""
Script de déploiement CloudFormation sans émojis
"""

import os
import sys
import subprocess
import json
import time

def run_command(cmd, description=""):
    """Exécuter une commande et afficher le résultat"""
    if description:
        print(f"\n[INFO] {description}")
    
    print(f"[CMD] {' '.join(cmd)}")
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding='utf-8'
        )
        
        if result.returncode == 0:
            if result.stdout.strip():
                print(f"[OK] Succès")
                if len(result.stdout) < 500:
                    print(result.stdout)
            return True, result.stdout
        else:
            print(f"[ERREUR] Échec")
            print(f"Stderr: {result.stderr}")
            return False, result.stderr
    except Exception as e:
        print(f"[ERREUR] Exception: {e}")
        return False, str(e)

def check_aws_cli():
    """Vérifier si AWS CLI est configuré"""
    print("=" * 60)
    print("VERIFICATION AWS CLI")
    print("=" * 60)
    
    success, output = run_command(
        ["aws", "sts", "get-caller-identity"],
        "Verification des credentials AWS"
    )
    
    if success:
        try:
            identity = json.loads(output)
            print(f"[OK] Compte AWS: {identity.get('Account')}")
            print(f"[OK] User ID: {identity.get('UserId')}")
            print(f"[OK] ARN: {identity.get('Arn')}")
            return True
        except:
            print("[OK] AWS CLI configuré")
            return True
    else:
        print("[ERREUR] AWS CLI non configuré ou erreur d'authentification")
        print("\nPour configurer AWS CLI:")
        print("  1. aws configure")
        print("  2. Entrer vos credentials AWS")
        print("  3. Region: us-west-2")
        return False

def get_region():
    """Obtenir la région AWS"""
    success, output = run_command(
        ["aws", "configure", "get", "region"],
        "Recuperation de la region AWS"
    )
    
    if success and output.strip():
        region = output.strip()
        print(f"[OK] Region AWS: {region}")
        return region
    else:
        print("[INFO] Utilisation de la region par défaut: us-west-2")
        return "us-west-2"

def validate_template(template_file):
    """Valider le template CloudFormation"""
    print("\n" + "=" * 60)
    print("VALIDATION DU TEMPLATE CLOUDFORMATION")
    print("=" * 60)
    
    region = get_region()
    
    # Vérifier si le fichier existe
    if not os.path.exists(template_file):
        print(f"[ERREUR] Fichier template non trouvé: {template_file}")
        return False
    
    print(f"[INFO] Template: {template_file}")
    
    success, output = run_command(
        [
            "aws", "cloudformation", "validate-template",
            "--template-body", f"file://{os.path.abspath(template_file)}",
            "--region", region
        ],
        "Validation du template CloudFormation"
    )
    
    if success:
        print("[OK] Template CloudFormation valide !")
        return True
    else:
        print("[ERREUR] Template invalide")
        
        # Afficher les premières lignes pour déboguer
        print("\n[DEBUG] Premières lignes du template:")
        try:
            with open(template_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                for i, line in enumerate(lines[:20], 1):
                    print(f"  {i:3}: {line.rstrip()}")
        except Exception as e:
            print(f"  Erreur lecture fichier: {e}")
        
        return False

def create_stack(template_file):
    """Créer la stack CloudFormation"""
    print("\n" + "=" * 60)
    print("CREATION DE LA STACK CLOUDFORMATION")
    print("=" * 60)
    
    region = get_region()
    timestamp = int(time.time())
    stack_name = "invoice-extractor-stack"
    
    # Générer un nom de bucket unique
    bucket_name = f"invoice-extractor-bucket-{timestamp}"
    
    print(f"[INFO] Stack: {stack_name}")
    print(f"[INFO] Region: {region}")
    print(f"[INFO] Bucket: {bucket_name}")
    print(f"[INFO] Modele: meta.llama3-1-70b-instruct-v1:0")
    
    # Demander confirmation
    print("\n[ATTENTION] Vous allez créer des ressources AWS facturables")
    confirm = input("Confirmez-vous la creation ? (oui/non): ").strip().lower()
    if confirm != "oui":
        print("[INFO] Creation annulee")
        return False
    
    # Paramètres
    parameters = [
        f"ParameterKey=EnvironmentName,ParameterValue=prod",
        f"ParameterKey=BucketName,ParameterValue={bucket_name}",
        f"ParameterKey=TableName,ParameterValue=invoices",
        f"ParameterKey=BedrockModelId,ParameterValue=meta.llama3-1-70b-instruct-v1:0"
    ]
    
    # Créer la stack
    cmd = [
        "aws", "cloudformation", "create-stack",
        "--stack-name", stack_name,
        "--template-body", f"file://{os.path.abspath(template_file)}",
        "--parameters"
    ] + parameters + [
        "--capabilities", "CAPABILITY_IAM",
        "--region", region,
        "--tags", "Key=Project,Value=InvoiceExtractor", "Key=Environment,Value=Production"
    ]
    
    success, output = run_command(cmd, "Creation de la stack CloudFormation")
    
    if success:
        try:
            response = json.loads(output)
            stack_id = response.get("StackId")
            print("[OK] Stack creee avec succes")
            print(f"[INFO] Stack ID: {stack_id}")
            
            # Attendre la création
            print("\n[INFO] Attente de la creation de la stack...")
            wait_for_stack(stack_name, region, "CREATE_COMPLETE")
            
            return True
        except:
            print("[OK] Stack creee")
            return True
    else:
        return False

def wait_for_stack(stack_name, region, expected_status):
    """Attendre qu'une stack atteigne un statut spécifique"""
    max_attempts = 60  # 30 minutes max
    
    for attempt in range(max_attempts):
        print(f"[INFO] Verification... (tentative {attempt + 1}/{max_attempts})")
        
        success, output = run_command(
            [
                "aws", "cloudformation", "describe-stacks",
                "--stack-name", stack_name,
                "--region", region
            ],
            ""
        )
        
        if success:
            try:
                stacks = json.loads(output).get("Stacks", [])
                if stacks:
                    stack = stacks[0]
                    status = stack.get("StackStatus")
                    print(f"[INFO] Statut: {status}")
                    
                    if status == expected_status:
                        print(f"[OK] Stack {expected_status} !")
                        
                        # Afficher les outputs
                        outputs = stack.get("Outputs", [])
                        if outputs:
                            print("\n[INFO] Outputs:")
                            for output in outputs:
                                key = output.get("OutputKey", "Unknown")
                                value = output.get("OutputValue", "")
                                print(f"  - {key}: {value}")
                        
                        return True
                    elif "FAILED" in status or "ROLLBACK" in status:
                        print(f"[ERREUR] Stack en echec: {status}")
                        
                        # Afficher les événements d'erreur
                        show_stack_events(stack_name, region)
                        return False
                
                time.sleep(30)  # Attendre 30 secondes
            except:
                time.sleep(30)
        else:
            time.sleep(30)
    
    print("[ERREUR] Timeout lors de l'attente de la stack")
    return False

def show_stack_events(stack_name, region):
    """Afficher les événements de la stack"""
    print("\n[DEBUG] Evenements recents de la stack:")
    
    success, output = run_command(
        [
            "aws", "cloudformation", "describe-stack-events",
            "--stack-name", stack_name,
            "--region", region,
            "--max-items", "10"
        ],
        ""
    )
    
    if success:
        try:
            events = json.loads(output).get("StackEvents", [])
            for event in events[:5]:  # 5 derniers événements
                resource = event.get("LogicalResourceId", "Unknown")
                status = event.get("ResourceStatus", "Unknown")
                reason = event.get("ResourceStatusReason", "")
                timestamp = event.get("Timestamp", "")
                
                if "FAILED" in status or "ROLLBACK" in status:
                    print(f"  [ERREUR] {resource}: {status}")
                    if reason:
                        print(f"     Raison: {reason}")
                else:
                    print(f"  [OK] {resource}: {status}")
        except:
            pass

def describe_stack():
    """Décrire la stack CloudFormation"""
    print("\n" + "=" * 60)
    print("DESCRIPTION DE LA STACK")
    print("=" * 60)
    
    region = get_region()
    stack_name = "invoice-extractor-stack"
    
    success, output = run_command(
        [
            "aws", "cloudformation", "describe-stacks",
            "--stack-name", stack_name,
            "--region", region
        ],
        f"Description de la stack {stack_name}"
    )
    
    if success:
        try:
            stacks = json.loads(output).get("Stacks", [])
            if stacks:
                stack = stacks[0]
                print(f"[INFO] Nom: {stack.get('StackName')}")
                print(f"[INFO] Statut: {stack.get('StackStatus')}")
                print(f"[INFO] Creee: {stack.get('CreationTime')}")
                
                # Outputs
                outputs = stack.get("Outputs", [])
                if outputs:
                    print("\n[INFO] Outputs:")
                    for output in outputs:
                        key = output.get("OutputKey")
                        value = output.get("OutputValue")
                        print(f"  - {key}: {value}")
                
                # Paramètres
                parameters = stack.get("Parameters", [])
                if parameters:
                    print("\n[INFO] Parametres:")
                    for param in parameters:
                        key = param.get("ParameterKey")
                        value = param.get("ParameterValue")
                        print(f"  - {key}: {value}")
            else:
                print("[INFO] Stack non trouvee")
        except:
            print("[OK] Stack existe")
    else:
        if "does not exist" in output:
            print("[INFO] Stack n'existe pas")
        else:
            print("[ERREUR] Erreur lors de la description")

def delete_stack():
    """Supprimer la stack CloudFormation"""
    print("\n" + "=" * 60)
    print("SUPPRESSION DE LA STACK")
    print("=" * 60)
    
    region = get_region()
    stack_name = "invoice-extractor-stack"
    
    print(f"[INFO] Stack a supprimer: {stack_name}")
    print(f"[INFO] Region: {region}")
    
    # Demander confirmation
    print("\n[ATTENTION] Vous allez supprimer toutes les ressources AWS")
    confirm = input("Confirmez-vous la suppression ? (oui/non): ").strip().lower()
    if confirm != "oui":
        print("[INFO] Suppression annulee")
        return False
    
    success, output = run_command(
        [
            "aws", "cloudformation", "delete-stack",
            "--stack-name", stack_name,
            "--region", region
        ],
        "Suppression de la stack"
    )
    
    if success:
        print("[OK] Commande de suppression envoyee")
        print("[INFO] La suppression peut prendre quelques minutes...")
        return True
    else:
        return False

def main():
    """Fonction principale"""
    print("=" * 60)
    print("DEPLOIEMENT INVOICE EXTRACTOR - CLOUDFORMATION")
    print("=" * 60)
    
    # Vérifier AWS CLI
    if not check_aws_cli():
        sys.exit(1)
    
    # Choisir le template
    template_file = "cloudformation-template-simple.yaml"
    if not os.path.exists(template_file):
        template_file = "cloudformation-template.yaml"
    
    print(f"\n[INFO] Template selectionne: {template_file}")
    
    # Menu principal
    while True:
        print("\n" + "=" * 60)
        print("MENU PRINCIPAL")
        print("=" * 60)
        print("1. Valider le template")
        print("2. Creer la stack")
        print("3. Decrire la stack")
        print("4. Supprimer la stack")
        print("0. Quitter")
        print("=" * 60)
        
        choice = input("\nChoisissez une option (0-4): ").strip()
        
        if choice == "1":
            validate_template(template_file)
        elif choice == "2":
            create_stack(template_file)
        elif choice == "3":
            describe_stack()
        elif choice == "4":
            delete_stack()
        elif choice == "0":
            print("\n[INFO] Au revoir !")
            break
        else:
            print("[ERREUR] Option invalide")

if __name__ == "__main__":
    main()
