#!/usr/bin/env python3
"""
Script de déploiement simplifié avec CDK
"""

import os
import sys
import subprocess
import json
from pathlib import Path

def check_aws_cli():
    """Vérifier si AWS CLI est installé et configuré"""
    try:
        result = subprocess.run(
            ["aws", "sts", "get-caller-identity"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            print("✅ AWS CLI configuré")
            return True
        else:
            print("❌ AWS CLI non configuré ou erreur d'authentification")
            print(f"Erreur: {result.stderr}")
            return False
    except FileNotFoundError:
        print("❌ AWS CLI non installé")
        print("Installez AWS CLI: https://aws.amazon.com/cli/")
        return False

def check_cdk_installed():
    """Vérifier si CDK est installé"""
    try:
        # Essayer avec npx (Node.js)
        result = subprocess.run(
            ["npx", "cdk", "--version"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            print(f"✅ CDK installé (version: {result.stdout.strip()})")
            return True
    except FileNotFoundError:
        pass
    
    try:
        # Essayer avec npm (installation globale)
        result = subprocess.run(
            ["cdk", "--version"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            print(f"✅ CDK installé (version: {result.stdout.strip()})")
            return True
    except FileNotFoundError:
        pass
    
    print("❌ CDK non installé")
    print("Installez CDK avec: npm install -g aws-cdk")
    return False

def install_cdk():
    """Installer CDK avec npm"""
    print("📦 Installation de CDK...")
    try:
        result = subprocess.run(
            ["npm", "install", "-g", "aws-cdk"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            print("✅ CDK installé avec succès")
            return True
        else:
            print(f"❌ Erreur lors de l'installation: {result.stderr}")
            return False
    except FileNotFoundError:
        print("❌ npm non installé")
        print("Installez Node.js: https://nodejs.org/")
        return False

def bootstrap_cdk():
    """Bootstrap CDK (première fois seulement)"""
    print("🚀 Bootstrap CDK...")
    try:
        result = subprocess.run(
            ["cdk", "bootstrap"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            print("✅ CDK bootstrap réussi")
            return True
        else:
            print(f"⚠️  Bootstrap échoué ou déjà fait: {result.stderr}")
            return True  # Peut être déjà bootstrapé
    except FileNotFoundError:
        print("❌ CDK non trouvé")
        return False

def synth_cdk():
    """Générer le template CloudFormation"""
    print("🔧 Génération du template CloudFormation...")
    try:
        result = subprocess.run(
            ["cdk", "synth"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            print("✅ Template généré avec succès")
            # Sauvegarder le template
            template_path = Path("cdk.out/InvoiceExtractorStack.template.json")
            if template_path.exists():
                print(f"📄 Template sauvegardé: {template_path}")
            return True
        else:
            print(f"❌ Erreur lors de la génération: {result.stderr}")
            return False
    except FileNotFoundError:
        print("❌ CDK non trouvé")
        return False

def diff_cdk():
    """Voir les changements"""
    print("📊 Vérification des changements...")
    try:
        result = subprocess.run(
            ["cdk", "diff"],
            capture_output=True,
            text=True
        )
        print(result.stdout)
        if result.returncode == 0:
            return True
        else:
            return False
    except FileNotFoundError:
        print("❌ CDK non trouvé")
        return False

def deploy_cdk():
    """Déployer la stack"""
    print("🚀 Déploiement de la stack...")
    try:
        result = subprocess.run(
            ["cdk", "deploy", "--require-approval", "never"],
            capture_output=True,
            text=True
        )
        print(result.stdout)
        if result.returncode == 0:
            print("✅ Déploiement réussi !")
            return True
        else:
            print(f"❌ Erreur lors du déploiement: {result.stderr}")
            return False
    except FileNotFoundError:
        print("❌ CDK non trouvé")
        return False

def destroy_cdk():
    """Supprimer la stack"""
    print("🗑️  Suppression de la stack...")
    try:
        result = subprocess.run(
            ["cdk", "destroy", "--force"],
            capture_output=True,
            text=True
        )
        print(result.stdout)
        if result.returncode == 0:
            print("✅ Stack supprimée")
            return True
        else:
            print(f"❌ Erreur lors de la suppression: {result.stderr}")
            return False
    except FileNotFoundError:
        print("❌ CDK non trouvé")
        return False

def main():
    """Fonction principale"""
    print("=" * 60)
    print("DÉPLOIEMENT INVOICE EXTRACTOR AVEC AWS CDK")
    print("=" * 60)
    
    # Vérifier les prérequis
    if not check_aws_cli():
        sys.exit(1)
    
    if not check_cdk_installed():
        print("\nVoulez-vous installer CDK maintenant ? (o/n)")
        choice = input().strip().lower()
        if choice == 'o':
            if not install_cdk():
                sys.exit(1)
        else:
            print("Installation de CDK requise pour continuer")
            sys.exit(1)
    
    # Menu principal
    while True:
        print("\n" + "=" * 60)
        print("MENU PRINCIPAL")
        print("=" * 60)
        print("1. 🔧 Générer le template CloudFormation (synth)")
        print("2. 📊 Voir les changements (diff)")
        print("3. 🚀 Déployer la stack (deploy)")
        print("4. 🗑️  Supprimer la stack (destroy)")
        print("5. 🚀 Bootstrap CDK (première fois)")
        print("6. 📋 Vérifier la configuration")
        print("0. ❌ Quitter")
        print("=" * 60)
        
        choice = input("\nChoisissez une option (0-6): ").strip()
        
        if choice == "1":
            synth_cdk()
        elif choice == "2":
            diff_cdk()
        elif choice == "3":
            print("\n⚠️  ATTENTION: Vous allez déployer des ressources AWS facturables")
            confirm = input("Confirmez-vous le déploiement ? (oui/non): ").strip().lower()
            if confirm == "oui":
                deploy_cdk()
        elif choice == "4":
            print("\n⚠️  ATTENTION: Vous allez supprimer toutes les ressources AWS")
            confirm = input("Confirmez-vous la suppression ? (oui/non): ").strip().lower()
            if confirm == "oui":
                destroy_cdk()
        elif choice == "5":
            bootstrap_cdk()
        elif choice == "6":
            check_aws_cli()
            check_cdk_installed()
        elif choice == "0":
            print("Au revoir ! 👋")
            break
        else:
            print("Option invalide")

if __name__ == "__main__":
    main()
