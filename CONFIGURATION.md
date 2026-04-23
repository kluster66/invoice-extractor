# Configuration - Invoice Extractor

## Fichier .env

Créer un fichier `.env` à la racine du projet (non versionné) en vous basant sur `env.example` :

```env
# AWS
AWS_REGION=us-west-2

# DynamoDB
DYNAMODB_TABLE_NAME=invoices-extractor

# S3 — remplacer {account-id} par votre Account ID AWS
S3_INPUT_BUCKET=invoice-input-{account-id}-us-west-2

# Bedrock
BEDROCK_MODEL_ID=meta.llama3-1-70b-instruct-v1:0
BEDROCK_MAX_TOKENS=1000
BEDROCK_TEMPERATURE=0.1
```

Retrouver votre Account ID :
```powershell
aws sts get-caller-identity --query Account --output text
```

---

## Variables d'environnement

| Variable | Description | Valeur par défaut |
|----------|-------------|-------------------|
| `AWS_REGION` | Région AWS | `us-west-2` |
| `DYNAMODB_TABLE_NAME` | Table DynamoDB | `invoices-extractor` |
| `S3_INPUT_BUCKET` | Bucket S3 d'entrée | *(requis)* |
| `BEDROCK_MODEL_ID` | Modèle Bedrock | `meta.llama3-1-70b-instruct-v1:0` |
| `BEDROCK_MAX_TOKENS` | Tokens max en réponse | `1000` |
| `BEDROCK_TEMPERATURE` | Température du modèle | `0.1` |
| `LOG_LEVEL` | Niveau de logs | `INFO` |
| `MAX_PDF_SIZE_MB` | Taille max PDF (MB) | `50` |
| `EXTRACTION_TIMEOUT` | Timeout extraction (s) | `300` |

---

## Modèles Bedrock

| Clé | ID complet | Activation |
|-----|-----------|------------|
| `llama-3-70b` | `meta.llama3-70b-instruct-v1:0` | Non requise |
| `llama-3-1-70b` | `meta.llama3-1-70b-instruct-v1:0` | Non requise |
| `claude-3-sonnet` | `anthropic.claude-3-sonnet-20240229-v1:0` | Requise |
| `claude-3-haiku` | `anthropic.claude-3-haiku-20240307-v1:0` | Requise |
| `claude-3-5-sonnet` | `anthropic.claude-3-5-sonnet-20241022-v2:0` | Requise |
| `titan-text-express` | `amazon.titan-text-express-v1` | Requise |

Changer de modèle via variable d'environnement Lambda :
```powershell
aws lambda update-function-configuration `
  --function-name invoice-extractor-prod `
  --environment Variables={BEDROCK_MODEL_ID=anthropic.claude-3-5-sonnet-20241022-v2:0} `
  --region us-west-2
```

---

## Données extraites (schéma DynamoDB)

```json
{
  "invoice_id":      "uuid-v4 (clé primaire)",
  "nom_fichier":     "Facture_2025.pdf",
  "fournisseur":     "ORANGE",
  "numero_facture":  "FACT-2025-001",
  "date_facture":    "2025-12-01",
  "montant_ht":      1250.00,
  "devise":          "EUR",
  "chrono":          "12345",
  "couverture":      "01/12/2025 au 31/12/2025",
  "extraction_date": "2026-04-23T07:00:00+00:00",
  "pdf_path":        "/tmp/Facture_2025.pdf",
  "raw_data":        "{...JSON brut retourné par le LLM...}"
}
```

### Index secondaires

| Index | Champ | Usage |
|-------|-------|-------|
| `numero_facture-index` | `numero_facture` | Recherche par numéro |
| `date_facture-index` | `date_facture` | Recherche par date |
| `fournisseur-index` | `fournisseur` | Recherche par fournisseur |

---

## Trigger S3

Le bucket S3 déclenche la Lambda sur tout upload de fichier `.pdf` ou `.PDF` :

```yaml
# cloudformation-template-final.yaml
LambdaConfigurations:
  - Event: s3:ObjectCreated:*
    Filter:
      S3Key:
        Rules:
          - Name: suffix
            Value: .pdf
  - Event: s3:ObjectCreated:*
    Filter:
      S3Key:
        Rules:
          - Name: suffix
            Value: .PDF
```

---

## Lambda

| Paramètre | Valeur |
|-----------|--------|
| Runtime | Python 3.11+ |
| Handler | `main.lambda_handler` |
| Mémoire | 1024 MB |
| Timeout | 300 s |
| Architecture | x86_64 |

### Permissions IAM du rôle Lambda

- `s3:GetObject` sur le bucket d'entrée
- `dynamodb:PutItem`, `GetItem`, `Scan`, `Query`, `DeleteItem`, `DescribeTable` sur `invoices-extractor`
- `bedrock:InvokeModel`
- `logs:CreateLogGroup`, `CreateLogStream`, `PutLogEvents`

---

## Ajouter un nouveau champ extrait

1. Modifier le prompt dans `src_propre/main.py` (méthode `_create_prompt`) — ajouter le champ dans les sections "Champs à extraire" et "Champs requis"
2. Ajouter la colonne dans `COLUMNS` de `ui_invoices.py` et `view_invoices.py`
3. Redéployer : `python deploy.py`
4. Retraiter les factures existantes (supprimer depuis l'UI, re-uploader les PDF)

---

## Monitoring

- **Logs** : CloudWatch `/aws/lambda/invoice-extractor-prod` (rétention 30 jours)
- **Console Lambda** : `https://us-west-2.console.aws.amazon.com/lambda/home?region=us-west-2#/functions/invoice-extractor-prod`
- **Console DynamoDB** : `https://us-west-2.console.aws.amazon.com/dynamodbv2/home?region=us-west-2#table?name=invoices-extractor`
