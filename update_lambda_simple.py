#!/usr/bin/env python3
"""
Script simple pour mettre à jour le code de la fonction Lambda
"""

import boto3
import json
import os
import zipfile
import tempfile
import shutil
from pathlib import Path

def update_lambda_simple():
    """Met à jour la fonction Lambda avec le code corrigé"""
    
    # Configuration AWS
    region = "us-west-2"
    function_name = "invoice-extractor-prod"
    
    print(f"Mise à jour de la fonction Lambda: {function_name} dans {region}")
    
    # Créer le client Lambda
    lambda_client = boto3.client('lambda', region_name=region)
    
    # Vérifier que la fonction existe
    try:
        response = lambda_client.get_function(FunctionName=function_name)
        print(f"✓ Fonction trouvée: {function_name}")
    except Exception as e:
        print(f"✗ Erreur: Fonction {function_name} non trouvée: {e}")
        return
    
    # Créer un package ZIP simple avec le code corrigé
    temp_dir = tempfile.mkdtemp()
    package_dir = Path(temp_dir) / "lambda_package"
    package_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Création du package dans: {package_dir}")
    
    # Copier le code source corrigé depuis src_propre
    src_dir = Path("src_propre")
    for file in src_dir.glob("*.py"):
        shutil.copy2(file, package_dir / file.name)
        print(f"  Copié: {file.name}")
    
    # Créer un fichier __init__.py si nécessaire
    init_file = package_dir / "__init__.py"
    if not init_file.exists():
        init_file.write_text("")
    
    # Créer l'archive ZIP
    zip_path = Path("deployment-updated.zip")
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(package_dir):
            for file in files:
                file_path = Path(root) / file
                arcname = file_path.relative_to(package_dir)
                zipf.write(file_path, arcname)
    
    print(f"✓ Package créé: {zip_path} ({zip_path.stat().st_size / 1024 / 1024:.2f} MB)")
    
    # Mettre à jour le code de la fonction
    try:
        with open(zip_path, 'rb') as f:
            zip_content = f.read()
        
        print("Mise à jour du code Lambda...")
        response = lambda_client.update_function_code(
            FunctionName=function_name,
            ZipFile=zip_content
        )
        
        print(f"✓ Code Lambda mis à jour avec succès!")
        print(f"  Version: {response['Version']}")
        print(f"  CodeSha256: {response['CodeSha256'][:20]}...")
        
    except Exception as e:
        print(f"✗ Erreur lors de la mise à jour du code: {e}")
        # Nettoyer
        shutil.rmtree(temp_dir)
        if zip_path.exists():
            zip_path.unlink()
        return
    
    # Mettre à jour la configuration
    try:
        print("Mise à jour de la configuration Lambda...")
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
        print("✓ Configuration Lambda mise à jour avec succès!")
    except Exception as e:
        print(f"✗ Erreur lors de la mise à jour de la configuration: {e}")
    
    # Nettoyer
    shutil.rmtree(temp_dir)
    if zip_path.exists():
        zip_path.unlink()
    
    print("\n✓ Mise à jour terminée!")
    print(f"  URL Console Lambda: https://{region}.console.aws.amazon.com/lambda/home?region={region}#/functions/{function_name}")

def test_lambda():
    """Teste la fonction Lambda mise à jour"""
    
    region = "us-west-2"
    function_name = "invoice-extractor-prod"
    
    print(f"\n=== Test de la fonction Lambda ===")
    
    lambda_client = boto3.client('lambda', region_name=region)
    
    # Créer un événement de test simple
    test_event = {
        "test": "hello"
    }
    
    try:
        print("Invocation de la fonction Lambda...")
        response = lambda_client.invoke(
            FunctionName=function_name,
            InvocationType='RequestResponse',
            Payload=bytes(json.dumps(test_event), 'utf-8')
        )
        
        result = json.loads(response['Payload'].read())
        print(f"Résultat: {json.dumps(result, indent=2)}")
        
        if result.get('statusCode') == 500 and "'Records'" in str(result.get('body', '')):
            print("✓ Test réussi! La fonction attend un événement S3 (champ 'Records')")
        else:
            print("⚠ Résultat inattendu")
            
    except Exception as e:
        print(f"✗ Erreur lors du test: {e}")

if __name__ == "__main__":
    update_lambda_simple()
    test_lambda()
