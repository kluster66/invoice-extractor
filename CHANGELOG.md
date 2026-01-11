# Changelog

Tous les changements notables de ce projet seront documentés dans ce fichier.

Le format est basé sur [Keep a Changelog](https://keepachangelog.com/fr/1.0.0/),
et ce projet adhère au [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.1] - 2026-01-11

### Ajouté
- **Fichier `.gitignore` complet** : Pour pousser sur GitHub en sécurité
- **Script de déploiement CloudFormation** : `deploy_with_cloudformation.py`
- **Support CloudFormation direct** : Alternative à SAM avec Python 3.14
- **Structure de projet propre** : Code source dans `src_propre/`, dépendances exclues
- **Documentation mise à jour** : Problème SAM avec Python 3.14 documenté
- **Script CDK simplifié** : `deploy_with_cdk_simple.py`

### Modifié
- **Organisation du code source** : Séparation code/dépendances pour GitHub
- **Mise à jour README.md** : Instructions CloudFormation ajoutées
- **Mise à jour DEPLOY.md** : Guide CloudFormation détaillé
- **Mise à jour CONFIGURATION.md** : Structure du projet documentée
- **Version des guides** : 2.0.1 pour toutes les documentations

### Corrections
- **Problème SAM Python 3.14** : Documentation des solutions de contournement
- **Structure pour GitHub** : `.gitignore` complet pour éviter les secrets
- **Encodage des scripts** : Versions sans émojis pour Windows

### Notes
- **GitHub Ready** : Projet prêt à être poussé sur GitHub
- **Compatibilité Python 3.14** : Solution CloudFormation disponible
- **Options de déploiement** : CloudFormation, SAM, CDK, Manuel

## [2.0.0] - 2026-01-11

### Ajouté
- **Support multi-modèles Bedrock** : Claude 3, Llama 3, Amazon Titan, etc.
- **Configuration AWS intelligente** : Détection automatique région/credentials depuis AWS CLI
- **Parsing robuste** : Extraction JSON même avec texte supplémentaire
- **Normalisation des champs** : Support français/anglais automatique
- **Scripts de test améliorés** : `test_models_simple.py`, `list_available_models.py`
- **Documentation mise à jour** : README, CONFIGURATION.md, DEPLOY.md
- **Configuration interactive** : `configure_model.py` pour choisir facilement le modèle

### Modifié
- **Client Bedrock refactorisé** : Support des formats d'API différents par modèle
- **Configuration refaite** : Priorité AWS CLI → Variables d'environnement → Valeurs par défaut
- **Prompt d'extraction optimisé** : Meilleure précision pour différents modèles
- **Structure des données** : Normalisation automatique des noms de champs

### Supprimé
- **Configuration hardcodée** : Plus de région/credentials en dur
- **Dépendances obsolètes** : Mise à jour des versions

### Notes de migration
- **Ancienne configuration** : Variables d'environnement requises
- **Nouvelle configuration** : AWS CLI suffit, .env optionnel
- **Modèle par défaut** : Llama 3.1 70B au lieu de Claude 3 Sonnet (pas d'activation requise)

## [1.0.0] - 2026-01-10

### Ajouté
- **Fonctionnalité de base** : Extraction PDF avec PyPDF2 + pdfplumber
- **Intégration AWS Bedrock** : Claude 3 Sonnet pour l'extraction
- **Stockage DynamoDB** : Table avec indexes optimisés
- **Déclenchement S3** : Architecture serverless complète
- **Déploiement multi-méthodes** : SAM, CDK, manuel
- **Tests unitaires** : Couverture des composants principaux
- **Documentation complète** : README, guides de déploiement

### Fonctionnalités
- Extraction des champs de facture : fournisseur, montant, numéro, date, etc.
- Validation des données extraites
- Gestion des erreurs et retry
- Logging CloudWatch
- Monitoring de base

## Notes de version

### Version 2.0.1
- **GitHub Ready** : Structure propre avec `.gitignore` complet
- **Solution SAM Python 3.14** : CloudFormation direct comme alternative
- **Documentation complète** : Tous les guides mis à jour

### Version 2.0.0
- **Breaking change** : Configuration AWS intelligente (plus de hardcoding)
- **Amélioration majeure** : Support de 129 modèles Bedrock
- **Compatibilité** : Python 3.8+, AWS us-west-2 recommandée

### Version 1.0.0
- **Version initiale** : Fonctionnalités de base opérationnelles
- **Production ready** : Architecture AWS complète
- **Documentation** : Guides complets d'installation et déploiement

## Prochaines versions

### [2.1.0] - Planifié
- Support des images dans les PDF
- Extraction multi-pages améliorée
- Cache des résultats pour réduire les coûts
- Dashboard de monitoring

### [3.0.0] - À venir
- Support multi-langues (anglais, espagnol, allemand)
- Extraction de tableaux complexes
- Intégration avec d'autres LLM providers
- Plugin system pour extensions

---

## Convention de version

- **MAJOR** : Changements incompatibles avec l'API
- **MINOR** : Nouvelles fonctionnalités rétrocompatibles  
- **PATCH** : Corrections de bugs rétrocompatibles

## Politique de support

- **Version actuelle** : 2.0.1 (support complet)
- **Version précédente** : 2.0.0 (support sécurité seulement)
- **Versions plus anciennes** : Non supportées

## Liens

- [Documentation](README.md)
- [Guide de configuration](CONFIGURATION.md)
- [Guide de déploiement](DEPLOY.md)
- [Issues GitHub](https://github.com/votre-repo/issues)
- [Releases](https://github.com/votre-repo/releases)
