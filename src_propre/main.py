#!/usr/bin/env python3
"""
Outil d'extraction d'informations de factures PDF avec AWS Bedrock
Version simplifiée utilisant seulement PyPDF2
"""

import os
import json
import logging
import boto3
from typing import Dict, Any
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote_plus

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import des modules locaux
try:
    from pdf_extractor_simple import PDFExtractorSimple
    from bedrock_client import BedrockClient
    from dynamodb_client import DynamoDBClient
    from config import Config
except ImportError as e:
    logger.error(f"Erreur d'import: {e}")
    raise


class InvoiceExtractorSimple:
    """Classe principale pour l'extraction de factures (version simplifiée)"""
    
    def __init__(self, region: str = None):
        """
        Initialise l'extracteur de factures
        
        Args:
            region: Région AWS à utiliser (si None, utilise la configuration)
        """
        self.region = region or Config.AWS_REGION
        self.pdf_extractor = PDFExtractorSimple()
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
            
            # 4. Post-traitement: corriger le fournisseur si le LLM s'est trompé
            extracted_data = self._fix_supplier_if_needed(extracted_data, filename)
            
            # 5. Ajouter des métadonnées et s'assurer que nom_fichier est défini
            if not extracted_data.get("nom_fichier"):
                extracted_data["nom_fichier"] = filename
            extracted_data["extraction_date"] = datetime.now(timezone.utc).isoformat()
            extracted_data["pdf_path"] = pdf_path
            
            return extracted_data
            
        except Exception as e:
            logger.error(f"Erreur lors de l'extraction: {str(e)}")
            raise
    
    def _fix_supplier_if_needed(self, data: Dict[str, Any], filename: str) -> Dict[str, Any]:
        """
        Corrige le fournisseur si le LLM a confondu client et fournisseur
        
        Args:
            data: Données extraites
            filename: Nom du fichier (contient souvent le fournisseur)
            
        Returns:
            Données corrigées
        """
        # Liste des clients connus (jamais fournisseurs)
        known_clients = [
            "BOARDRIDERS",
            "NA PALI",
            "QUIKSILVER",
            "KAUAI",
            "VANUATU",
            "EMERALD COAST",
            "PUKALANI",
            "HANALEI",
            "TARAWA",
            "SUNSHINE DIFFUSION"
        ]
        
        # Liste des fournisseurs connus
        known_suppliers = [
            "TELEFONICA",
            "CEGEDIM",
            "BOUYGUES",
            "ORANGE",
            "SFR",
            "FREE",
            "OVH"
        ]
        
        fournisseur = data.get("fournisseur", "")
        if not fournisseur:
            return data
        
        fournisseur_upper = fournisseur.upper()
        
        # Vérifier si le fournisseur extrait est en fait un client connu
        is_known_client = any(client in fournisseur_upper for client in known_clients)
        
        if is_known_client:
            logger.warning(f"Le LLM a identifié '{fournisseur}' comme fournisseur, mais c'est un client connu")
            
            # Essayer d'extraire le vrai fournisseur depuis le nom du fichier
            filename_upper = filename.upper()
            for supplier in known_suppliers:
                if supplier in filename_upper:
                    logger.info(f"Fournisseur corrigé depuis le nom du fichier: {supplier}")
                    data["fournisseur"] = supplier
                    return data
            
            logger.warning("Impossible de déterminer le fournisseur depuis le nom du fichier")
            data["fournisseur"] = None
        
        return data
    
    def _create_prompt(self, pdf_text: str, filename: str) -> str:
        """
        Crée le prompt pour Bedrock (format n8n qui fonctionnait)
        
        Args:
            pdf_text: Texte extrait du PDF
            filename: Nom du fichier
            
        Returns:
            Prompt formaté
        """
        # Limiter la taille du texte pour éviter de dépasser les limites de tokens
        max_text_length = 10000
        if len(pdf_text) > max_text_length:
            logger.warning(f"Texte PDF trop long ({len(pdf_text)} caractères), troncation à {max_text_length}")
            pdf_text = pdf_text[:max_text_length] + "... [texte tronqué]"
        
        # Prompt exact du n8n qui fonctionnait, amélioré pour distinguer fournisseur/client
        prompt = f"""Tu es un expert comptable. En te basant sur ces données : {pdf_text}

Nom du fichier (peut contenir un indice sur le fournisseur) : {filename}

Extrais les informations suivantes et formate-les en JSON strict (sans markdown, juste le code brut).

IMPORTANT - Distinction fournisseur/client :
- Le FOURNISSEUR est la société qui a ÉMIS/ENVOYÉ la facture (l'émetteur, le vendeur, celui qui facture)
- Le CLIENT est la société qui REÇOIT la facture (le destinataire, l'acheteur, celui qui paie)
- Ne confonds JAMAIS le client avec le fournisseur

RÈGLE CRITIQUE :
- BOARDRIDERS (toutes variantes: BOARDRIDERS TRADING ESPAÑA, BOARDRIDERS TRADING, etc.) est TOUJOURS le CLIENT, JAMAIS le fournisseur
- Si tu vois BOARDRIDERS, c'est le destinataire de la facture, pas l'émetteur

Le fournisseur est souvent identifié :
  * Dans l'en-tête ou le logo de la facture (en haut)
  * Dans les coordonnées bancaires (RIB, IBAN)
  * Dans le nom du fichier PDF
  * Comme "émetteur" ou "vendeur"
  
Le client est souvent identifié :
  * Dans "Adresse de facturation" ou "Adresse d'envoi"
  * Comme "destinataire" ou "acheteur"
  
ASTUCE: Le nom du fichier contient souvent le nom du FOURNISSEUR

Champs à extraire :
- fournisseur (Nom de la société ÉMETTRICE de la facture, PAS le client/destinataire. Utilise le nom du fichier comme indice si nécessaire)
- montant_ht (Montant hors taxes, nombre uniquement)
- numero_facture (Numéro de la facture)
- date_facture (Date de la facture au format YYYY-MM-DD)
- chrono (Le numéro Chrono du document si présent)
- couverture (La période de couverture/facturation si présente)
- nom_fichier (nom du fichier : {filename})

Champs requis :
- fournisseur (String) - ATTENTION: société ÉMETTRICE, pas le client. Vérifie le nom du fichier ! Si tu vois BOARDRIDERS, ce n'est PAS le fournisseur !
- montant_ht (Number)
- numero_facture (String)
- date_facture (YYYY-MM-DD)
- chrono (Number/String)
- couverture (String - période)
- nom_fichier (String)

Si une info est manquante, mets null.

Réponds UNIQUEMENT avec le JSON, sans texte avant ou après."""
        
        return prompt
    
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
            key = unquote_plus(s3_event["object"]["key"])
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
                }, ensure_ascii=False)
            }
            
        except Exception as e:
            logger.error(f"Erreur lors du traitement: {str(e)}")
            return {
                "statusCode": 500,
                "body": json.dumps({
                    "error": str(e),
                    "message": "Erreur lors du traitement de la facture"
                }, ensure_ascii=False)
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
    region = os.getenv("AWS_REGION")
    
    # Initialiser et exécuter l'extracteur
    extractor = InvoiceExtractorSimple(region=region)
    return extractor.process_s3_event(event)


if __name__ == "__main__":
    # Mode local pour les tests
    import sys
    
    if len(sys.argv) != 2:
        print("Usage: python main_simple.py <chemin_vers_pdf>")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    filename = Path(pdf_path).name
    
    extractor = InvoiceExtractorSimple()
    
    try:
        result = extractor.extract_from_pdf(pdf_path, filename)
        print("Informations extraites:")
        print(json.dumps(result, indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"Erreur: {str(e)}")
        sys.exit(1)
