"""
Configuration de l'application
"""

import os
import boto3
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()


def get_aws_region() -> str:
    """
    Obtient la région AWS de manière intelligente :
    1. Variable d'environnement AWS_REGION
    2. Configuration AWS CLI
    3. Valeur par défaut us-west-2
    """
    # 1. Variable d'environnement
    env_region = os.getenv("AWS_REGION")
    if env_region:
        return env_region
    
    try:
        # 2. Configuration AWS CLI
        session = boto3.Session()
        if session.region_name:
            return session.region_name
    except Exception:
        pass
    
    # 3. Valeur par défaut
    return "us-west-2"


def get_aws_credentials():
    """
    Obtient les credentials AWS de manière intelligente :
    1. Configuration AWS CLI
    2. Variables d'environnement
    """
    try:
        session = boto3.Session()
        credentials = session.get_credentials()
        if credentials:
            return {
                "access_key": credentials.access_key,
                "secret_key": credentials.secret_key,
                "token": credentials.token
            }
    except Exception:
        pass
    
    # Fallback aux variables d'environnement
    return {
        "access_key": os.getenv("AWS_ACCESS_KEY_ID"),
        "secret_key": os.getenv("AWS_SECRET_ACCESS_KEY"),
        "token": os.getenv("AWS_SESSION_TOKEN")
    }


class Config:
    """Classe de configuration"""
    
    # AWS Configuration
    AWS_REGION = get_aws_region()
    
    # Obtenir les credentials
    credentials = get_aws_credentials()
    AWS_ACCESS_KEY_ID = credentials["access_key"]
    AWS_SECRET_ACCESS_KEY = credentials["secret_key"]
    AWS_SESSION_TOKEN = credentials["token"]
    
    # Bedrock Configuration
    BEDROCK_MODEL_ID = os.getenv("BEDROCK_MODEL_ID", "anthropic.claude-3-sonnet-20240229-v1:0")
    BEDROCK_MAX_TOKENS = int(os.getenv("BEDROCK_MAX_TOKENS", "1000"))
    BEDROCK_TEMPERATURE = float(os.getenv("BEDROCK_TEMPERATURE", "0.1"))
    
    # Modèles Bedrock disponibles (pour référence et sélection facile)
    BEDROCK_AVAILABLE_MODELS = {
        # Anthropic Claude Models
        "claude-3-sonnet": "anthropic.claude-3-sonnet-20240229-v1:0",
        "claude-3-haiku": "anthropic.claude-3-haiku-20240307-v1:0",
        "claude-3-opus": "anthropic.claude-3-opus-20240229-v1:0",
        "claude-2.1": "anthropic.claude-v2:1",
        "claude-instant": "anthropic.claude-instant-v1",
        
        # Amazon Titan Models
        "titan-text-express": "amazon.titan-text-express-v1",
        "titan-text-lite": "amazon.titan-text-lite-v1",
        "titan-embed": "amazon.titan-embed-text-v1",
        
        # AI21 Labs Jurassic Models
        "jurassic-2-ultra": "ai21.j2-ultra-v1",
        "jurassic-2-mid": "ai21.j2-mid-v1",
        
        # Cohere Models
        "cohere-command": "cohere.command-text-v14",
        "cohere-embed": "cohere.embed-english-v3",
        
        # Meta Llama Models
        "llama-3-70b": "meta.llama3-70b-instruct-v1:0",
        "llama-3-8b": "meta.llama3-8b-instruct-v1:0",
        "llama-2-70b": "meta.llama2-70b-chat-v1",
        "llama-2-13b": "meta.llama2-13b-chat-v1",
    }
    
    # DynamoDB Configuration
    DYNAMODB_TABLE_NAME = os.getenv("DYNAMODB_TABLE_NAME", "invoices")
    DYNAMODB_READ_CAPACITY = int(os.getenv("DYNAMODB_READ_CAPACITY", "5"))
    DYNAMODB_WRITE_CAPACITY = int(os.getenv("DYNAMODB_WRITE_CAPACITY", "5"))
    
    # S3 Configuration
    S3_INPUT_BUCKET = os.getenv("S3_INPUT_BUCKET", "invoice-input-bucket")
    S3_PROCESSED_PREFIX = os.getenv("S3_PROCESSED_PREFIX", "processed/")
    S3_ERROR_PREFIX = os.getenv("S3_ERROR_PREFIX", "error/")
    
    # Application Configuration
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    MAX_PDF_SIZE_MB = int(os.getenv("MAX_PDF_SIZE_MB", "50"))
    TEMP_DIR = os.getenv("TEMP_DIR", "/tmp")
    
    # Extraction Configuration
    EXTRACTION_TIMEOUT = int(os.getenv("EXTRACTION_TIMEOUT", "300"))  # 5 minutes
    MAX_RETRY_ATTEMPTS = int(os.getenv("MAX_RETRY_ATTEMPTS", "3"))
    
    @classmethod
    def set_model(cls, model_key: str) -> bool:
        """
        Change le modèle Bedrock à utiliser
        
        Args:
            model_key: Clé du modèle dans BEDROCK_AVAILABLE_MODELS
            
        Returns:
            True si le modèle a été changé avec succès
        """
        if model_key in cls.BEDROCK_AVAILABLE_MODELS:
            cls.BEDROCK_MODEL_ID = cls.BEDROCK_AVAILABLE_MODELS[model_key]
            print(f"Modèle changé pour: {model_key} -> {cls.BEDROCK_MODEL_ID}")
            return True
        else:
            print(f"Modèle non trouvé: {model_key}")
            print(f"Modèles disponibles: {', '.join(cls.BEDROCK_AVAILABLE_MODELS.keys())}")
            return False
    
    @classmethod
    def get_available_models(cls) -> Dict[str, str]:
        """
        Retourne la liste des modèles disponibles
        
        Returns:
            Dictionnaire des modèles disponibles
        """
        return cls.BEDROCK_AVAILABLE_MODELS
    
    @classmethod
    def list_available_models(cls) -> None:
        """
        Affiche la liste des modèles disponibles
        """
        print("Modèles Bedrock disponibles:")
        print("-" * 50)
        for key, value in cls.BEDROCK_AVAILABLE_MODELS.items():
            print(f"{key:30} -> {value}")
        print("-" * 50)
    
    @classmethod
    def validate(cls) -> bool:
        """
        Valide la configuration
        
        Returns:
            True si la configuration est valide
        """
        errors = []
        
        # Vérifier les credentials AWS
        if not cls.AWS_ACCESS_KEY_ID:
            errors.append("AWS_ACCESS_KEY_ID non défini")
        if not cls.AWS_SECRET_ACCESS_KEY:
            errors.append("AWS_SECRET_ACCESS_KEY non défini")
        
        # Vérifier le modèle Bedrock
        if cls.BEDROCK_MODEL_ID not in cls.BEDROCK_AVAILABLE_MODELS.values():
            print(f"Attention: Modèle Bedrock '{cls.BEDROCK_MODEL_ID}' n'est pas dans la liste des modèles connus")
            print("Cela peut être normal si vous utilisez un modèle personnalisé ou une nouvelle version")
        
        # Vérifier les tailles
        if cls.MAX_PDF_SIZE_MB <= 0:
            errors.append("MAX_PDF_SIZE_MB doit être positif")
        
        if cls.EXTRACTION_TIMEOUT <= 0:
            errors.append("EXTRACTION_TIMEOUT doit être positif")
        
        if errors:
            print("Erreurs de configuration:")
            for error in errors:
                print(f"  - {error}")
            return False
        
        return True
    
    @classmethod
    def to_dict(cls) -> Dict[str, Any]:
        """
        Convertit la configuration en dictionnaire
        
        Returns:
            Dictionnaire de configuration
        """
        config_dict = {}
        
        for key in dir(cls):
            if not key.startswith('_') and key.isupper():
                value = getattr(cls, key)
                config_dict[key] = value
        
        return config_dict
    
    @classmethod
    def print_config(cls, hide_secrets: bool = True) -> None:
        """
        Affiche la configuration
        
        Args:
            hide_secrets: Masquer les valeurs sensibles
        """
        print("Configuration actuelle:")
        print("-" * 50)
        
        for key, value in cls.to_dict().items():
            if hide_secrets and any(secret in key.lower() for secret in ['key', 'secret', 'token', 'password']):
                display_value = "***MASQUÉ***"
            else:
                display_value = value
            
            print(f"{key}: {display_value}")
        
        print("-" * 50)


# Instance de configuration globale
config = Config()
