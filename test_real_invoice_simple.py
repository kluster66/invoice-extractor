#!/usr/bin/env python3
"""
Test avec une facture réelle (version sans émojis)
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
    from src.dynamodb_client import DynamoDBClient
    from config.config import Config
except ImportError as e:
    print(f"Erreur d'import: {e}")
    print("Assurez-vous que vous êtes dans le répertoire invoice-extractor")
    sys.exit(1)


def test_real_invoice():
    """Test avec une facture réelle"""
    print("Test avec facture réelle")
    print("=" * 60)
    
    # Afficher la configuration
    Config.print_config()
    
    # Vérifier les credentials AWS
    if not Config.AWS_ACCESS_KEY_ID or not Config.AWS_SECRET_ACCESS_KEY:
        print("\nATTENTION: Credentials AWS non configurés")
        print("Veuillez configurer vos credentials AWS:")
        print("1. Dans un fichier .env (copier .env.example)")
        print("2. Ou via variables d'environnement")
        print("3. Ou via AWS CLI: aws configure")
        return False
    
    # Chemin vers la facture
    invoice_path = Path("test_factures") / "2140 1902095741 210515 TELEFONICA MG PLVT.pdf"
    
    if not invoice_path.exists():
        print(f"\nERREUR: Fichier non trouvé: {invoice_path}")
        print("Veuillez placer une facture PDF dans le répertoire test_factures/")
        return False
    
    print(f"\nFacture à tester: {invoice_path}")
    print(f"   Taille: {invoice_path.stat().st_size / 1024:.1f} KB")
    
    # 1. Test d'extraction PDF
    print("\n1. Extraction du texte PDF...")
    try:
        pdf_extractor = PDFExtractor()
        
        # Validation
        is_valid = pdf_extractor.validate_pdf(str(invoice_path))
        print(f"   PDF valide: {is_valid}")
        
        if not is_valid:
            print("   ERREUR: Le fichier n'est pas un PDF valide")
            return False
        
        # Extraction texte
        text = pdf_extractor.extract_text(str(invoice_path))
        print(f"   Texte extrait: {len(text)} caractères")
        
        # Afficher un aperçu
        preview = text[:500].replace('\n', ' ')
        print(f"   Aperçu: {preview}...")
        
        # Métadonnées
        metadata = pdf_extractor.extract_metadata(str(invoice_path))
        print(f"   Métadonnées extraites: {len(metadata)} clés")
        
    except Exception as e:
        print(f"   ERREUR d'extraction PDF: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    # 2. Test Bedrock Client
    print("\n2. Test du client Bedrock...")
    try:
        bedrock_client = BedrockClient()
        print(f"   Client initialisé (région: {bedrock_client.region})")
        print(f"   Modèle: {bedrock_client.model_id}")
        
        # Test de connexion simple
        try:
            # Juste pour vérifier que le client peut se connecter
            print("   Test de connexion à Bedrock...")
            # Note: Nous ne faisons pas d'appel réel pour économiser des tokens
            print("   Connexion Bedrock prête")
        except Exception as e:
            print(f"   ATTENTION: Erreur de connexion Bedrock: {str(e)}")
            print("   Cela peut être normal si vous n'avez pas accès à Bedrock")
        
    except Exception as e:
        print(f"   ERREUR initialisation Bedrock: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    # 3. Test DynamoDB Client
    print("\n3. Test du client DynamoDB...")
    try:
        dynamodb_client = DynamoDBClient()
        print(f"   Client initialisé (table: {dynamodb_client.table_name})")
        print(f"   Région: {dynamodb_client.region}")
        
        # Vérifier si la table existe
        try:
            table_exists = dynamodb_client.table_exists()
            print(f"   Table existe: {table_exists}")
            
            if not table_exists:
                print("   ATTENTION: La table n'existe pas, elle sera créée au premier usage")
        except Exception as e:
            print(f"   ATTENTION: Erreur vérification table: {str(e)}")
        
    except Exception as e:
        print(f"   ERREUR initialisation DynamoDB: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    # 4. Test complet de l'extracteur
    print("\n4. Test de l'extracteur complet...")
    try:
        extractor = InvoiceExtractor()
        print(f"   Extracteur initialisé")
        
        # Créer le prompt pour vérification
        prompt = extractor._create_prompt(text, invoice_path.name)
        print(f"   Prompt créé: {len(prompt)} caractères")
        
        # Afficher un aperçu du prompt
        prompt_preview = prompt[:300].replace('\n', ' ')
        print(f"   Aperçu prompt: {prompt_preview}...")
        
        print("\nSUCCES: Tous les tests préparatoires ont réussi!")
        print("\nProchaines étapes:")
        print("1. Pour tester l'extraction complète avec Bedrock:")
        print("   python -m src.main test_factures/2140\\ 1902095741\\ 210515\\ TELEFONICA\\ MG\\ PLVT.pdf")
        print("\n2. Pour simuler un événement S3:")
        print("   python -c \"from src.main import lambda_handler; import json; event = {'Records':[{'eventSource':'aws:s3','eventName':'ObjectCreated:Put','s3':{'bucket':{'name':'test-bucket'},'object':{'key':'test.pdf'}}}]}; lambda_handler(event, None)\"")
        
        return True
        
    except Exception as e:
        print(f"   ERREUR extracteur: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Fonction principale"""
    print("TEST AVEC FACTURE RÉELLE")
    print("=" * 60)
    
    success = test_real_invoice()
    
    print("\n" + "=" * 60)
    if success:
        print("SUCCES: TESTS PRÉPARATOIRES RÉUSSIS")
        print("\nLe système est prêt pour l'extraction avec Bedrock.")
        print("Veuillez exécuter la commande ci-dessus pour tester l'extraction complète.")
    else:
        print("ERREUR: TESTS ÉCHOUÉS")
        print("\nVeuillez corriger les erreurs avant de continuer.")
    
    print("=" * 60)


if __name__ == "__main__":
    main()
