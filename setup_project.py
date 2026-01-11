#!/usr/bin/env python3
"""
Script de configuration du projet Invoice Extractor
"""

import os
import sys
import subprocess
from pathlib import Path

def print_header(text):
    """Affiche un en-tête stylisé"""
    print("\n" + "=" * 60)
    print(f" {text}")
    print("=" * 60)

def check_aws_cli():
    """Vérifie si AWS CLI est configuré"""
    print_header("VÉRIFICATION AWS CLI")
    
    try:
        # Vérifier si AWS CLI est installé
        result = subprocess.run(["aws", "--version"], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ AWS CLI installé")
            print(f"   Version: {result.stdout.strip()}")
        else:
            print("❌ AWS CLI non trouvé")
            print("   Installez AWS CLI: https://aws.amazon.com/cli/")
            return False
        
        # Vérifier la configuration
        region_result = subprocess.run(["aws", "configure", "get", "region"], capture_output=True, text=True)
        if region_result.returncode == 0 and region_result.stdout.strip():
            print(f"✅ Région AWS configurée: {region_result.stdout.strip()}")
        else:
            print("⚠️  Région AWS non configurée")
            print("   Exécutez: aws configure set region us-west-2")
        
        # Vérifier les credentials
        creds_result = subprocess.run(["aws", "sts", "get-caller-identity"], capture_output=True, text=True)
        if creds_result.returncode == 0:
            print("✅ Credentials AWS valides")
        else:
            print("❌ Credentials AWS invalides ou manquants")
            print("   Exécutez: aws configure")
            return False
        
        return True
        
    except FileNotFoundError:
        print("❌ AWS CLI non installé")
        print("   Téléchargez depuis: https://aws.amazon.com/cli/")
        return False

def check_python_deps():
    """Vérifie les dépendances Python"""
    print_header("VÉRIFICATION DES DÉPENDANCES")
    
    try:
        import boto3
        print("✅ boto3 installé")
    except ImportError:
        print("❌ boto3 non installé")
        print("   Exécutez: pip install boto3")
        return False
    
    try:
        import PyPDF2
        print("✅ PyPDF2 installé")
    except ImportError:
        print("❌ PyPDF2 non installé")
        print("   Exécutez: pip install PyPDF2")
        return False
    
    try:
        import pdfplumber
        print("✅ pdfplumber installé")
    except ImportError:
        print("❌ pdfplumber non installé")
        print("   Exécutez: pip install pdfplumber")
        return False
    
    return True

def create_env_file():
    """Crée le fichier .env si nécessaire"""
    print_header("CONFIGURATION .ENV")
    
    env_file = Path(".env")
    env_example = Path("env.example")
    
    if env_file.exists():
        print("✅ Fichier .env existe déjà")
        return True
    
    if not env_example.exists():
        print("❌ Fichier env.example non trouvé")
        return False
    
    # Copier env.example vers .env
    try:
        with open(env_example, 'r', encoding='utf-8') as src:
            content = src.read()
        
        with open(env_file, 'w', encoding='utf-8') as dst:
            dst.write(content)
        
        print("✅ Fichier .env créé à partir de env.example")
        print("   Éditez-le pour personnaliser la configuration")
        return True
        
    except Exception as e:
        print(f"❌ Erreur lors de la création de .env: {e}")
        return False

def test_bedrock_access():
    """Teste l'accès à Bedrock"""
    print_header("TEST ACCÈS BEDROCK")
    
    try:
        # Importer après vérification des dépendances
        sys.path.insert(0, str(Path(__file__).parent))
        from config.config import Config
        
        print(f"Région configurée: {Config.AWS_REGION}")
        print(f"Modèle par défaut: {Config.BEDROCK_MODEL_ID}")
        
        # Tester avec un modèle qui ne nécessite pas d'activation
        Config.BEDROCK_MODEL_ID = "meta.llama3-1-70b-instruct-v1:0"
        
        import boto3
        from botocore.exceptions import ClientError
        
        bedrock = boto3.client('bedrock-runtime', region_name=Config.AWS_REGION)
        
        try:
            # Test simple
            response = bedrock.list_foundation_models()
            model_count = len(response.get('modelSummaries', []))
            print(f"✅ Accès Bedrock OK - {model_count} modèles disponibles")
            return True
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == "AccessDeniedException":
                print("❌ Permission Bedrock refusée")
                print("   Ajoutez AmazonBedrockFullAccess au rôle IAM")
            else:
                print(f"⚠️  Erreur Bedrock: {error_code}")
            return False
            
    except Exception as e:
        print(f"❌ Erreur lors du test Bedrock: {e}")
        return False

def run_quick_test():
    """Exécute un test rapide"""
    print_header("TEST RAPIDE")
    
    test_file = Path("test_factures")
    if not test_file.exists():
        print("⚠️  Répertoire test_factures non trouvé")
        print("   Créez-le et ajoutez une facture PDF pour tester")
        return False
    
    pdf_files = list(test_file.glob("*.pdf"))
    if not pdf_files:
        print("⚠️  Aucun fichier PDF trouvé dans test_factures/")
        print("   Ajoutez une facture PDF pour tester")
        return False
    
    test_pdf = pdf_files[0]
    print(f"Fichier de test: {test_pdf}")
    
    try:
        # Importer et tester
        sys.path.insert(0, str(Path(__file__).parent))
        sys.path.insert(0, str(Path(__file__).parent / "src"))
        
        from src.pdf_extractor import PDFExtractor
        
        extractor = PDFExtractor()
        text = extractor.extract_text(str(test_pdf))
        
        if text and len(text) > 10:
            print(f"✅ Extraction PDF réussie: {len(text)} caractères")
            print(f"   Aperçu: {text[:100]}...")
            return True
        else:
            print("❌ Échec de l'extraction PDF")
            return False
            
    except Exception as e:
        print(f"❌ Erreur lors du test: {e}")
        return False

def show_next_steps():
    """Affiche les prochaines étapes"""
    print_header("PROCHAINES ÉTAPES")
    
    steps = [
        "1. Tester différents modèles: python test_models_simple.py",
        "2. Lister les modèles disponibles: python list_available_models.py",
        "3. Configurer un modèle spécifique: python configure_model.py",
        "4. Tester l'extraction complète: python -m src.main test_factures/votre_facture.pdf",
        "5. Pour déployer sur AWS:",
        "   - SAM: sam build && sam deploy --guided",
        "   - Manuel: voir DEPLOY.md",
        "",
        "Documentation:",
        "- README.md : Vue d'ensemble",
        "- CONFIGURATION.md : Guide de configuration",
        "- DEPLOY.md : Guide de déploiement",
        "- CHANGELOG.md : Historique des changements",
    ]
    
    for step in steps:
        print(f"   {step}")

def main():
    """Fonction principale"""
    print_header("CONFIGURATION INVOICE EXTRACTOR v2.0.0")
    
    checks = [
        ("AWS CLI", check_aws_cli),
        ("Dépendances Python", check_python_deps),
        ("Fichier .env", create_env_file),
        ("Accès Bedrock", test_bedrock_access),
        ("Test rapide", run_quick_test),
    ]
    
    results = []
    for name, check_func in checks:
        print(f"\n🔍 {name}...")
        try:
            result = check_func()
            results.append((name, result))
        except Exception as e:
            print(f"❌ Erreur lors de la vérification: {e}")
            results.append((name, False))
    
    # Résumé
    print_header("RÉSUMÉ DE LA CONFIGURATION")
    
    all_passed = True
    for name, passed in results:
        status = "✅" if passed else "❌"
        print(f"{status} {name}")
        if not passed:
            all_passed = False
    
    if all_passed:
        print("\n🎉 Toutes les vérifications ont réussi !")
    else:
        print("\n⚠️  Certaines vérifications ont échoué")
        print("   Corrigez les problèmes avant de continuer")
    
    show_next_steps()
    
    return all_passed

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nConfiguration interrompue")
        sys.exit(1)
