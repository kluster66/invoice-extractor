#!/usr/bin/env python3
"""
Configure facilement le modèle Bedrock à utiliser
"""

import os
import sys
import json
from pathlib import Path

# Ajouter les répertoires au path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))
sys.path.insert(0, str(current_dir / "src"))

from config.config import Config

def configure_model_interactive():
    """Configuration interactive du modèle"""
    print("CONFIGURATION DU MODÈLE BEDROCK")
    print("=" * 60)
    
    # Afficher le modèle actuel
    print(f"\nModèle actuel: {Config.BEDROCK_MODEL_ID}")
    
    # Afficher les modèles recommandés
    print("\nMODÈLES RECOMMANDÉS POUR L'EXTRACTION DE FACTURES:")
    print("-" * 60)
    
    recommendations = [
        ("claude-3-5-sonnet", "anthropic.claude-3-5-sonnet-20241022-v2:0", "Claude 3.5 Sonnet - Meilleure précision"),
        ("claude-3-haiku", "anthropic.claude-3-haiku-20240307-v1:0", "Claude 3 Haiku - Rapide et économique"),
        ("claude-3-opus", "anthropic.claude-3-opus-20240229-v1:0", "Claude 3 Opus - Très puissant"),
        ("llama-3-1-70b", "meta.llama3-1-70b-instruct-v1:0", "Llama 3.1 70B - Open source, bon rapport qualité/prix"),
        ("llama-3-2-90b", "meta.llama3-2-90b-instruct-v1:0", "Llama 3.2 90B - Très performant"),
        ("titan-text-express", "amazon.titan-text-express-v1", "Amazon Titan - Natif AWS"),
    ]
    
    for i, (key, model_id, description) in enumerate(recommendations, 1):
        print(f"{i}. {description}")
        print(f"   ID: {model_id}")
        print()
    
    print("7. Autre modèle (saisir l'ID complet)")
    print("8. Quitter")
    
    # Demander le choix
    while True:
        try:
            choice = input("\nVotre choix (1-8): ").strip()
            
            if choice == "8":
                print("Configuration annulée.")
                return False
            
            elif choice == "7":
                custom_model = input("Entrez l'ID complet du modèle (ex: anthropic.claude-3-5-sonnet-20241022-v2:0): ").strip()
                if custom_model:
                    # Mettre à jour la configuration
                    update_configuration(custom_model)
                    return True
                else:
                    print("ID de modèle invalide.")
            
            elif choice in ["1", "2", "3", "4", "5", "6"]:
                idx = int(choice) - 1
                selected_key, selected_model, description = recommendations[idx]
                
                print(f"\nVous avez sélectionné: {description}")
                print(f"ID du modèle: {selected_model}")
                
                confirm = input("Confirmer (o/n)? ").strip().lower()
                if confirm in ["o", "oui", "y", "yes"]:
                    # Mettre à jour la configuration
                    update_configuration(selected_model)
                    return True
                else:
                    print("Annulé.")
            
            else:
                print("Choix invalide. Veuillez entrer un nombre entre 1 et 8.")
                
        except KeyboardInterrupt:
            print("\n\nConfiguration annulée.")
            return False
        except Exception as e:
            print(f"Erreur: {e}")


def update_configuration(model_id: str):
    """Met à jour la configuration avec le nouveau modèle"""
    print(f"\nMise à jour de la configuration avec le modèle: {model_id}")
    print("-" * 60)
    
    # Options de configuration
    print("\nCHOIX DE CONFIGURATION:")
    print("1. Mettre à jour le fichier .env (recommandé)")
    print("2. Mettre à jour la configuration en mémoire (pour ce test seulement)")
    print("3. Afficher la commande pour variable d'environnement")
    print("4. Annuler")
    
    while True:
        try:
            choice = input("\nVotre choix (1-4): ").strip()
            
            if choice == "1":
                update_env_file(model_id)
                break
            elif choice == "2":
                Config.BEDROCK_MODEL_ID = model_id
                print(f"Modèle mis à jour en mémoire: {Config.BEDROCK_MODEL_ID}")
                print("Note: Ce changement n'est valable que pour cette session.")
                break
            elif choice == "3":
                print(f"\nCommande pour variable d'environnement:")
                print(f"export BEDROCK_MODEL_ID='{model_id}'")
                print(f"\nOu pour Windows PowerShell:")
                print(f"$env:BEDROCK_MODEL_ID='{model_id}'")
                print(f"\nOu pour Windows CMD:")
                print(f"set BEDROCK_MODEL_ID={model_id}")
                break
            elif choice == "4":
                print("Annulé.")
                return False
            else:
                print("Choix invalide.")
                
        except KeyboardInterrupt:
            print("\n\nAnnulé.")
            return False


def update_env_file(model_id: str):
    """Met à jour le fichier .env"""
    env_file = Path(".env")
    env_example = Path(".env.example")
    
    # Créer .env.example s'il n'existe pas
    if not env_example.exists():
        create_env_example()
    
    # Créer ou mettre à jour .env
    if not env_file.exists():
        print(f"Création du fichier {env_file}...")
        env_example.copy(env_file)
    
    # Lire le contenu
    with open(env_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Mettre à jour BEDROCK_MODEL_ID
    updated = False
    new_lines = []
    for line in lines:
        if line.strip().startswith("BEDROCK_MODEL_ID="):
            new_lines.append(f"BEDROCK_MODEL_ID={model_id}\n")
            updated = True
        else:
            new_lines.append(line)
    
    # Ajouter si non présent
    if not updated:
        new_lines.append(f"\n# Modèle Bedrock pour l'extraction de factures\nBEDROCK_MODEL_ID={model_id}\n")
    
    # Écrire le fichier
    with open(env_file, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
    
    print(f"Fichier {env_file} mis à jour avec BEDROCK_MODEL_ID={model_id}")
    print("\nPour appliquer la configuration:")
    print("1. Redémarrer l'application")
    print("2. Ou exécuter: from dotenv import load_dotenv; load_dotenv()")


def create_env_example():
    """Crée un fichier .env.example"""
    content = """# Configuration AWS
AWS_ACCESS_KEY_ID=votre_access_key_id
AWS_SECRET_ACCESS_KEY=votre_secret_access_key
AWS_REGION=us-west-2

# Configuration Bedrock
BEDROCK_MODEL_ID=anthropic.claude-3-5-sonnet-20241022-v2:0
BEDROCK_MAX_TOKENS=1000
BEDROCK_TEMPERATURE=0.1

# Configuration DynamoDB
DYNAMODB_TABLE_NAME=invoices
DYNAMODB_READ_CAPACITY=5
DYNAMODB_WRITE_CAPACITY=5

# Configuration S3
S3_INPUT_BUCKET=invoice-input-bucket
S3_PROCESSED_PREFIX=processed/
S3_ERROR_PREFIX=error/

# Configuration Application
LOG_LEVEL=INFO
MAX_PDF_SIZE_MB=50
TEMP_DIR=/tmp
EXTRACTION_TIMEOUT=300
MAX_RETRY_ATTEMPTS=3
"""
    
    with open(".env.example", 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("Fichier .env.example créé.")


def test_model_access(model_id: str):
    """Teste l'accès au modèle"""
    print(f"\nTest d'accès au modèle: {model_id}")
    print("-" * 40)
    
    try:
        import boto3
        from botocore.exceptions import ClientError
        
        bedrock = boto3.client('bedrock-runtime', region_name=Config.AWS_REGION)
        
        # Test avec un prompt simple
        test_prompt = "Bonjour, ceci est un test. Réponds simplement par 'TEST_OK'."
        
        # Essayer différents formats selon le modèle
        if "anthropic.claude" in model_id:
            # Format Anthropic Claude
            body = {
                "prompt": f"\n\nHuman: {test_prompt}\n\nAssistant:",
                "max_tokens_to_sample": 10,
                "temperature": 0.1
            }
        elif "meta.llama" in model_id:
            # Format Meta Llama
            body = {
                "prompt": test_prompt,
                "max_gen_len": 10,
                "temperature": 0.1
            }
        elif "amazon.titan" in model_id:
            # Format Amazon Titan
            body = {
                "inputText": test_prompt,
                "textGenerationConfig": {
                    "maxTokenCount": 10,
                    "temperature": 0.1
                }
            }
        else:
            # Format générique
            body = {
                "inputs": test_prompt,
                "parameters": {
                    "max_new_tokens": 10,
                    "temperature": 0.1
                }
            }
        
        response = bedrock.invoke_model(
            modelId=model_id,
            body=json.dumps(body).encode('utf-8')
        )
        
        response_body = json.loads(response['body'].read())
        print(f"SUCCÈS - Accès au modèle OK")
        print(f"Réponse: {response_body}")
        return True
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_msg = e.response['Error']['Message']
        
        print(f"ERREUR - {error_code}: {error_msg}")
        
        if error_code == "ResourceNotFoundException":
            print("\nACTION REQUISE:")
            print("1. Accédez à AWS Console > Bedrock > Model access")
            print(f"2. Demandez l'accès au modèle: {model_id}")
            print("3. Remplissez le formulaire de cas d'utilisation")
            print("4. Attendez l'approbation (généralement rapide)")
        
        return False
    except Exception as e:
        print(f"ERREUR - {str(e)}")
        return False


def main():
    """Fonction principale"""
    print("CONFIGURATEUR DE MODÈLE BEDROCK")
    print("=" * 60)
    
    # Vérifier les credentials
    if not Config.AWS_ACCESS_KEY_ID or not Config.AWS_SECRET_ACCESS_KEY:
        print("ATTENTION: Credentials AWS non configurés")
        print("Veuillez configurer AWS CLI ou créer un fichier .env")
        print("\nPour configurer AWS CLI:")
        print("  aws configure")
        return
    
    # Configuration interactive
    if configure_model_interactive():
        print(f"\n{'='*60}")
        print("CONFIGURATION TERMINÉE")
        print(f"{'='*60}")
        print(f"\nModèle configuré: {Config.BEDROCK_MODEL_ID}")
        print("\nProchaines étapes:")
        print("1. Testez l'accès au modèle (optionnel)")
        print("2. Testez l'extraction de facture")
        print("3. Déployez sur AWS")
        
        test = input("\nVoulez-vous tester l'accès au modèle (o/n)? ").strip().lower()
        if test in ["o", "oui", "y", "yes"]:
            test_model_access(Config.BEDROCK_MODEL_ID)


if __name__ == "__main__":
    main()
