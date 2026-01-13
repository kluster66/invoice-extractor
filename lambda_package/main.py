#!/usr/bin/env python3
"""
Handler Lambda pour l'extraction d'informations de factures PDF avec AWS Bedrock
Version spéciale pour Lambda avec imports absolus
"""

import os
import json
import logging
import boto3
from typing import Dict, Any
from datetime import datetime
from pathlib import Path

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import des modules locaux (absolus)
from pdf_extractor import PDFExtractor
from bedrock_client import BedrockClient
from dynamodb_client import DynamoDBClient
import config


class InvoiceExtractor:
    """Classe principale pour l'extraction de factures"""
    
    def __init__(self, region: str = None):
        """
        Initialise l'extracteur de factures
        
        Args:
            region: Région AWS à utiliser (si None, utilise la configuration)
        """
        self.region = region or config.Config.AWS_REGION
        self.pdf_extractor = PDFExtractor()
        self.bedrock_client = BedrockClient(region=self.region)
        self.dynamodb_client = DynamoDBClient(region=self.region)
        
    def extract_from_pdf(self, pdf_path: str, filename: str) -> Dict[str, Any]:
        """
        Extrait les informations d'une facture PDF
        
        Args:
            pdf_path: Chemin vers le fichier PDF
            filename: Nom du fichier
            
        Returns:
            Dictionnaire contenant les informations extraites
        """
        try:
            # 1. Extraire le texte du PDF
            logger.info(f"Extraction du texte du PDF: {pdf_path}")
            pdf_text = self.pdf_extractor.extract_text(pdf_path)
            
            if not pdf_text:
                raise ValueError(f"Aucun texte extrait du PDF: {pdf_path}")
            
            # 2. Préparer le prompt pour Bedrock
            prompt = self._create_prompt(pdf_text, filename)
            
            # 3. Appeler Bedrock pour l'extraction
            logger.info("Appel à AWS Bedrock pour l'extraction des informations")
            extracted_data = self.bedrock_client.extract_invoice_data(prompt)
            
            # 4. Ajouter des métadonnées
            extracted_data["filename"] = filename
            extracted_data["extraction_date"] = datetime.utcnow().isoformat()
            extracted_data["pdf_path"] = pdf_path
            
            return extracted_data
            
        except Exception as e:
            logger.error(f"Erreur lors de l'extraction: {str(e)}")
            raise
    
    def _create_prompt(self, pdf_text: str, filename: str) -> str:
        """
        Crée le prompt pour Bedrock
        
        Args:
            pdf_text: Texte extrait du PDF
            filename: Nom du fichier
            
        Returns:
            Prompt formaté
        """
        prompt_template = """Analyse ce document PDF.

Tu es un expert comptable. en te basant sur ces données : {pdf_text}

Extrais les informations suivantes et formate-les en JSON strict (sans markdown, juste le code brut).

Champs à extraire :
  - fournisseur (Nom de la société émettrice)
  - montant_ht (Nombre uniquement)
  - numero_facture
  - date_facture (Format YYYY-MM-DD)
  - Le numero Chrono du document
  - La période de couverture
  - nom du fichier que tu trouves ici {filename}
  

Si une info est manquante, mets null."""
        
        return prompt_template.format(pdf_text=pdf_text, filename=filename)
    
    def process_s3_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Traite un événement S3 (déclencheur Lambda)
        
        Args:
            event: Événement S3
            
        Returns:
            Résultat du traitement
        """
        try:
            # Extraire les informations de l'événement S3
            s3_event = event["Records"][0]["s3"]
            bucket = s3_event["bucket"]["name"]
            key = s3_event["object"]["key"]
            filename = Path(key).name
            
            logger.info(f"Traitement du fichier: {filename} depuis {bucket}/{key}")
            
            # 1. Télécharger le fichier depuis S3
            s3_client = boto3.client("s3", region_name=self.region)
            local_path = f"/tmp/{filename}"
            
            s3_client.download_file(bucket, key, local_path)
            logger.info(f"Fichier téléchargé: {local_path}")
            
            # 2. Extraire les informations
            extracted_data = self.extract_from_pdf(local_path, filename)
            
            # 3. Stocker dans DynamoDB
            item_id = self.dynamodb_client.save_invoice_data(extracted_data)
            
            # 4. Nettoyer le fichier temporaire
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


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Handler principal pour AWS Lambda
    
    Args:
        event: Événement déclencheur
        context: Contexte Lambda
        
    Returns:
        Réponse Lambda
    """
    # Récupérer la région depuis les variables d'environnement
    # En Lambda, AWS_REGION est automatiquement définie
    region = os.getenv("AWS_REGION")
    
    # Initialiser et exécuter l'extracteur
    extractor = InvoiceExtractor(region=region)
    return extractor.process_s3_event(event)
