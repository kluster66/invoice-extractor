#!/usr/bin/env python3
"""
Test avec différents modèles Bedrock
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
    
    Args:
        model_key: Clé du modèle à tester
        
    Returns:
        True si l'accès est disponible
    """
    print(f"\nTest d'accès au modèle: {model_key}")
    print("-" * 40)
    
    # Changer le modèle
    if not Config.set_model(model_key):
        return False
    
    # Créer un client Bedrock avec le nouveau modèle
    try:
        client = BedrockClient()
        print(f"✓ Client initialisé")
        print(f"  Modèle: {client.model_id}")
        print(f"  Région: {client.region}")
        
        # Tester une connexion simple
        print("  Test de connexion...")
        
        # Créer un prompt de test simple
        test_prompt = "Bonjour, ceci est un test. Réponds simplement par 'OK'."
        
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
            print(f"✓ Accès OK - Réponse: {response_body.get('completion', 'N/A')}")
            return True
            
        except Exception as e:
            error_msg = str(e)
            print(f"✗ Erreur d'accès: {error_msg}")
            
            # Analyser l'erreur
            if "ResourceNotFoundException" in error_msg:
                print("  → Le modèle n'est pas accessible dans cette région/compte")
                print("  → Vérifiez: AWS Console > Bedrock > Model access")
            elif "AccessDeniedException" in error_msg:
                print("  → Permission refusée")
                print("  → Vérifiez les IAM permissions pour Bedrock")
            elif "ThrottlingException" in error_msg:
                print("  → Limite de requêtes atteinte")
                print("  → Attendez quelques secondes")
            else:
                print(f"  → Erreur inconnue: {error_msg}")
            
            return False
            
    except Exception as e:
        print(f"✗ Erreur d'initialisation: {str(e)}")
        return False


def test_extraction_with_model(model_key: str, pdf_path: str) -> bool:
    """
    Teste l'extraction complète avec un modèle spécifique
    
    Args:
        model_key: Clé du modèle à tester
        pdf_path: Chemin vers le PDF
        
    Returns:
        True si l'extraction a réussi
    """
    print(f"\nTest d'extraction avec modèle: {model_key}")
    print("-" * 50)
    
    # Changer le modèle
    if not Config.set_model(model_key):
        return False
    
    # Créer un extracteur
    try:
        extractor = InvoiceExtractor()
        
        # Extraire le texte du PDF
        pdf_extractor = PDFExtractor()
        text = pdf_extractor.extract_text(pdf_path)
        
        if not text or len(text) < 10:
            print("✗ Texte PDF trop court ou vide")
            return False
        
        print(f"✓ Texte extrait: {len(text)} caractères")
        
        # Créer le prompt
        prompt = extractor._create_prompt(text, os.path.basename(pdf_path))
        print(f"✓ Prompt créé: {len(prompt)} caractères")
        
        # Tenter l'extraction
        print("  Appel à Bedrock...")
        try:
            extracted_data = extractor.bedrock_client.extract_invoice_data(prompt)
            print(f"✓ Extraction réussie!")
            print(f"  Données extraites: {json.dumps(extracted_data, indent=2, ensure_ascii=False)}")
            return True
            
        except Exception as e:
            print(f"✗ Erreur d'extraction: {str(e)}")
            return False
            
    except Exception as e:
        print(f"✗ Erreur générale: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Fonction principale"""
    print("TEST DE DIFFÉRENTS MODÈLES BEDROCK")
    print("=" * 60)
    
    # Afficher la configuration actuelle
    Config.print_config()
    
    # Afficher les modèles disponibles
    Config.list_available_models()
    
    # Chemin vers la facture de test
    pdf_path = "test_factures/2140 1902095741 210515 TELEFONICA MG PLVT.pdf"
    
    if not os.path.exists(pdf_path):
        print(f"\n✗ Fichier PDF non trouvé: {pdf_path}")
        print("Veuillez placer une facture dans le répertoire test_factures/")
        return
    
    print(f"\nFichier de test: {pdf_path}")
    print(f"Taille: {os.path.getsize(pdf_path) / 1024:.1f} KB")
    
    # Modèles à tester (par ordre de priorité)
    models_to_test = [
        "claude-3-haiku",      # Claude Haiku (moins cher, plus rapide)
        "claude-instant",      # Claude Instant (ancienne version)
        "claude-2.1",          # Claude 2.1
        "titan-text-express",  # Amazon Titan
        "llama-3-70b",         # Meta Llama 3
        "llama-2-70b",         # Meta Llama 2
    ]
    
    print(f"\nModèles à tester: {', '.join(models_to_test)}")
    
    # Tester l'accès à chaque modèle
    accessible_models = []
    
    for model_key in models_to_test:
        if test_model_access(model_key):
            accessible_models.append(model_key)
    
    print(f"\n{'='*60}")
    print(f"RÉSULTATS D'ACCÈS AUX MODÈLES")
    print(f"{'='*60}")
    
    if accessible_models:
        print(f"✓ Modèles accessibles: {', '.join(accessible_models)}")
        
        # Tester l'extraction avec le premier modèle accessible
        print(f"\nTest d'extraction avec le premier modèle accessible: {accessible_models[0]}")
        success = test_extraction_with_model(accessible_models[0], pdf_path)
        
        if success:
            print(f"\n✅ SUCCÈS! Vous pouvez utiliser le modèle: {accessible_models[0]}")
            print(f"\nPour configurer définitivement ce modèle:")
            print(f"1. Variable d'environnement: export BEDROCK_MODEL_ID={Config.BEDROCK_AVAILABLE_MODELS[accessible_models[0]]}")
            print(f"2. Fichier .env: BEDROCK_MODEL_ID={Config.BEDROCK_AVAILABLE_MODELS[accessible_models[0]]}")
            print(f"3. Code Python: Config.set_model('{accessible_models[0]}')")
        else:
            print(f"\n❌ L'extraction a échoué avec {accessible_models[0]}")
            print("Essayez un autre modèle de la liste des modèles accessibles")
            
    else:
        print("❌ Aucun modèle n'est accessible")
        print("\nVeuillez:")
        print("1. Accéder à AWS Console > Bedrock > Model access")
        print("2. Demander l'accès à au moins un modèle")
        print("3. Attendre l'approbation (quelques minutes à quelques heures)")
        print("\nModèles recommandés pour commencer:")
        print("  - Claude 3 Haiku (rapide, économique)")
        print("  - Amazon Titan Text Express (Amazon native)")
        print("  - Claude Instant (bon rapport qualité/prix)")
    
    print(f"\n{'='*60}")
    print("CONFIGURATION RECOMMANDÉE POUR LA PRODUCTION:")
    print(f"{'='*60}")
    print("1. Claude 3 Haiku: Économique et rapide pour l'extraction")
    print("2. Claude 3 Sonnet: Meilleure précision (nécessite activation)")
    print("3. Amazon Titan: Intégration AWS native")
    print("\nPour activer Claude 3 Sonnet:")
    print("  - AWS Console > Bedrock > Model access")
    print("  - Sélectionner 'Anthropic Claude 3 Sonnet'")
    print("  - Remplir le formulaire de cas d'utilisation")
    print("  - Attendre l'approbation")


if __name__ == "__main__":
    main()
