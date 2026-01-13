#!/usr/bin/env python3
"""
Crée le package final pour Lambda avec seulement PyPDF2
"""

import os
import zipfile
import tempfile
import shutil
import subprocess
import sys
from pathlib import Path

def install_dependencies(target_dir: Path):
    """Installe les dépendances minimales"""
    
    print("Installation des dépendances minimales...")
    
    # Dépendances minimales
    dependencies = [
        "boto3>=1.34.0",
        "PyPDF2>=3.0.0",
        "python-dotenv>=1.0.0"
    ]
    
    # Créer requirements.txt
    req_file = target_dir / "requirements.txt"
    req_file.write_text("\n".join(dependencies))
    
    # Installer
    try:
        result = subprocess.run([
            sys.executable, "-m", "pip", "install",
            "--target", str(target_dir),
            "-r", str(req_file),
            "--no-deps"
        ], check=True, capture_output=True, text=True)
        print("[OK] Dépendances installées")
    except subprocess.CalledProcessError as e:
        print(f"[ERREUR] Installation échouée: {e.stderr}")
        # Essayer sans --no-deps
        try:
            subprocess.run([
                sys.executable, "-m", "pip", "install",
                "--target", str(target_dir),
                "boto3", "PyPDF2", "python-dotenv"
            ], check=True)
            print("[OK] Dépendances installées (sans --no-deps)")
        except:
            print("[ATTENTION] Installation manuelle nécessaire")

def create_final_package():
    """Crée le package final"""
    
    temp_dir = tempfile.mkdtemp()
    package_dir = Path(temp_dir) / "lambda_package"
    package_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Création du package final dans: {package_dir}")
    
    # 1. Copier et modifier les fichiers source
    src_dir = Path("src_propre")
    
    # Fichiers à copier (sans pdf_extractor.py original)
    files_to_copy = [
        "bedrock_client.py",
        "config.py", 
        "dynamodb_client.py",
        "main.py",
        "__init__.py"
    ]
    
    for filename in files_to_copy:
        file = src_dir / filename
        if file.exists():
            content = file.read_text(encoding='utf-8')
            
            # Remplacer les imports
            content = content.replace("from .config import Config", "from config import Config")
            content = content.replace("from .pdf_extractor import PDFExtractor", "from pdf_extractor import PDFExtractor")
            content = content.replace("from .bedrock_client import BedrockClient", "from bedrock_client import BedrockClient")
            content = content.replace("from .dynamodb_client import DynamoDBClient", "from dynamodb_client import DynamoDBClient")
            
            (package_dir / filename).write_text(content, encoding='utf-8')
            print(f"  Copié: {filename}")
    
    # 2. Copier la version simplifiée de pdf_extractor
    simple_pdf = Path("src_propre/pdf_extractor_simple.py")
    if simple_pdf.exists():
        content = simple_pdf.read_text(encoding='utf-8')
        # Remplacer le nom de la classe si nécessaire
        (package_dir / "pdf_extractor.py").write_text(content, encoding='utf-8')
        print(f"  Copié: pdf_extractor.py (version simplifiée)")
    
    # 3. Installer les dépendances
    install_dependencies(package_dir)
    
    # 4. Créer un fichier lambda_function.py optimisé
    lambda_code = """import json
import os
import logging
import boto3
from datetime import datetime
from pathlib import Path

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import des modules
try:
    from pdf_extractor import PDFExtractor
    from bedrock_client import BedrockClient
    from dynamodb_client import DynamoDBClient
    from config import Config
except ImportError as e:
    logger.error(f"Erreur d'import: {e}")
    raise

class InvoiceProcessor:
    def __init__(self, region: str = None):
        self.region = region or os.environ.get('AWS_REGION', 'us-west-2')
        self.pdf_extractor = PDFExtractor()
        self.bedrock_client = BedrockClient(region=self.region)
        self.dynamodb_client = DynamoDBClient(region=self.region)
    
    def process_pdf(self, pdf_path: str, filename: str):
        # Extraire le texte
        pdf_text = self.pdf_extractor.extract_text(pdf_path)
        if not pdf_text:
            raise ValueError(f"Aucun texte extrait: {pdf_path}")
        
        # Créer le prompt
        prompt = f\"\"\"Analyse ce document PDF.

Tu es un expert comptable. En te basant sur ces données : {pdf_text[:4000]}

Extrais les informations suivantes en JSON strict:

{{
  "fournisseur": "Nom de la société",
  "montant_ht": 0.0,
  "numero_facture": "Numéro",
  "date_facture": "YYYY-MM-DD",
  "Le numero Chrono du document": "Numéro chrono",
  "La période de couverture": "Période",
  "nom du fichier que tu trouves ici": "{filename}"
}}

Si une info est manquante, mets null.\"\"\"
        
        # Appeler Bedrock
        extracted_data = self.bedrock_client.extract_invoice_data(prompt)
        
        # Ajouter métadonnées
        extracted_data["filename"] = filename
        extracted_data["extraction_date"] = datetime.utcnow().isoformat()
        extracted_data["pdf_path"] = pdf_path
        
        return extracted_data
    
    def process_s3_event(self, event):
        try:
            # Extraire info S3
            s3_event = event["Records"][0]["s3"]
            bucket = s3_event["bucket"]["name"]
            key = s3_event["object"]["key"]
            filename = Path(key).name
            
            logger.info(f"Traitement: {filename} depuis {bucket}/{key}")
            
            # Télécharger depuis S3
            s3_client = boto3.client("s3", region_name=self.region)
            local_path = f"/tmp/{filename}"
            s3_client.download_file(bucket, key, local_path)
            
            # Traiter le PDF
            extracted_data = self.process_pdf(local_path, filename)
            
            # Sauvegarder dans DynamoDB
            item_id = self.dynamodb_client.save_invoice_data(extracted_data)
            
            # Nettoyer
            if os.path.exists(local_path):
                os.remove(local_path)
            
            return {
                "statusCode": 200,
                "body": json.dumps({
                    "message": "Facture traitée",
                    "invoice_id": item_id,
                    "data": extracted_data
                })
            }
            
        except Exception as e:
            logger.error(f"Erreur: {str(e)}")
            return {
                "statusCode": 500,
                "body": json.dumps({
                    "error": str(e),
                    "message": "Erreur de traitement"
                })
            }

def lambda_handler(event, context):
    logger.info(f"Événement reçu: {json.dumps(event)[:500]}...")
    
    # Vérifier que c'est un événement S3
    if "Records" not in event:
        return {
            "statusCode": 400,
            "body": json.dumps({
                "error": "Événement S3 attendu",
                "message": "Le champ 'Records' est manquant"
            })
        }
    
    # Traiter
    processor = InvoiceProcessor()
    return processor.process_s3_event(event)
"""
    
    (package_dir / "lambda_function.py").write_text(lambda_code, encoding='utf-8')
    print("  Créé: lambda_function.py")
    
    # 5. Créer l'archive ZIP
    zip_path = Path("deployment-final.zip")
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(package_dir):
            for file in files:
                file_path = Path(root) / file
                arcname = file_path.relative_to(package_dir)
                zipf.write(file_path, arcname)
    
    file_size_mb = zip_path.stat().st_size / 1024 / 1024
    print(f"[OK] Package final créé: {zip_path} ({file_size_mb:.2f} MB)")
    
    # Nettoyer
    shutil.rmtree(temp_dir)
    
    return zip_path

if __name__ == "__main__":
    create_final_package()
