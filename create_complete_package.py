#!/usr/bin/env python3
"""
Crée un package Lambda complet avec dépendances
"""

import os
import zipfile
import tempfile
import shutil
import subprocess
from pathlib import Path

def install_dependencies(target_dir: Path):
    """Installe les dépendances dans le répertoire cible"""
    
    requirements = [
        "boto3>=1.34.0",
        "PyPDF2>=3.0.0", 
        "pdfplumber>=0.10.0",
        "python-dotenv>=1.0.0"
    ]
    
    print("Installation des dépendances...")
    
    # Créer un fichier requirements temporaire
    req_file = target_dir / "requirements.txt"
    req_file.write_text("\n".join(requirements))
    
    # Installer avec pip
    try:
        subprocess.run([
            sys.executable, "-m", "pip", "install",
            "--target", str(target_dir),
            "-r", str(req_file),
            "--no-deps"
        ], check=True, capture_output=True)
        print("[OK] Dépendances installées")
    except subprocess.CalledProcessError as e:
        print(f"[ATTENTION] Erreur pip: {e.stderr.decode()}")
        # Essayer manuellement
        print("Installation manuelle...")
        subprocess.run([
            sys.executable, "-m", "pip", "install",
            "--target", str(target_dir),
            "boto3", "PyPDF2", "pdfplumber", "python-dotenv"
        ])

def create_complete_package():
    """Crée un package Lambda complet"""
    
    temp_dir = tempfile.mkdtemp()
    package_dir = Path(temp_dir) / "lambda_package"
    package_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Création du package complet dans: {package_dir}")
    
    # 1. Copier et modifier les fichiers source
    src_dir = Path("src_propre")
    
    for file in src_dir.glob("*.py"):
        content = file.read_text(encoding='utf-8')
        
        # Remplacer les imports relatifs par des imports absolus
        content = content.replace("from .config import Config", "from config import Config")
        content = content.replace("from .pdf_extractor import PDFExtractor", "from pdf_extractor import PDFExtractor")
        content = content.replace("from .bedrock_client import BedrockClient", "from bedrock_client import BedrockClient")
        content = content.replace("from .dynamodb_client import DynamoDBClient", "from dynamodb_client import DynamoDBClient")
        
        # Écrire le fichier modifié
        (package_dir / file.name).write_text(content, encoding='utf-8')
        print(f"  Traité: {file.name}")
    
    # 2. Installer les dépendances
    install_dependencies(package_dir)
    
    # 3. Créer un fichier lambda_function.py simplifié pour Lambda
    lambda_code = """import json
import os
import logging
import boto3
from datetime import datetime
from pathlib import Path

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import des modules locaux
from pdf_extractor import PDFExtractor
from bedrock_client import BedrockClient
from dynamodb_client import DynamoDBClient
from config import Config

class InvoiceExtractor:
    def __init__(self, region: str = None):
        self.region = region or Config.AWS_REGION
        self.pdf_extractor = PDFExtractor()
        self.bedrock_client = BedrockClient(region=self.region)
        self.dynamodb_client = DynamoDBClient(region=self.region)
    
    def extract_from_pdf(self, pdf_path: str, filename: str):
        pdf_text = self.pdf_extractor.extract_text(pdf_path)
        if not pdf_text:
            raise ValueError(f"Aucun texte extrait du PDF: {pdf_path}")
        
        prompt = f\"\"\"Analyse ce document PDF.

Tu es un expert comptable. En te basant sur ces données : {pdf_text[:5000]}

Extrais les informations suivantes et formate-les en JSON strict (sans markdown, juste le code brut).

Champs à extraire :
  - fournisseur (Nom de la société émettrice)
  - montant_ht (Nombre uniquement)
  - numero_facture
  - date_facture (Format YYYY-MM-DD)
  - Le numero Chrono du document
  - La période de couverture
  - nom du fichier que tu trouves ici {filename}

Si une info est manquante, mets null.\"\"\"
        
        extracted_data = self.bedrock_client.extract_invoice_data(prompt)
        extracted_data["filename"] = filename
        extracted_data["extraction_date"] = datetime.utcnow().isoformat()
        extracted_data["pdf_path"] = pdf_path
        return extracted_data
    
    def process_s3_event(self, event):
        try:
            s3_event = event["Records"][0]["s3"]
            bucket = s3_event["bucket"]["name"]
            key = s3_event["object"]["key"]
            filename = Path(key).name
            
            logger.info(f"Traitement du fichier: {filename} depuis {bucket}/{key}")
            
            s3_client = boto3.client("s3", region_name=self.region)
            local_path = f"/tmp/{filename}"
            s3_client.download_file(bucket, key, local_path)
            
            extracted_data = self.extract_from_pdf(local_path, filename)
            item_id = self.dynamodb_client.save_invoice_data(extracted_data)
            
            if os.path.exists(local_path):
                os.remove(local_path)
            
            return {
                "statusCode": 200,
                "body": json.dumps({
                    "message": "Facture traitée avec succès",
                    "invoice_id": item_id,
                    "data": extracted_data
                })
            }
        except Exception as e:
            logger.error(f"Erreur lors du traitement: {str(e)}")
            return {
                "statusCode": 500,
                "body": json.dumps({
                    "error": str(e),
                    "message": "Erreur lors du traitement de la facture"
                })
            }

def lambda_handler(event, context):
    region = os.environ.get("AWS_REGION", "us-west-2")
    extractor = InvoiceExtractor(region=region)
    return extractor.process_s3_event(event)
"""
    
    (package_dir / "lambda_function.py").write_text(lambda_code, encoding='utf-8')
    print("  Créé: lambda_function.py (handler simplifié)")
    
    # 4. Créer l'archive ZIP
    zip_path = Path("deployment-complete.zip")
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(package_dir):
            for file in files:
                file_path = Path(root) / file
                arcname = file_path.relative_to(package_dir)
                zipf.write(file_path, arcname)
    
    file_size_mb = zip_path.stat().st_size / 1024 / 1024
    print(f"[OK] Package complet créé: {zip_path} ({file_size_mb:.2f} MB)")
    
    # Nettoyer
    shutil.rmtree(temp_dir)
    
    return zip_path

def update_lambda():
    """Met à jour la fonction Lambda"""
    
    import boto3
    import time
    
    region = "us-west-2"
    function_name = "invoice-extractor-prod"
    
    print(f"\nMise à jour de Lambda...")
    
    lambda_client = boto3.client('lambda', region_name=region)
    
    # Créer le package
    zip_path = create_complete_package()
    
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
        
        # Attendre
        print("Attente 5 secondes...")
        time.sleep(5)
        
        # Mettre à jour la configuration (sans AWS_REGION)
        print("Mise à jour de la configuration...")
        response = lambda_client.update_function_configuration(
            FunctionName=function_name,
            Runtime="python3.10",
            Handler="lambda_function.lambda_handler",  # Nouveau handler
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
        
    except Exception as e:
        print(f"[ERREUR] {e}")
    
    # Nettoyer
    if zip_path.exists():
        zip_path.unlink()
    
    print("\n[OK] Mise à jour terminée!")

if __name__ == "__main__":
    import sys
    create_complete_package()
