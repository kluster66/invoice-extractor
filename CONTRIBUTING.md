# Guide de Contribution

## Structure du projet

```
invoice-extractor/
├── src_propre/                         # Code déployé sur Lambda
│   ├── main.py                        # Handler Lambda + prompt d'extraction
│   ├── bedrock_client.py              # Client AWS Bedrock (multi-modèles)
│   ├── dynamodb_client.py             # Client DynamoDB
│   ├── pdf_extractor_simple.py        # Extraction texte PDF (PyPDF2)
│   └── config.py                      # Configuration via variables d'env
├── ui_invoices.py                     # Interface graphique NiceGui
├── view_invoices.py                   # Outil CLI
├── deploy.py                          # Script de déploiement AWS
├── cleanup.py                         # Script de nettoyage AWS
├── cloudformation-template-final.yaml # Infrastructure as Code
├── requirements.txt                   # Dépendances locales (nicegui, openpyxl inclus)
├── requirements-lambda.txt            # Dépendances Lambda
├── env.example                        # Template de configuration
└── .gitignore
```

## Développement local

```powershell
# 1. Cloner
git clone https://github.com/votre-repo/invoice-extractor.git
cd invoice-extractor

# 2. Environnement virtuel
uv venv .venv
.\.venv\Scripts\Activate.ps1
uv pip install -r requirements.txt

# 3. Configuration
copy env.example .env
# Éditer .env avec vos valeurs

# 4. Configurer AWS CLI
aws configure
```

## Branches

- `main` : production
- `feature/*` : nouvelles fonctionnalités
- `bugfix/*` : corrections de bugs

## Workflow Git

```powershell
git checkout main
git pull origin main
git checkout -b feature/ma-fonctionnalite
# ... développer ...
git add fichier1.py fichier2.py
git commit -m "feat: description de la fonctionnalité"
git push origin feature/ma-fonctionnalite
# Créer une Pull Request sur GitHub
```

## Convention de commits

Format : `type: description`

Types : `feat`, `fix`, `docs`, `refactor`, `test`, `chore`

Exemples :
- `feat: ajout champ devise dans l'extraction`
- `fix: correction trigger S3 pour extension .PDF`
- `docs: mise à jour README v3.0.0`

## Tests

```powershell
# Tests unitaires
pytest tests/ -v

# Avec couverture
pytest tests/ --cov=src_propre --cov-report=html
```

## Ajouter un champ extrait

1. Modifier le prompt dans `src_propre/main.py` (`_create_prompt`) — ajouter le champ dans le JSON exemple
2. Ajouter l'alias dans `_normalize_field_names` de `bedrock_client.py`
3. Ajouter le champ dans `extracted_fields` de `dynamodb_client.py`
4. Ajouter la colonne dans `COLUMNS` de `ui_invoices.py` et `view_invoices.py`
5. Redéployer avec `python deploy.py`
6. Retraiter les factures existantes si nécessaire

## Ajouter un client connu (nouvelle entité du groupe)

Modifier `KNOWN_CLIENTS` dans `src_propre/main.py` :

```python
KNOWN_CLIENTS = [
    "BOARDRIDERS",
    "NA PALI",
    # Ajouter la nouvelle entité ici (en majuscules)
]
```

La liste est injectée dans le prompt Bedrock et utilisée pour la correction automatique client/fournisseur. Redéployer après modification.

## Style de code

- PEP 8
- Type hints sur les fonctions publiques
- Docstrings format Google
- Commentaires en français

## Pull Requests

Checklist avant de soumettre :
- [ ] Tests unitaires passent
- [ ] Pas de secrets dans le code (Account ID, clés AWS)
- [ ] `.env` non commité
- [ ] CHANGELOG.md mis à jour
- [ ] Documentation mise à jour si nécessaire

## Sécurité

- Ne jamais commiter de fichier `.env`
- Ne jamais hardcoder d'Account ID AWS, de clé d'accès, ou d'ARN avec compte spécifique
- Les valeurs spécifiques à l'infrastructure passent par `os.getenv()` avec fallback générique
- Voir `.gitignore` pour la liste complète des fichiers exclus
