#!/usr/bin/env python3
"""
Déploie le package final sur Lambda
"""

import boto3
import json
import time
from pathlib import Path

def deploy_to_lambda():
    """Déploie le package sur Lambda"""
    
    region = "us-west-2"
    function_name = "invoice-extractor-prod"
    
    print(f"Déploiement sur Lambda: {function_name} dans {region}")
    
    lambda_client = boto3.client('lambda', region_name=region)
    
    # Vérifier la fonction
    try:
        func = lambda_client.get_function(FunctionName=function_name)
        print(f"[OK] Fonction trouvée: {function_name}")
        print(f"  Runtime: {func['Configuration']['Runtime']}")
        print(f"  Handler: {func['Configuration']['Handler']}")
    except Exception as e:
        print(f"[ERREUR] Fonction non trouvée: {e}")
        return
    
    # Charger le package
    zip_path = Path("deployment-final.zip")
    if not zip_path.exists():
        print(f"[ERREUR] Package non trouvé: {zip_path}")
        return
    
    print(f"Package: {zip_path} ({zip_path.stat().st_size / 1024 / 1024:.2f} MB)")
    
    # Mettre à jour le code
    try:
        with open(zip_path, 'rb') as f:
            zip_content = f.read()
        
        print("Mise à jour du code...")
        response = lambda_client.update_function_code(
            FunctionName=function_name,
            ZipFile=zip_content
        )
        
        print(f"[OK] Code mis à jour")
        print(f"  Version: {response['Version']}")
        print(f"  CodeSha256: {response['CodeSha256'][:16]}...")
        
        # Attendre
        print("Attente 5 secondes...")
        time.sleep(5)
        
    except Exception as e:
        print(f"[ERREUR] Mise à jour du code: {e}")
        return
    
    # Mettre à jour la configuration
    try:
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
        print("[OK] Configuration mise à jour")
        
        # Attendre
        print("Attente 5 secondes pour application...")
        time.sleep(5)
        
    except Exception as e:
        print(f"[ERREUR] Configuration: {e}")
        # Continuer quand même
    
    print("\n[OK] Déploiement terminé!")
    print(f"URL: https://{region}.console.aws.amazon.com/lambda/home?region={region}#/functions/{function_name}")

def test_deployment():
    """Teste le déploiement"""
    
    region = "us-west-2"
    function_name = "invoice-extractor-prod"
    
    print(f"\n=== Test du déploiement ===")
    
    lambda_client = boto3.client('lambda', region_name=region)
    
    # Test 1: Événement invalide (manque Records)
    test1 = {"test": "hello"}
    
    try:
        print("Test 1: Événement invalide...")
        response = lambda_client.invoke(
            FunctionName=function_name,
            InvocationType='RequestResponse',
            Payload=bytes(json.dumps(test1), 'utf-8')
        )
        
        result = json.loads(response['Payload'].read())
        print(f"Résultat: {json.dumps(result, indent=2)}")
        
        if result.get('statusCode') == 400 and "'Records'" in str(result):
            print("[OK] Test 1: Fonction valide les événements S3")
        else:
            print("[ATTENTION] Résultat inattendu")
            
    except Exception as e:
        print(f"[ERREUR] Test 1: {e}")
    
    # Test 2: Événement S3 simulé
    test2 = {
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
            Payload=bytes(json.dumps(test2), 'utf-8')
        )
        
        result = json.loads(response['Payload'].read())
        print(f"Résultat: {json.dumps(result, indent=2)}")
        
        # Le fichier n'existe pas dans S3, donc erreur attendue
        # Mais pas d'erreur d'import
        if 'errorMessage' not in result:
            print("[OK] Test 2: Code exécuté sans erreur d'import")
        elif "NoSuchKey" in str(result) or "not found" in str(result).lower():
            print("[OK] Test 2: Erreur S3 attendue (fichier non trouvé)")
        else:
            print(f"[INFO] Résultat: {result.get('errorMessage', 'Unknown')[:100]}")
            
    except Exception as e:
        print(f"[ERREUR] Test 2: {e}")
    
    # Vérifier les logs
    print("\n=== Vérification des logs ===")
    try:
        logs_client = boto3.client('logs', region_name=region)
        log_group = f"/aws/lambda/{function_name}"
        
        # Récupérer les derniers logs
        response = logs_client.describe_log_streams(
            logGroupName=log_group,
            orderBy='LastEventTime',
            descending=True,
            limit=1
        )
        
        if response['logStreams']:
            log_stream = response['logStreams'][0]['logStreamName']
            print(f"Dernier log stream: {log_stream}")
            
            # Récupérer quelques événements
            events = logs_client.get_log_events(
                logGroupName=log_group,
                logStreamName=log_stream,
                limit=10
            )
            
            print("Derniers logs:")
            for event in events['events'][-5:]:
                print(f"  {event['message']}")
        else:
            print("Aucun log stream trouvé")
            
    except Exception as e:
        print(f"[INFO] Impossible de récupérer les logs: {e}")

if __name__ == "__main__":
    deploy_to_lambda()
    test_deployment()
