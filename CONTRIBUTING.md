# Guide de Contribution

Merci de votre intérêt pour contribuer à Invoice Extractor ! Ce guide explique comment contribuer efficacement.

## 📋 Table des matières

1. [Code de conduite](#-code-de-conduite)
2. [Comment contribuer](#-comment-contribuer)
3. [Structure du projet](#-structure-du-projet)
4. [Développement local](#-développement-local)
5. [Tests](#-tests)
6. [Pull Requests](#-pull-requests)
7. [Style de code](#-style-de-code)
8. [Documentation](#-documentation)

## 🤝 Code de conduite

Ce projet et tous les participants sont régis par notre [Code de Conduite](CODE_OF_CONDUCT.md). En participant, vous vous engagez à respecter ce code.

## 🚀 Comment contribuer

### 1. Signaler un bug
- Vérifier si le bug n'a pas déjà été signalé
- Utiliser le template d'issue "Bug Report"
- Inclure les étapes pour reproduire
- Ajouter les logs et messages d'erreur
- Spécifier votre environnement (OS, Python, AWS)

### 2. Proposer une fonctionnalité
- Vérifier si la fonctionnalité n'a pas déjà été proposée
- Utiliser le template d'issue "Feature Request"
- Expliquer le cas d'utilisation
- Décrire l'implémentation envisagée
- Discuter des impacts sur l'existant

### 3. Corriger un bug
- Assigner l'issue à vous-même
- Créer une branche dédiée
- Implémenter la correction
- Ajouter des tests
- Soumettre une Pull Request

### 4. Implémenter une fonctionnalité
- Discuter de l'implémentation dans l'issue
- Créer une branche dédiée
- Implémenter par petites étapes
- Ajouter des tests complets
- Mettre à jour la documentation
- Soumettre une Pull Request

## 📁 Structure du projet

```
invoice-extractor/
├── src_propre/              # Code source propre (à versionner)
│   ├── main.py             # Handler Lambda principal
│   ├── bedrock_client.py   # Client multi-modèles AWS Bedrock
│   ├── dynamodb_client.py  # Client DynamoDB avec indexes
│   ├── pdf_extractor.py    # Extraction PDF (PyPDF2 + pdfplumber)
│   └── config.py           # Configuration intelligente AWS
├── config/                 # Configuration
│   ├── config.py          # (copié dans src_propre/)
│   └── env.example        # Template variables d'environnement
├── infrastructure/         # Infrastructure as Code
│   └── cdk-stack.py       # Stack AWS CDK
├── tests/                 # Tests unitaires et d'intégration
├── docs/                  # Documentation supplémentaire
├── scripts/               # Scripts utilitaires
├── .gitignore            # Fichiers à ignorer
├── cloudformation-template.yaml  # Template CloudFormation
├── template.yaml         # Template AWS SAM
├── requirements.txt      # Dépendances Python
└── requirements-lambda.txt # Dépendances pour Lambda
```

## 💻 Développement local

### Configuration initiale
```bash
# 1. Cloner le dépôt
git clone https://github.com/votre-repo/invoice-extractor.git
cd invoice-extractor

# 2. Créer un environnement virtuel
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac

# 3. Installer les dépendances
pip install -r requirements.txt

# 4. Configurer AWS CLI
aws configure
```

### Structure des branches
- `main` : Branche de production
- `develop` : Branche de développement
- `feature/*` : Nouvelles fonctionnalités
- `bugfix/*` : Corrections de bugs
- `release/*` : Préparation de release

### Workflow Git
```bash
# 1. Mettre à jour la branche principale
git checkout main
git pull origin main

# 2. Créer une branche de fonctionnalité
git checkout -b feature/nouvelle-fonctionnalite

# 3. Développer et commiter
git add .
git commit -m "feat: ajout nouvelle fonctionnalité"

# 4. Pousser la branche
git push origin feature/nouvelle-fonctionnalite

# 5. Créer une Pull Request
```

## 🧪 Tests

### Tests unitaires
```bash
# Exécuter tous les tests
pytest tests/ -v

# Exécuter un test spécifique
pytest tests/test_pdf_extractor.py -v

# Exécuter avec couverture
pytest tests/ --cov=src_propre --cov-report=html
```

### Tests d'intégration
```bash
# Tester l'extraction complète
python test_real_invoice_simple.py

# Tester différents modèles Bedrock
python test_models_simple.py

# Lister les modèles disponibles
python list_available_models.py
```

### Tests AWS
```bash
# Tester la configuration AWS
python -c "from config.config import Config; print(Config.get_region())"

# Tester l'accès Bedrock
python -c "from src_propre.bedrock_client import BedrockClient; client = BedrockClient(); print(client.list_available_models())"
```

## 🔀 Pull Requests

### Processus de review
1. **Créer la PR** avec une description claire
2. **Vérifier les tests** : Tous doivent passer
3. **Vérifier le style de code** : Respecter les conventions
4. **Mettre à jour la documentation** : README, docstrings, etc.
5. **Attendre les reviews** : Au moins 1 approbation requise
6. **Résoudre les commentaires** : Adresser tous les feedbacks
7. **Merge** : Après approbation

### Template de PR
```markdown
## Description
[Description claire des changements]

## Type de changement
- [ ] Correction de bug
- [ ] Nouvelle fonctionnalité
- [ ] Changement cassant (breaking change)
- [ ] Documentation
- [ ] Refactoring

## Checklist
- [ ] Mon code suit le style de code du projet
- [ ] J'ai ajouté des tests pour mes changements
- [ ] Tous les tests passent localement
- [ ] J'ai mis à jour la documentation
- [ ] J'ai ajouté des exemples si nécessaire

## Tests effectués
- [ ] Testé localement avec Python 3.8+
- [ ] Testé avec différents modèles Bedrock
- [ ] Testé avec des factures réelles

## Screenshots (si applicable)
[Ajouter des captures d'écran si pertinent]

## Informations supplémentaires
[Ajouter toute information supplémentaire]
```

## 🎨 Style de code

### Python
- **PEP 8** : Suivre les conventions PEP 8
- **Docstrings** : Utiliser le format Google
- **Types** : Ajouter des type hints
- **Imports** : Organiser par groupe (standard, tiers, local)

### Exemple de code
```python
def extract_invoice_data(pdf_path: str, model_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Extrait les données d'une facture PDF en utilisant AWS Bedrock.
    
    Args:
        pdf_path: Chemin vers le fichier PDF
        model_id: ID du modèle Bedrock à utiliser (optionnel)
        
    Returns:
        Dictionnaire contenant les données extraites
        
    Raises:
        FileNotFoundError: Si le fichier PDF n'existe pas
        ExtractionError: Si l'extraction échoue
    """
    # Implémentation
    pass
```

### Commits
- **Format** : `type: description`
- **Types** : `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`
- **Exemples** :
  - `feat: ajout support multi-modèles Bedrock`
  - `fix: correction parsing JSON avec texte supplémentaire`
  - `docs: mise à jour guide de déploiement`

## 📚 Documentation

### Types de documentation
1. **Docstrings** : Documentation des fonctions et classes
2. **README.md** : Documentation principale
3. **CONFIGURATION.md** : Guide de configuration
4. **DEPLOY.md** : Guide de déploiement
5. **CHANGELOG.md** : Historique des changements
6. **CONTRIBUTING.md** : Guide de contribution

### Mettre à jour la documentation
```bash
# 1. Mettre à jour les docstrings
# 2. Mettre à jour README.md si nécessaire
# 3. Mettre à jour CHANGELOG.md
# 4. Vérifier que tous les liens fonctionnent
# 5. Tester les exemples de code
```

### Ajouter des exemples
```markdown
```python
# Exemple d'utilisation
from src_propre.main import extract_invoice

result = extract_invoice("facture.pdf")
print(f"Fournisseur: {result['fournisseur']}")
```
```

## 🐛 Dépannage

### Problèmes courants

#### "AWS credentials not found"
```bash
# Vérifier la configuration AWS CLI
aws configure get region
aws sts get-caller-identity
```

#### "Model access not granted"
1. AWS Console → Bedrock → Model access
2. Demander l'accès au modèle
3. Attendre l'approbation

#### "SAM build fails with Python 3.14"
```bash
# Utiliser CloudFormation direct
python deploy_with_cloudformation.py

# Ou utiliser Python 3.12
python3.12 -m venv venv
venv\Scripts\activate
pip install aws-sam-cli
```

### Débogage
```python
# Activer les logs détaillés
import logging
logging.basicConfig(level=logging.DEBUG)

# Utiliser pdb pour le débogage
import pdb; pdb.set_trace()
```

## 📞 Support

### Ressources
- **Documentation** : [README.md](README.md)
- **Issues** : https://github.com/votre-repo/issues
- **Discussions** : https://github.com/votre-repo/discussions

### Obtenir de l'aide
1. **Chercher dans les issues** existantes
2. **Consulter la documentation**
3. **Ouvrir une issue** si nécessaire
4. **Participer aux discussions**

## 🏆 Reconnaissance

Les contributeurs sont reconnus dans :
- **CHANGELOG.md** : Pour les contributions significatives
- **README.md** : Pour les contributions majeures
- **Releases GitHub** : Pour chaque version

---

**Merci pour votre contribution !** 🎉

Vos efforts aident à améliorer Invoice Extractor pour toute la communauté.

Pour toute question, n'hésitez pas à ouvrir une issue ou à participer aux discussions.
