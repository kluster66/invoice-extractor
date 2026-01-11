#!/usr/bin/env python3
"""
Test avec différents modèles Bedrock (version simple sans émojis)
"""

import os
import sys
import json
from pathlib import Path

# Ajouter les répertoires au path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))
sys.path.insert(0, str(current_dir / "src"))

try:
    from src.main import InvoiceExtractor
    from src.pdf_extractor import PDFExtractor
    from src.bedrock_client import BedrockClient
    from config.config import Config
except ImportError as e:
    print(f"Erreur d'import: {e}")
    print("Assurez-vous que vous êtes dans le répertoire invoice-extractor")
    sys.exit(1)


def test_model_access(model_key: str) -> bool:
    """
    Teste l'accès à un modèle spécifique
    """
    print(f"\nTest d'acces au modele: {model_key}")
    print("-" * 40)
    
    # Changer le modèle
    if not Config.set_model(model_key):
        return False
    
    # Créer un client Bedrock avec le nouveau modèle
    try:
        client = BedrockClient()
        print(f"OK - Client initialise")
        print(f"  Modele: {client.model_id}")
        print(f"  Region: {client.region}")
        
        # Tester une connexion simple
        print("  Test de connexion...")
        
        # Créer un prompt de test simple
        test_prompt = "Bonjour, ceci est un test. Reponds simplement par 'OK'."
        
        try:
            # Tenter d'appeler le modèle
            response = client.client.invoke_model(
                modelId=client.model_id,
                body=json.dumps({
                    "prompt": f"\n\nHuman: {test_prompt}\n\nAssistant:",
                    "max_tokens_to_sample": 10,
                    "temperature": 0.1
                }).encode('utf-8')
            )
            
            response_body = json.loads(response['body'].read())
            print(f"OK - Acces OK - Reponse: {response_body.get('completion', 'N/A')}")
            return True
            
        except Exception as e:
            error_msg = str(e)
            print(f"ERREUR - Erreur d'acces: {error_msg}")
            
            # Analyser l'erreur
            if "ResourceNotFoundException" in error_msg:
                print("  -> Le modele n'est pas accessible dans cette region/compte")
                print("  -> Verifiez: AWS Console > Bedrock > Model access")
            elif "AccessDeniedException" in error_msg:
                print("  -> Permission refusee")
                print("  -> Verifiez les IAM permissions pour Bedrock")
            elif "ThrottlingException" in error_msg:
                print("  -> Limite de requetes atteinte")
                print("  -> Attendez quelques secondes")
            else:
                print(f"  -> Erreur inconnue: {error_msg}")
            
            return False
            
    except Exception as e:
        print(f"ERREUR - Erreur d'initialisation: {str(e)}")
        return False


def main():
    """Fonction principale"""
    print("TEST DE DIFFERENTS MODELES BEDROCK")
    print("=" * 60)
    
    # Afficher la configuration actuelle
    Config.print_config()
    
    # Afficher les modèles disponibles
    Config.list_available_models()
    
    # Modèles à tester (par ordre de priorité)
    models_to_test = [
        "claude-3-haiku",      # Claude Haiku (moins cher, plus rapide)
        "claude-instant",      # Claude Instant (ancienne version)
        "claude-2.1",          # Claude 2.1
        "titan-text-express",  # Amazon Titan
        "llama-3-70b",         # Meta Llama 3
        "llama-2-70b",         # Meta Llama 2
    ]
    
    print(f"\nModeles a tester: {', '.join(models_to_test)}")
    
    # Tester l'accès à chaque modèle
    accessible_models = []
    
    for model_key in models_to_test:
        if test_model_access(model_key):
            accessible_models.append(model_key)
    
    print(f"\n{'='*60}")
    print(f"RESULTATS D'ACCES AUX MODELES")
    print(f"{'='*60}")
    
    if accessible_models:
        print(f"SUCCES - Modeles accessibles: {', '.join(accessible_models)}")
        
        # Recommandation
        print(f"\nRECOMMANDATION: Utilisez le modele: {accessible_models[0]}")
        print(f"\nPour configurer definitivement ce modele:")
        print(f"1. Variable d'environnement: export BEDROCK_MODEL_ID={Config.BEDROCK_AVAILABLE_MODELS[accessible_models[0]]}")
        print(f"2. Fichier .env: BEDROCK_MODEL_ID={Config.BEDROCK_AVAILABLE_MODELS[accessible_models[0]]}")
        print(f"3. Code Python: Config.set_model('{accessible_models[0]}')")
            
    else:
        print("ECHEC - Aucun modele n'est accessible")
        print("\nVeuillez:")
        print("1. Acceder a AWS Console > Bedrock > Model access")
        print("2. Demander l'acces a au moins un modele")
        print("3. Attendre l'approbation (quelques minutes a quelques heures)")
        print("\nModeles recommandes pour commencer:")
        print("  - Claude 3 Haiku (rapide, economique)")
        print("  - Amazon Titan Text Express (Amazon native)")
        print("  - Claude Instant (bon rapport qualite/prix)")
    
    print(f"\n{'='*60}")
    print("CONFIGURATION RECOMMANDEE POUR LA PRODUCTION:")
    print(f"{'='*60}")
    print("1. Claude 3 Haiku: Economique et rapide pour l'extraction")
    print("2. Claude 3 Sonnet: Meilleure precision (necessite activation)")
    print("3. Amazon Titan: Integration AWS native")
    print("\nPour activer Claude 3 Sonnet:")
    print("  - AWS Console > Bedrock > Model access")
    print("  - Selectionner 'Anthropic Claude 3 Sonnet'")
    print("  - Remplir le formulaire de cas d'utilisation")
    print("  - Attendre l'approbation")


if __name__ == "__main__":
    main()
