#!/usr/bin/env python3
"""
Script de debug pour voir le texte extrait du PDF
"""

import sys
from pathlib import Path

# Ajouter le répertoire src_propre au path
sys.path.insert(0, str(Path(__file__).parent / "src_propre"))

from pdf_extractor_simple import PDFExtractorSimple

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python debug_pdf_text.py <chemin_vers_pdf>")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    extractor = PDFExtractorSimple()
    
    print("=" * 80)
    print(f"TEXTE EXTRAIT DE: {pdf_path}")
    print("=" * 80)
    
    text = extractor.extract_text(pdf_path)
    print(text)
    
    print("\n" + "=" * 80)
    print(f"LONGUEUR: {len(text)} caractères")
    print("=" * 80)
