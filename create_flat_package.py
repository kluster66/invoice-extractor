#!/usr/bin/env python3
"""
Crée un package Lambda plat (sans imports relatifs)
"""

import os
import zipfile
import tempfile
import shutil
from pathlib import Path

def create_flat_package():
    """Crée un package Lambda avec une structure plate"""
    
    temp_dir = tempfile.mkdtemp()
    package_dir = Path(temp_dir) / "lambda_package"
    package_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Création du package plat dans: {package_dir}")
    
    # Lire et modifier les fichiers source pour enlever les imports relatifs
    src_dir = Path("src_propre")
    
    for file in src_dir.glob("*.py"):
        content = file.read_text(encoding='utf-8')
        
        # Remplacer les imports relatifs
        content = content.replace("from .config import Config", "from config import Config")
        content = content.replace("from .pdf_extractor import PDFExtractor", "from pdf_extractor import PDFExtractor")
        content = content.replace("from .bedrock_client import BedrockClient", "from bedrock_client import BedrockClient")
        content = content.replace("from .dynamodb_client import DynamoDBClient", "from dynamodb_client import DynamoDBClient")
        
        # Écrire le fichier modifié
        (package_dir / file.name).write_text(content, encoding='utf-8')
        print(f"  Traité: {file.name}")
    
    # Créer l'archive ZIP
    zip_path = Path("deployment-flat.zip")
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(package_dir):
            for file in files:
                file_path = Path(root) / file
                arcname = file_path.relative_to(package_dir)
                zipf.write(file_path, arcname)
    
    file_size_mb = zip_path.stat().st_size / 1024 / 1024
    print(f"[OK] Package plat créé: {zip_path} ({file_size_mb:.2f} MB)")
    
    # Nettoyer
    shutil.rmtree(temp_dir)
    
    return zip_path

def update_lambda_with_flat_package():
    """Met à jour Lambda avec le package plat"""
    
    import boto3
    import json
    
    region = "us-west-2"
    function_name = "invoice-extractor-prod"
    
    print(f"\nMise à jour de Lambda avec package plat...")
    
    lambda_client = boto3.client('lambda', region_name=region)
    
    # Créer le package plat
    zip_path = create_flat_package()
    
    # Mettre à jour le code
    try:
        with open(zip_path, 'rb') as f:
            zip_content = f.read()
        
        print("Mise à jour du code Lambda...")
        response = lambda_client.update_function_code(
            FunctionName=function_name,
            ZipFile=zip_content
        )
        
        print(f"[OK] Code Lambda mis à jour!")
        print(f"  Version: {response['Version']}")
        
        # Attendre que la mise à jour soit terminée
        import time
        print("Attente de la fin de la mise à jour...")
        time.sleep(10)
        
        # Maintenant mettre à jour la configuration
        print("Mise à jour de la configuration...")
        response = lambda_client.update_function_configuration(
            FunctionName=function_name,
            Runtime="python3.10",
            Handler="main.lambda_handler",
            Timeout=300,
            MemorySize=1024,
            Environment={
                'Variables': {
                    'DYNAMODB_TABLE_NAME': 'invoices-extractor-final',
                    'S3_INPUT_BUCKET': 'invoice-extractor-final-bucket',
                    'BEDROCK_MODEL_ID': 'meta.llama3-1-70b-instruct-v1:0',
                    'ENVIRONMENT_NAME': 'prod',
                    'LOG_LEVEL': 'INFO',
                    'AWS_REGION': region
                }
            }
        )
        print("[OK] Configuration mise à jour!")
        
    except Exception as e:
        print(f"[ERREUR] {e}")
    
    # Nettoyer
    if zip_path.exists():
        zip_path.unlink()
    
    print("\n[OK] Mise à jour terminée!")

def test_lambda_after_update():
    """Teste Lambda après mise à jour"""
    
    import boto3
    import json
    import base64
    
    region = "us-west-2"
    function_name = "invoice-extractor-prod"
    
    print(f"\n=== Test après mise à jour ===")
    
    lambda_client = boto3.client('lambda', region_name=region)
    
    # Test avec un événement simple
    test_event = {"test": "hello"}
    
    try:
        print("Test avec événement simple...")
        payload = json.dumps(test_event).encode('utf-8')
        
        response = lambda_client.invoke(
            FunctionName=function_name,
            InvocationType='RequestResponse',
            Payload=payload
        )
        
        result = json.loads(response['Payload'].read())
        print(f"Résultat: {json.dumps(result, indent=2)}")
        
    except Exception as e:
        print(f"[ERREUR] Test échoué: {e}")

if __name__ == "__main__":
    update_lambda_with_flat_package()
    test_lambda_after_update()
