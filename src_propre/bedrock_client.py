"""
Client pour AWS Bedrock avec support multi-modèles et parsing amélioré
"""

import json
import logging
import re
import boto3
from typing import Dict, Any, Optional
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class BedrockClient:
    """Client pour interagir avec AWS Bedrock avec support multi-modèles"""
    
    def __init__(self, region: str = None, model_id: str = None):
        """
        Initialise le client Bedrock
        
        Args:
            region: Région AWS (si None, utilise la configuration)
            model_id: ID du modèle Bedrock (si None, utilise la configuration)
        """
        from config import Config
        
        self.region = region or Config.AWS_REGION
        self.model_id = model_id or Config.BEDROCK_MODEL_ID
        self.max_tokens = Config.BEDROCK_MAX_TOKENS
        self.temperature = Config.BEDROCK_TEMPERATURE
        
        self.client = boto3.client("bedrock-runtime", region_name=self.region)
        
        # Déterminer le type de modèle pour le format de requête
        self.model_type = self._detect_model_type()
        
        logger.info(f"Client Bedrock initialisé (modèle: {self.model_id}, région: {self.region}, type: {self.model_type})")
    
    def _detect_model_type(self) -> str:
        """
        Détermine le type de modèle pour adapter le format de requête
        
        Returns:
            Type de modèle: 'anthropic', 'meta', 'amazon', 'ai21', 'cohere', 'unknown'
        """
        model_id_lower = self.model_id.lower()
        
        if "anthropic" in model_id_lower:
            return "anthropic"
        elif "meta" in model_id_lower:
            return "meta"
        elif "amazon" in model_id_lower:
            return "amazon"
        elif "ai21" in model_id_lower:
            return "ai21"
        elif "cohere" in model_id_lower:
            return "cohere"
        else:
            return "unknown"
    
    def _create_request_body(self, prompt: str) -> Dict[str, Any]:
        """
        Crée le corps de la requête selon le type de modèle
        
        Args:
            prompt: Prompt à envoyer au modèle
            
        Returns:
            Corps de la requête formaté
        """
        if self.model_type == "anthropic":
            # Format Anthropic Claude (Completions API)
            return {
                "prompt": f"\n\nHuman: {prompt}\n\nAssistant:",
                "max_tokens_to_sample": self.max_tokens,
                "temperature": self.temperature,
                "stop_sequences": ["\n\nHuman:"]
            }
        
        elif self.model_type == "meta":
            # Format Meta Llama
            return {
                "prompt": prompt,
                "max_gen_len": self.max_tokens,
                "temperature": self.temperature,
                "top_p": 0.9
            }
        
        elif self.model_type == "amazon":
            # Format Amazon Titan
            return {
                "inputText": prompt,
                "textGenerationConfig": {
                    "maxTokenCount": self.max_tokens,
                    "temperature": self.temperature,
                    "topP": 0.9,
                    "stopSequences": []
                }
            }
        
        elif self.model_type == "ai21":
            # Format AI21 Jurassic
            return {
                "prompt": prompt,
                "maxTokens": self.max_tokens,
                "temperature": self.temperature,
                "topP": 0.9,
                "stopSequences": [],
                "countPenalty": {
                    "scale": 0
                },
                "presencePenalty": {
                    "scale": 0
                },
                "frequencyPenalty": {
                    "scale": 0
                }
            }
        
        elif self.model_type == "cohere":
            # Format Cohere Command
            return {
                "prompt": prompt,
                "max_tokens": self.max_tokens,
                "temperature": self.temperature,
                "p": 0.9,
                "k": 0,
                "stop_sequences": [],
                "return_likelihoods": "NONE"
            }
        
        else:
            # Format générique (essayer le format Anthropic)
            logger.warning(f"Type de modèle inconnu: {self.model_id}, utilisation du format Anthropic par défaut")
            return {
                "prompt": f"\n\nHuman: {prompt}\n\nAssistant:",
                "max_tokens_to_sample": self.max_tokens,
                "temperature": self.temperature
            }
    
    def _parse_response(self, response_body: Dict[str, Any]) -> str:
        """
        Parse la réponse selon le type de modèle
        
        Args:
            response_body: Corps de la réponse du modèle
            
        Returns:
            Texte extrait de la réponse
        """
        if self.model_type == "anthropic":
            return response_body.get("completion", "").strip()
        
        elif self.model_type == "meta":
            return response_body.get("generation", "").strip()
        
        elif self.model_type == "amazon":
            results = response_body.get("results", [])
            if results:
                return results[0].get("outputText", "").strip()
            return ""
        
        elif self.model_type == "ai21":
            return response_body.get("completions", [{}])[0].get("data", {}).get("text", "").strip()
        
        elif self.model_type == "cohere":
            generations = response_body.get("generations", [])
            if generations:
                return generations[0].get("text", "").strip()
            return ""
        
        else:
            # Essayer de trouver le texte dans la réponse
            if "completion" in response_body:
                return response_body["completion"].strip()
            elif "generation" in response_body:
                return response_body["generation"].strip()
            elif "outputText" in response_body:
                return response_body["outputText"].strip()
            else:
                # Retourner la réponse entière comme string
                return str(response_body)
    
    def _extract_json_from_response(self, response_text: str) -> Optional[Dict[str, Any]]:
        """
        Extrait le JSON de la réponse texte, même s'il y a du texte supplémentaire
        
        Args:
            response_text: Réponse texte du modèle
            
        Returns:
            Données JSON extraites ou None
        """
        # Nettoyer la réponse
        cleaned = response_text.strip()
        
        # Chercher des blocs JSON dans des backticks
        json_pattern = r'```(?:json)?\s*(\{.*?\})\s*```'
        matches = re.findall(json_pattern, cleaned, re.DOTALL)
        
        for match in matches:
            try:
                data = json.loads(match)
                if isinstance(data, dict):
                    logger.info(f"JSON extrait d'un bloc backtick: {len(match)} caractères")
                    return data
            except json.JSONDecodeError:
                continue
        
        # Chercher du JSON sans backticks
        try:
            # Essayer de parser toute la réponse
            data = json.loads(cleaned)
            if isinstance(data, dict):
                logger.info(f"JSON parsé directement: {len(cleaned)} caractères")
                return data
        except json.JSONDecodeError:
            pass
        
        # Chercher le premier objet JSON dans le texte
        json_match = re.search(r'\{.*\}', cleaned, re.DOTALL)
        if json_match:
            json_str = json_match.group(0)
            try:
                data = json.loads(json_str)
                if isinstance(data, dict):
                    logger.info(f"JSON extrait par regex: {len(json_str)} caractères")
                    return data
            except json.JSONDecodeError:
                pass
        
        return None
    
    def _normalize_field_names(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalise les noms de champs pour correspondre au schéma n8n
        
        Args:
            data: Données avec des noms de champs variés
            
        Returns:
            Données avec des noms de champs normalisés (schéma n8n)
        """
        # Mapping simplifié vers le schéma n8n exact
        field_mappings = {
            "fournisseur": ["fournisseur", "supplier", "vendor", "vendeur"],
            "montant_ht": ["montant_ht", "montant", "amount", "total"],
            "numero_facture": ["numero_facture", "numero", "invoice_number", "facture_numero"],
            "date_facture": ["date_facture", "date", "invoice_date"],
            "chrono": ["chrono", "numero_chrono", "chrono_number", "document_chrono"],
            "couverture": ["couverture", "periode_couverture", "periode", "period", "coverage_period"],
            "nom_fichier": ["nom_fichier", "filename", "file_name"]
        }
        
        normalized_data = {}
        
        for standard_field, possible_names in field_mappings.items():
            value = None
            
            # Chercher dans les champs existants (case insensitive)
            data_lower = {k.lower(): v for k, v in data.items()}
            for name in possible_names:
                if name.lower() in data_lower:
                    value = data_lower[name.lower()]
                    break
            
            # Si pas trouvé, mettre None
            normalized_data[standard_field] = value
        
        # Garder les autres champs non mappés (métadonnées, etc.)
        for key, value in data.items():
            key_lower = key.lower()
            if not any(key_lower in [n.lower() for n in names] for names in field_mappings.values()):
                normalized_data[key] = value
        
        return normalized_data
    
    def extract_invoice_data(self, prompt: str) -> Dict[str, Any]:
        """
        Extrait les données de facture depuis le texte PDF
        
        Args:
            prompt: Prompt contenant le texte PDF et les instructions
            
        Returns:
            Données de facture structurées
        """
        try:
            logger.info(f"Envoi de la requête à Bedrock (modèle: {self.model_id}, région: {self.region})")
            
            # Créer le corps de la requête selon le type de modèle
            request_body = self._create_request_body(prompt)
            
            # Appeler le modèle
            response = self.client.invoke_model(
                modelId=self.model_id,
                body=json.dumps(request_body).encode('utf-8')
            )
            
            # Parser la réponse
            response_body = json.loads(response['body'].read())
            response_text = self._parse_response(response_body)
            
            logger.info(f"Réponse reçue de Bedrock: {len(response_text)} caractères")
            
            # Essayer d'extraire le JSON
            extracted_data = self._extract_json_from_response(response_text)
            
            if extracted_data:
                # Normaliser les noms de champs
                extracted_data = self._normalize_field_names(extracted_data)
                
                # Valider les champs requis
                self._validate_extracted_data(extracted_data)
                
                logger.info("Données extraites avec succès depuis Bedrock")
                return extracted_data
            else:
                logger.warning("Aucun JSON valide trouvé, tentative d'extraction manuelle")
                return self._extract_manual_data(response_text)
                
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_msg = e.response['Error']['Message']
            logger.error(f"Erreur AWS Bedrock: {error_code}: {error_msg}")
            raise
        except Exception as e:
            logger.error(f"Erreur inattendue: {str(e)}")
            raise
    
    def _validate_extracted_data(self, data: Dict[str, Any]) -> None:
        """
        Valide les données extraites et ajoute des warnings pour les champs manquants
        
        Args:
            data: Données extraites
        """
        # Champs requis selon le schéma n8n
        required_fields = [
            "fournisseur",
            "montant_ht", 
            "numero_facture",
            "date_facture"
        ]
        
        # Champs optionnels selon le schéma n8n
        optional_fields = [
            "chrono",
            "couverture", 
            "nom_fichier"
        ]
        
        for field in required_fields:
            if field not in data or data[field] is None:
                logger.warning(f"Champ requis manquant dans les données extraites: {field}")
        
        for field in optional_fields:
            if field not in data:
                logger.warning(f"Champ optionnel manquant dans les données extraites: {field}")
                data[field] = None
    
    def _extract_manual_data(self, response_text: str) -> Dict[str, Any]:
        """
        Tente d'extraire manuellement les données depuis la réponse texte
        
        Args:
            response_text: Réponse texte du modèle
            
        Returns:
            Données extraites (partielles)
        """
        logger.warning("Tentative d'extraction manuelle des données depuis la réponse texte")
        
        # Schéma n8n avec noms de champs corrects
        extracted_data = {
            "fournisseur": None,
            "montant_ht": None,
            "numero_facture": None,
            "date_facture": None,
            "chrono": None,
            "couverture": None,
            "nom_fichier": None
        }
        
        # Chercher des patterns spécifiques dans le texte
        patterns = {
            "fournisseur": r'(?:fournisseur|supplier|vendeur)[:\s]+([^\n]+)',
            "montant_ht": r'(?:montant|amount|total)[:\s]+([\d,.]+)\s*€?',
            "numero_facture": r'(?:numero|numéro|facture|invoice)[\s#:]+([A-Za-z0-9\-_]+)',
            "date_facture": r'(?:date|date facture)[:\s]+(\d{2}[/-]\d{2}[/-]\d{4}|\d{4}[/-]\d{2}[/-]\d{2})',
        }
        
        for field, pattern in patterns.items():
            match = re.search(pattern, response_text, re.IGNORECASE)
            if match:
                extracted_data[field] = match.group(1).strip()
        
        # Chercher un montant avec regex plus générique
        amount_match = re.search(r'(\d+[.,]\d{2})\s*€', response_text)
        if amount_match and not extracted_data["montant_ht"]:
            try:
                extracted_data["montant_ht"] = float(amount_match.group(1).replace(',', '.'))
            except:
                pass
        
        return extracted_data
    
    def test_connection(self) -> bool:
        """
        Teste la connexion à Bedrock avec un prompt simple
        
        Returns:
            True si la connexion réussit
        """
        try:
            test_prompt = "Bonjour, ceci est un test. Réponds simplement par 'TEST_OK'."
            request_body = self._create_request_body(test_prompt)
            
            response = self.client.invoke_model(
                modelId=self.model_id,
                body=json.dumps(request_body).encode('utf-8')
            )
            
            response_body = json.loads(response['body'].read())
            response_text = self._parse_response(response_body)
            
            logger.info(f"Test de connexion réussi: {response_text}")
            return True
            
        except Exception as e:
            logger.error(f"Test de connexion échoué: {str(e)}")
            return False
