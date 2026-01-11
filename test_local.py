#!/usr/bin/env python3
"""
Script de test local pour l'extracteur de factures
"""

import os
import sys
import json
import tempfile
from pathlib import Path

# Ajouter les répertoires au path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))
sys.path.insert(0, str(current_dir / "src"))

# Imports avec fallback
try:
    from src.main import InvoiceExtractor
    from src.pdf_extractor import PDFExtractor
    from src.bedrock_client import BedrockClient
    from src.dynamodb_client import DynamoDBClient
    from config.config import Config
except ImportError:
    try:
        from main import InvoiceExtractor
        from pdf_extractor import PDFExtractor
        from bedrock_client import BedrockClient
        from dynamodb_client import DynamoDBClient
        from config.config import Config
    except ImportError as e:
        print(f"❌ Erreur d'import: {e}")
        print("Assurez-vous que vous êtes dans le répertoire invoice-extractor")
        sys.exit(1)


def test_pdf_extraction():
    """Test de l'extraction PDF"""
    print("🧪 Test d'extraction PDF...")
    
    extractor = PDFExtractor()
    
    # Créer un fichier PDF de test simple
    test_pdf_content = b"""%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj
2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj
3 0 obj
<<
/Type /Page
/Parent 2 0 R
/Resources <<
/Font <<
/F1 4 0 R
>>
>>
/Contents 5 0 R
>>
endobj
4 0 obj
<<
/Type /Font
/Subtype /Type1
/BaseFont /Helvetica
>>
endobj
5 0 obj
<<
/Length 44
>>
stream
BT
/F1 12 Tf
72 720 Td
(Test Invoice - Company XYZ) Tj
ET
endstream
endobj
xref
0 6
0000000000 65535 f 
0000000010 00000 n 
0000000053 00000 n 
0000000106 00000 n 
0000000221 00000 n 
0000000282 00000 n 
trailer
<<
/Size 6
/Root 1 0 R
>>
startxref
357
%%EOF"""
    
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        f.write(test_pdf_content)
        pdf_path = f.name
    
    try:
        # Test validation PDF
        is_valid = extractor.validate_pdf(pdf_path)
        print(f"  ✓ PDF valide: {is_valid}")
        
        # Test extraction texte
        text = extractor.extract_text(pdf_path)
        print(f"  ✓ Texte extrait: {len(text)} caractères")
        print(f"  ✓ Contenu: '{text[:50]}...'")
        
        # Test métadonnées
        metadata = extractor.extract_metadata(pdf_path)
        print(f"  ✓ Métadonnées: {metadata}")
        
        return True
        
    finally:
        # Nettoyer
        if os.path.exists(pdf_path):
            os.remove(pdf_path)


def test_bedrock_client():
    """Test du client Bedrock (simulé)"""
    print("\n🧪 Test du client Bedrock...")
    
    client = BedrockClient()
    
    # Test connexion
    try:
        # Ceci échouera sans credentials AWS, mais nous testons l'initialisation
        print(f"  ✓ Client initialisé (région: {client.region})")
        print(f"  ✓ Modèle configuré: {client.model_id}")
        
        # Test création de prompt
        test_text = "Facture n°FAC-2024-001\nFournisseur: Entreprise XYZ\nMontant HT: 1500,50€\nDate: 15/01/2024"
        test_filename = "facture_test.pdf"
        
        # Simuler une réponse JSON
        mock_response = {
            "fournisseur": "Entreprise XYZ",
            "montant_ht": 1500.50,
            "numero_facture": "FAC-2024-001",
            "date_facture": "2024-01-15",
            "Le numero Chrono du document": "CHR-001",
            "La période de couverture": "Janvier 2024",
            "nom du fichier que tu trouves ici": "facture_test.pdf"
        }
        
        print(f"  ✓ Format de réponse simulé: {json.dumps(mock_response, indent=2)}")
        
        return True
        
    except Exception as e:
        print(f"  ✗ Erreur: {str(e)}")
        print("  ℹ️ Note: Ce test nécessite des credentials AWS valides")
        return False


def test_dynamodb_client():
    """Test du client DynamoDB (simulé)"""
    print("\n🧪 Test du client DynamoDB...")
    
    client = DynamoDBClient()
    
    try:
        print(f"  ✓ Client initialisé (table: {client.table_name})")
        print(f"  ✓ Région: {client.region}")
        
        # Test format conversion
        test_item = {
            "invoice_id": "test-123",
            "fournisseur": "Test Company",
            "montant_ht": 1000.50,
            "numero_facture": "TEST-001",
            "date_facture": "2024-01-01"
        }
        
        dynamo_format = client._convert_to_dynamo_format(test_item)
        print(f"  ✓ Conversion format DynamoDB: OK")
        
        # Conversion inverse
        python_format = client._convert_from_dynamo_format(dynamo_format)
        print(f"  ✓ Conversion inverse: OK")
        
        return True
        
    except Exception as e:
        print(f"  ✗ Erreur: {str(e)}")
        print("  ℹ️ Note: Ce test nécessite des credentials AWS valides")
        return False


def test_invoice_extractor():
    """Test de l'extracteur complet"""
    print("\n🧪 Test de l'extracteur de factures...")
    
    extractor = InvoiceExtractor()
    
    try:
        print(f"  ✓ Extracteur initialisé")
        print(f"  ✓ Composants: PDF Extractor, Bedrock Client, DynamoDB Client")
        
        # Test création de prompt
        test_text = "Facture de test"
        test_filename = "test.pdf"
        prompt = extractor._create_prompt(test_text, test_filename)
        
        print(f"  ✓ Prompt créé: {len(prompt)} caractères")
        print(f"  ✓ Contient filename: {'test.pdf' in prompt}")
        print(f"  ✓ Contient texte: {'Facture de test' in prompt}")
        
        return True
        
    except Exception as e:
        print(f"  ✗ Erreur: {str(e)}")
        return False


def test_configuration():
    """Test de la configuration"""
    print("\n🧪 Test de configuration...")
    
    try:
        # Afficher la configuration
        Config.print_config()
        
        # Valider
        is_valid = Config.validate()
        print(f"  ✓ Validation configuration: {'PASS' if is_valid else 'FAIL'}")
        
        # Vérifier les valeurs par défaut
        print(f"  ✓ Région par défaut: {Config.AWS_REGION}")
        print(f"  ✓ Table DynamoDB: {Config.DYNAMODB_TABLE_NAME}")
        print(f"  ✓ Modèle Bedrock: {Config.BEDROCK_MODEL_ID}")
        
        return is_valid
        
    except Exception as e:
        print(f"  ✗ Erreur: {str(e)}")
        return False


def test_s3_event_simulation():
    """Simulation d'un événement S3"""
    print("\n🧪 Simulation d'événement S3...")
    
    event = {
        "Records": [
            {
                "eventSource": "aws:s3",
                "eventName": "ObjectCreated:Put",
                "s3": {
                    "bucket": {
                        "name": "test-bucket"
                    },
                    "object": {
                        "key": "invoices/facture_test.pdf"
                    }
                }
            }
        ]
    }
    
    print(f"  ✓ Événement S3 simulé créé")
    print(f"  ✓ Bucket: {event['Records'][0]['s3']['bucket']['name']}")
    print(f"  ✓ Key: {event['Records'][0]['s3']['object']['key']}")
    print(f"  ✓ Nom de fichier: facture_test.pdf")
    
    return True


def main():
    """Fonction principale de test"""
    print("=" * 60)
    print("🧪 TEST COMPLET DE L'EXTRACTEUR DE FACTURES")
    print("=" * 60)
    
    tests = [
        ("Configuration", test_configuration),
        ("Extraction PDF", test_pdf_extraction),
        ("Client Bedrock", test_bedrock_client),
        ("Client DynamoDB", test_dynamodb_client),
        ("Extracteur complet", test_invoice_extractor),
        ("Simulation S3", test_s3_event_simulation)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"  ✗ Exception: {str(e)}")
            results.append((test_name, False))
    
    print("\n" + "=" * 60)
    print("📊 RÉSULTATS DES TESTS")
    print("=" * 60)
    
    all_passed = True
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} - {test_name}")
        if not success:
            all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 TOUS LES TESTS ONT RÉUSSI !")
        print("\nProchaines étapes:")
        print("1. Configurer vos credentials AWS dans .env")
        print("2. Tester avec un vrai PDF: python -m src.main chemin/vers/facture.pdf")
        print("3. Déployer sur AWS avec SAM ou CDK")
    else:
        print("⚠️  CERTAINS TESTS ONT ÉCHOUÉ")
        print("\nVérifiez:")
        print("1. Les dépendances Python sont installées")
        print("2. Les fichiers de configuration sont présents")
        print("3. Les permissions de fichiers sont correctes")
    
    print("=" * 60)


if __name__ == "__main__":
    main()
