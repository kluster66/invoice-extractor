#!/usr/bin/env python3
"""
Script pour corriger les imports relatifs dans les fichiers Python.
"""

import os
import re

def fix_file_imports(filepath):
    """Corrige les imports relatifs dans un fichier."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Remplacer les imports relatifs
    # from .module import X -> from module import X
    # from . import module -> import module
    content = re.sub(r'from \.(\w+) import', r'from \1 import', content)
    content = re.sub(r'from \. import (\w+)', r'import \1', content)
    
    # Remplacer les imports spécifiques
    content = content.replace('from .config import Config', 'from config import Config')
    content = content.replace('from .pdf_extractor import PDFExtractor', 'from pdf_extractor import PDFExtractor')
    content = content.replace('from .bedrock_client import BedrockClient', 'from bedrock_client import BedrockClient')
    content = content.replace('from .dynamodb_client import DynamoDBClient', 'from dynamodb_client import DynamoDBClient')
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"Corrigé: {filepath}")

def main():
    """Fonction principale."""
    src_dir = "src_propre"
    
    if not os.path.exists(src_dir):
        print(f"Erreur: Répertoire {src_dir} non trouvé")
        return
    
    # Liste des fichiers à corriger
    files_to_fix = [
        "main.py",
        "bedrock_client.py", 
        "dynamodb_client.py",
        "pdf_extractor.py",
        "pdf_extractor_simple.py"
    ]
    
    for filename in files_to_fix:
        filepath = os.path.join(src_dir, filename)
        if os.path.exists(filepath):
            fix_file_imports(filepath)
        else:
            print(f"Fichier non trouvé: {filepath}")
    
    print("\n✅ Tous les imports ont été corrigés !")

if __name__ == "__main__":
    main()
