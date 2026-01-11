#!/usr/bin/env python3
"""
Script d'installation des dépendances
"""

import subprocess
import sys
import os
from pathlib import Path

def install_requirements():
    """Installer les dépendances depuis requirements.txt"""
    print("📦 Installation des dépendances...")
    
    requirements_file = Path(__file__).parent / "requirements.txt"
    
    if not requirements_file.exists():
        print(f"❌ Fichier {requirements_file} non trouvé")
        return False
    
    try:
        # Installer avec pip
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", str(requirements_file)],
            capture_output=True,
            text=True,
            check=True
        )
        
        print("✅ Dépendances installées avec succès")
        print(result.stdout)
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Erreur lors de l'installation: {e}")
        print(f"Stderr: {e.stderr}")
        return False

def create_virtual_env():
    """Créer un environnement virtuel (optionnel)"""
    print("\n🐍 Création d'un environnement virtuel...")
    
    venv_dir = Path(__file__).parent / "venv"
    
    try:
        # Créer l'environnement virtuel
        subprocess.run(
            [sys.executable, "-m", "venv", str(venv_dir)],
            check=True
        )
        
        print(f"✅ Environnement virtuel créé dans {venv_dir}")
        
        # Déterminer le chemin de pip selon l'OS
        if os.name == 'nt':  # Windows
            pip_path = venv_dir / "Scripts" / "pip.exe"
        else:  # Linux/Mac
            pip_path = venv_dir / "bin" / "pip"
        
        # Installer les dépendances dans le venv
        subprocess.run(
            [str(pip_path), "install", "-r", "requirements.txt"],
            check=True
        )
        
        print("✅ Dépendances installées dans l'environnement virtuel")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Erreur: {e}")
        return False

def main():
    """Fonction principale"""
    print("=" * 60)
    print("🔧 INSTALLATION DE L'EXTRACTEUR DE FACTURES")
    print("=" * 60)
    
    print("\nOptions d'installation:")
    print("1. Installer globalement (recommandé pour Lambda)")
    print("2. Créer un environnement virtuel")
    print("3. Quitter")
    
    choice = input("\nVotre choix (1-3): ").strip()
    
    if choice == "1":
        success = install_requirements()
    elif choice == "2":
        success = create_virtual_env()
    elif choice == "3":
        print("👋 Au revoir!")
        return
    else:
        print("❌ Choix invalide")
        return
    
    if success:
        print("\n" + "=" * 60)
        print("🎉 INSTALLATION RÉUSSIE !")
        print("=" * 60)
        print("\nProchaines étapes:")
        print("1. Tester l'installation: python test_local.py")
        print("2. Configurer AWS: cp config/env.example .env")
        print("3. Éditer .env avec vos credentials AWS")
    else:
        print("\n❌ L'installation a échoué. Vérifiez les erreurs ci-dessus.")

if __name__ == "__main__":
    main()
