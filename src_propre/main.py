#!/usr/bin/env python3
"""
Outil d'extraction d'informations de factures PDF avec AWS Bedrock.
Cette version utilise l'extracteur simplifié (PyPDF2 uniquement) pour une meilleure compatibilité Lambda.
"""

import os
import re
import json
import logging
import boto3
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote_plus

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Entités clientes connues — jamais fournisseurs (celui qui reçoit et paie la facture).
# Compléter si de nouvelles entités du groupe sont ajoutées.
KNOWN_CLIENTS = [
    "BOARDRIDERS",
    "NA PALI",
    "QUIKSILVER",
    "KAUAI",
    "VANUATU",
    "EMERALD COAST",
    "PUKALANI",
    "HANALEI",
    "TARAWA",
    "SUNSHINE DIFFUSION",
]

# Mots génériques présents dans les noms de fichiers de factures, à ignorer
# lors de l'extraction du fournisseur depuis le nom du fichier.
_FILENAME_NOISE_WORDS = {
    "FACTURE", "INVOICE", "FACT", "INV", "PDF",
    "HT", "TTC", "TVA", "VAT",
    "MG", "PLVT", "FR", "ES", "DE", "EN",
}

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
        Corrige le fournisseur si le LLM a confondu client et fournisseur.

        Quand le LLM met un client connu dans le champ fournisseur, on tente
        d'extraire le vrai fournisseur depuis le nom du fichier par élimination
        (sans liste fermée de fournisseurs).
        """
        fournisseur = data.get("fournisseur", "")
        if not fournisseur:
            return data

        fournisseur_upper = fournisseur.upper()
        is_known_client = any(client in fournisseur_upper for client in KNOWN_CLIENTS)

        if is_known_client:
            logger.warning(
                f"Le LLM a identifié '{fournisseur}' comme fournisseur, "
                "mais c'est un client connu — tentative de correction depuis le nom du fichier"
            )
            supplier = self._extract_supplier_from_filename(filename)
            if supplier:
                logger.info(f"Fournisseur extrait depuis le nom du fichier: {supplier}")
                data["fournisseur"] = supplier
            else:
                logger.warning("Impossible de déterminer le fournisseur depuis le nom du fichier")
                data["fournisseur"] = None

        return data

    def _extract_supplier_from_filename(self, filename: str) -> Optional[str]:
        """
        Extrait le nom du fournisseur depuis le nom du fichier par élimination.

        Logique : on retire les séquences numériques (dates, chronos…),
        les noms de clients connus et les mots génériques de facturation.
        Le premier token significatif restant est retenu comme fournisseur.
        Fonctionne pour n'importe quel fournisseur, sans liste pré-définie.
        """
        name = Path(filename).stem.upper()

        # Supprimer les séquences purement numériques (dates, numéros de chrono…)
        name = re.sub(r'\b\d+\b', ' ', name)

        # Supprimer les clients connus
        for client in KNOWN_CLIENTS:
            name = name.replace(client, ' ')

        # Découper et filtrer les tokens non significatifs
        tokens = [
            t for t in re.split(r'[\s_\-\.]+', name)
            if t and t not in _FILENAME_NOISE_WORDS and len(t) > 2
        ]

        if not tokens:
            return None

        # Capitaliser proprement (ex: "TELEFONICA" → "Telefonica")
        return tokens[0].capitalize()
    
    def _create_prompt(self, pdf_text: str, filename: str) -> str:
        """
        Crée le prompt d'extraction pour Bedrock.

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
        
        # Construire la liste des clients connus pour l'injecter dans le prompt
        known_clients_str = ", ".join(KNOWN_CLIENTS)

        prompt = f"""Tu es un expert comptable spécialisé dans l'analyse de factures B2B.

Texte extrait du PDF :
{pdf_text}

Nom du fichier : {filename}

---
MÉTHODE EN 2 ÉTAPES — suis-la dans l'ordre :

ÉTAPE 1 — Identifie le CLIENT (celui qui REÇOIT et PAIE la facture) :
  • Il apparaît dans "Adressé à", "Facturé à", "Bill to", "À l'attention de"
  • Les entités suivantes sont TOUJOURS le client, JAMAIS le fournisseur : {known_clients_str}
  • Si tu vois l'une de ces entités, c'est le client — point final.

ÉTAPE 2 — Identifie le FOURNISSEUR (celui qui ÉMET et ENVOIE la facture) :
  • C'est l'autre partie : l'émetteur, le prestataire, le vendeur
  • Son nom figure souvent en haut de la facture, dans l'en-tête ou le logo
  • Ses coordonnées bancaires (IBAN/RIB) sont dans la facture
  • Le nom du fichier contient souvent son nom
  • Il n'est JAMAIS l'une des entités listées à l'étape 1

---
Extrais les champs suivants et réponds UNIQUEMENT avec le JSON brut (sans markdown) :

{{
  "fournisseur": "Nom de la société émettrice (étape 2) — jamais le client",
  "montant_ht": 0.00,
  "devise": "Code ISO 4217 (EUR, USD, GBP…)",
  "numero_facture": "Numéro de facture",
  "date_facture": "YYYY-MM-DD",
  "chrono": "Numéro chrono si présent, sinon null",
  "couverture": "Période de couverture si présente, sinon null",
  "nom_fichier": "{filename}"
}}

Si une information est absente du document, mets null."""
        
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

            try:
                # 2. Extraire les informations
                extracted_data = self.extract_from_pdf(local_path, filename)

                # 3. Stocker dans DynamoDB
                item_id = self.dynamodb_client.save_invoice_data(extracted_data)
            finally:
                # 4. Nettoyer le fichier temporaire (toujours, même en cas d'erreur)
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
        print("Usage: python main.py <chemin_vers_pdf>")
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
