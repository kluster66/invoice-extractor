# Invoice Extractor avec AWS Bedrock

Outil serverless pour extraire automatiquement les informations structurées des factures PDF en utilisant AWS Bedrock (LLM).

## 🚀 Fonctionnalités

- **Extraction intelligente** : Identification automatique du fournisseur avec logique de correction (évite la confusion client/fournisseur)
- **Multi-modèles** : Support de Claude 3.5, Llama 3.1, Amazon Titan
- **Parsing robuste** : Extraction fiable des données JSON depuis les réponses LLM
- **Stockage structuré** : Données stockées dans DynamoDB avec indexes secondaires
- **Monitoring complet** : Logs CloudWatch et métriques
- **Déploiement automatisé** : Infrastructure as Code avec CloudFormation

## 📋 Architecture

```
S3 (Upload PDF) → Lambda → Bedrock (LLM) → DynamoDB (Stockage)
       ↑               ↓
  Notification    Logs CloudWatch
```

## 🛠️ Prérequis

1. **Compte AWS** avec accès à :
   - AWS Bedrock (modèles activés)
   - Lambda, S3, DynamoDB, CloudFormation
2. **AWS CLI** configuré :

   ```bash
   aws configure
   ```

3. **Python 3.8+** et **pip**

## 🚀 Déploiement rapide

### Option 1 : Déploiement automatique (recommandé)

```bash
# 1. Cloner le projet
git clone <url-du-repo>
cd invoice-extractor

# 2. Installer les dépendances
pip install -r requirements.txt

# 3. Déployer
python deploy.py
```

Le script `deploy.py` gère automatiquement :

- ✅ Validation du template CloudFormation
- ✅ Création du package Lambda
- ✅ Upload du code vers S3
- ✅ Déploiement de la stack CloudFormation
- ✅ Configuration des notifications S3
- ✅ Affichage des URLs de monitoring

### Option 2 : Déploiement manuel

```bash
# 1. Créer le package Lambda
python deploy.py

# 2. Déployer avec CloudFormation
aws cloudformation create-stack \
  --stack-name invoice-extractor \
  --template-body file://cloudformation-template-final.yaml \
  --parameters \
    ParameterKey=EnvironmentName,ParameterValue=prod \
    ParameterKey=BedrockModelId,ParameterValue=meta.llama3-1-70b-instruct-v1:0 \
  --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM \
  --region us-west-2
```

## 📊 Ressources créées

Le déploiement crée automatiquement :

| Service | Nom | Description |
|---------|-----|-------------|
| **S3** | `invoice-extractor-bucket-*` | Bucket pour les factures PDF |
| **Lambda** | `invoice-extractor-prod` | Fonction d'extraction |
| **DynamoDB** | `invoices-extractor` | Table de stockage |
| **CloudWatch** | `/aws/lambda/...` | Logs et monitoring |
| **IAM** | Rôle avec permissions | Accès S3, DynamoDB, Bedrock |

## 🧪 Test

1. **Uploader une facture** dans le bucket S3
2. **Vérifier l'exécution** dans les logs CloudWatch
3. **Consulter les données** dans DynamoDB

```bash
# Tester avec un fichier de test
aws s3 cp test_factures/example.pdf s3://[bucket-name]/

# Vérifier les logs
aws logs tail /aws/lambda/invoice-extractor-prod --follow

# Vérifier les données
aws dynamodb scan --table-name invoices-extractor
```

## 🔧 Configuration

### Variables d'environnement

| Variable | Description | Valeur par défaut |
|----------|-------------|-------------------|
| `DYNAMODB_TABLE_NAME` | Table DynamoDB | `invoices-extractor` |
| `S3_INPUT_BUCKET` | Bucket S3 | Auto-détecté |
| `BEDROCK_MODEL_ID` | Modèle Bedrock | `meta.llama3-1-70b-instruct-v1:0` |
| `LOG_LEVEL` | Niveau de logs | `INFO` |

### Modèles supportés

- `meta.llama3-1-70b-instruct-v1:0` (recommandé, pas d'activation requise)
- `anthropic.claude-3-5-sonnet-*`
- `amazon.titan-text-express-v1`

## 🐛 Dépannage

### Problèmes courants

1. **"Model access not granted"**

   ```bash
   # Activer l'accès dans la console AWS Bedrock
   # Ou utiliser Llama 3.1 (pas d'activation requise)
   ```

2. **Permissions IAM manquantes**

   ```bash
   # Vérifier que le rôle Lambda a les permissions :
   # - dynamodb:DescribeTable
   # - s3:GetObject
   # - bedrock:InvokeModel
   ```

3. **Fichier trop volumineux**

   ```bash
   # Augmenter la mémoire Lambda (max 10240 MB)
   # Augmenter le timeout (max 900 secondes)
   ```

### Logs et monitoring

- **CloudWatch Logs** : `/aws/lambda/invoice-extractor-prod`
- **Métriques Lambda** : Invocations, erreurs, durée
- **Console S3** : Fichiers uploadés
- **Console DynamoDB** : Données extraites

## 📁 Structure du projet

```
invoice-extractor/
├── src_propre/              # Code source
│   ├── main.py             # Handler Lambda
│   ├── bedrock_client.py   # Client multi-modèles
│   ├── dynamodb_client.py  # Client DynamoDB
│   ├── pdf_extractor_simple.py # Extraction PDF (recommandé)
│   └── config.py           # Configuration
├── cloudformation-template-final.yaml  # Template IaC
├── deploy.py               # Script de déploiement
├── cleanup.py              # Script de nettoyage AWS
├── requirements.txt        # Dépendances
├── .gitignore             # Fichiers à ignorer
└── README.md              # Documentation
```

## 🔄 Mise à jour

```bash
# Mettre à jour le code Lambda
python deploy.py

# Ou mettre à jour manuellement
aws lambda update-function-code \
  --function-name invoice-extractor-prod \
  --zip-file fileb://invoice-extractor-lambda.zip \
  --region us-west-2
```

## 🧹 Nettoyage

```bash
# Supprimer la stack CloudFormation
aws cloudformation delete-stack --stack-name invoice-extractor --region us-west-2

# Ou utiliser le script de nettoyage
python cleanup.py
```

## 📄 Licence

MIT License - voir [LICENSE](LICENSE) pour plus de détails.

## 🤝 Contribution

Les contributions sont les bienvenues ! Voir [CONTRIBUTING.md](CONTRIBUTING.md) pour les guidelines.

## 📞 Support

Pour les problèmes :

1. Vérifier les logs CloudWatch
2. Tester avec différents modèles Bedrock
3. Ouvrir une issue sur GitHub

---

**Dernière mise à jour** : Janvier 2026  
**Version** : 2.1.0  
**Statut** : Production Ready  
**Modèle par défaut** : Llama 3.1 70B  
**Runtime Lambda** : Python 3.10  
**Région AWS** : us-west-2
