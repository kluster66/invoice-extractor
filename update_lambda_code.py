#!/usr/bin/env python3
"""
Script pour mettre à jour le code de la fonction Lambda existante
"""

import boto3
import os
import zipfile
import tempfile
import shutil
from pathlib import Path

def create_lambda_package():
    """Crée un package ZIP pour Lambda avec le code corrigé"""
    
    # Créer un répertoire temporaire
    temp_dir = tempfile.mkdtemp()
    package_dir = Path(temp_dir) / "lambda_package"
    package_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Création du package dans: {package_dir}")
    
    # Copier le code source corrigé
    src_dir = Path("src_propre")
    for file in src_dir.glob("*.py"):
        shutil.copy2(file, package_dir / file.name)
        print(f"Copié: {file.name}")
    
    # Créer un fichier requirements.txt minimal
    requirements = [
        "boto3>=1.34.0",
        "PyPDF2>=3.0.0",
        "pdfplumber>=0.10.0",
        "python-dotenv>=1.0.0"
    ]
    
    with open(package_dir / "requirements.txt", "w") as f:
        f.write("\n".join(requirements))
    
    # Installer les dépendances dans le package
    import subprocess
    subprocess.run([
        "pip", "install", 
        "--target", str(package_dir),
        "-r", str(package_dir / "requirements.txt")
    ], check=True)
    
    # Créer l'archive ZIP
    zip_path = Path("deployment-corrected.zip")
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(package_dir):
            for file in files:
                file_path = Path(root) / file
                arcname = file_path.relative_to(package_dir)
                zipf.write(file_path, arcname)
    
    print(f"Package créé: {zip_path} ({zip_path.stat().st_size / 1024 / 1024:.2f} MB)")
    
    # Nettoyer
    shutil.rmtree(temp_dir)
    
    return zip_path

def update_lambda_function():
    """Met à jour la fonction Lambda existante"""
    
    # Configuration AWS
    region = "us-west-2"
    function_name = "invoice-extractor-prod"
    
    # Créer le client Lambda
    lambda_client = boto3.client('lambda', region_name=region)
    
    # Vérifier que la fonction existe
    try:
        response = lambda_client.get_function(FunctionName=function_name)
        print(f"Fonction trouvée: {function_name}")
    except Exception as e:
        print(f"Erreur: Fonction {function_name} non trouvée: {e}")
        return
    
    # Créer le package
    zip_path = create_lambda_package()
    
    # Mettre à jour le code de la fonction
    try:
        with open(zip_path, 'rb') as f:
            zip_content = f.read()
        
        response = lambda_client.update_function_code(
            FunctionName=function_name,
            ZipFile=zip_content
        )
        
        print(f"Code Lambda mis à jour avec succès!")
        print(f"Version: {response['Version']}")
        print(f"CodeSha256: {response['CodeSha256'][:20]}...")
        
    except Exception as e:
        print(f"Erreur lors de la mise à jour: {e}")
    
    # Mettre à jour la configuration si nécessaire
    try:
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
                    'LOG_LEVEL': 'INFO'
                }
            }
        )
        print("Configuration Lambda mise à jour avec succès!")
    except Exception as e:
        print(f"Erreur lors de la mise à jour de la configuration: {e}")

def test_lambda_function():
    """Teste la fonction Lambda mise à jour"""
    
    region = "us-west-2"
    function_name = "invoice-extractor-prod"
    
    lambda_client = boto3.client('lambda', region_name=region)
    
    # Créer un événement de test S3
    test_event = {
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
        response = lambda_client.invoke(
            FunctionName=function_name,
            InvocationType='RequestResponse',
            Payload=bytes(json.dumps(test_event), 'utf-8')
        )
        
        result = json.loads(response['Payload'].read())
        print(f"Résultat du test: {json.dumps(result, indent=2)}")
        
    except Exception as e:
        print(f"Erreur lors du test: {e}")

if __name__ == "__main__":
    import json
    
    print("=== Mise à jour de la fonction Lambda ===")
    update_lambda_function()
    
    print("\n=== Test de la fonction Lambda ===")
    test_lambda_function()
