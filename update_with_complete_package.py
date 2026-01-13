#!/usr/bin/env python3
"""
Met à jour Lambda avec le package complet
"""

import boto3
import json
import time
from pathlib import Path

def update_lambda():
    """Met à jour la fonction Lambda"""
    
    region = "us-west-2"
    function_name = "invoice-extractor-prod"
    
    print(f"Mise à jour de la fonction Lambda: {function_name} dans {region}")
    
    lambda_client = boto3.client('lambda', region_name=region)
    
    # Vérifier que la fonction existe
    try:
        response = lambda_client.get_function(FunctionName=function_name)
        print(f"[OK] Fonction trouvée: {function_name}")
    except Exception as e:
        print(f"[ERREUR] Fonction non trouvée: {e}")
        return
    
    # Charger le package ZIP
    zip_path = Path("deployment-complete.zip")
    if not zip_path.exists():
        print(f"[ERREUR] Package non trouvé: {zip_path}")
        return
    
    print(f"Package trouvé: {zip_path} ({zip_path.stat().st_size / 1024 / 1024:.2f} MB)")
    
    # Mettre à jour le code
    try:
        with open(zip_path, 'rb') as f:
            zip_content = f.read()
        
        print("Mise à jour du code Lambda...")
        response = lambda_client.update_function_code(
            FunctionName=function_name,
            ZipFile=zip_content
        )
        
        print(f"[OK] Code mis à jour! Version: {response['Version']}")
        
        # Attendre que la mise à jour soit terminée
        print("Attente 10 secondes pour que la mise à jour se termine...")
        time.sleep(10)
        
        # Mettre à jour la configuration
        print("Mise à jour de la configuration...")
        response = lambda_client.update_function_configuration(
            FunctionName=function_name,
            Runtime="python3.10",
            Handler="lambda_function.lambda_handler",
            Timeout=300,
            MemorySize=1024,
            Environment={
                'Variables': {
                    'DYNAMODB_TABLE_NAME': 'invoices-extractor-final',
                    'S3_INPUT_BUCKET': 'invoice-extractor-final-bucket',
                    'BEDROCK_MODEL_ID': 'meta.llama3-1-70b-instruct-v1:0',
                    'ENVIRONMENT_NAME': 'prod',
                    'LOG_LEVEL': 'INFO'
                }
            }
        )
        print("[OK] Configuration mise à jour!")
        
        # Attendre encore un peu
        print("Attente 5 secondes pour que la configuration soit appliquée...")
        time.sleep(5)
        
    except Exception as e:
        print(f"[ERREUR] {e}")
        return
    
    print("\n[OK] Mise à jour terminée avec succès!")
    print(f"URL Console: https://{region}.console.aws.amazon.com/lambda/home?region={region}#/functions/{function_name}")

def test_lambda():
    """Teste la fonction Lambda"""
    
    region = "us-west-2"
    function_name = "invoice-extractor-prod"
    
    print(f"\n=== Test de la fonction Lambda ===")
    
    lambda_client = boto3.client('lambda', region_name=region)
    
    # Test 1: Événement simple (devrait échouer avec 'Records')
    test_event = {"test": "hello"}
    
    try:
        print("Test 1: Événement simple...")
        response = lambda_client.invoke(
            FunctionName=function_name,
            InvocationType='RequestResponse',
            Payload=bytes(json.dumps(test_event), 'utf-8')
        )
        
        result = json.loads(response['Payload'].read())
        print(f"Résultat: {json.dumps(result, indent=2)}")
        
        if result.get('statusCode') == 500 and "'Records'" in str(result.get('body', '')):
            print("[OK] Test 1 réussi! La fonction attend un événement S3")
        else:
            print("[ATTENTION] Résultat inattendu pour Test 1")
            
    except Exception as e:
        print(f"[ERREUR] Test 1 échoué: {e}")
    
    # Test 2: Événement S3 simulé
    s3_event = {
        "Records": [
            {
                "s3": {
                    "bucket": {
                        "name": "invoice-extractor-final-bucket"
                    },
                    "object": {
                        "key": "test/test.pdf"
                    }
                }
            }
        ]
    }
    
    try:
        print("\nTest 2: Événement S3 simulé...")
        response = lambda_client.invoke(
            FunctionName=function_name,
            InvocationType='RequestResponse',
            Payload=bytes(json.dumps(s3_event), 'utf-8')
        )
        
        result = json.loads(response['Payload'].read())
        print(f"Résultat: {json.dumps(result, indent=2)}")
        
        # Le test devrait échouer car le fichier n'existe pas dans S3
        # Mais au moins on vérifie que le code s'exécute
        if 'errorMessage' not in result:
            print("[OK] Test 2 réussi! Le code s'exécute sans erreur d'import")
        else:
            print(f"[ATTENTION] Erreur d'exécution: {result.get('errorMessage', 'Unknown')}")
            
    except Exception as e:
        print(f"[ERREUR] Test 2 échoué: {e}")

if __name__ == "__main__":
    update_lambda()
    test_lambda()
