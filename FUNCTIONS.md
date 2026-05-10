# Référence des fonctions — Invoice Extractor

## lambda_handler()

### In
| Paramètre | Type | Description |
|-----------|------|-------------|
| `event` | `dict` | Événement AWS Lambda (contient l'enregistrement S3 déclencheur) |
| `context` | `Any` | Contexte d'exécution Lambda (non utilisé directement) |

### Transform
Point d'entrée principal pour AWS Lambda. Lit la variable d'environnement `AWS_REGION`, instancie `InvoiceExtractorSimple`, puis délègue le traitement à `process_s3_event`.

### Out
Dictionnaire HTTP-like avec `statusCode` (200 ou 500) et `body` JSON décrivant le résultat ou l'erreur.

---

## InvoiceExtractorSimple.__init__()

### In
| Paramètre | Type | Description |
|-----------|------|-------------|
| `region` | `str` (optionnel) | Région AWS ; si absent, utilise `Config.AWS_REGION` |

### Transform
Initialise les trois sous-clients : `PDFExtractorSimple`, `BedrockClient` et `DynamoDBClient`, tous pointant vers la même région AWS.

### Out
Aucune valeur de retour. Prépare l'instance pour les appels suivants.

---

## InvoiceExtractorSimple.extract_from_pdf()

### In
| Paramètre | Type | Description |
|-----------|------|-------------|
| `pdf_path` | `str` | Chemin local vers le fichier PDF |
| `filename` | `str` | Nom original du fichier (utilisé dans le prompt et les métadonnées) |

### Transform
Orchestre le pipeline complet en 5 étapes :
1. Extrait le texte brut via `PDFExtractorSimple.extract_text`.
2. Construit le prompt d'extraction via `_create_prompt`.
3. Appelle `BedrockClient.extract_invoice_data` pour obtenir les données structurées.
4. Corrige éventuellement le fournisseur via `_fix_supplier_if_needed`.
5. Ajoute les métadonnées (`extraction_date`, `pdf_path`, `nom_fichier`).

### Out
Dictionnaire contenant les champs de la facture (`fournisseur`, `montant_ht`, `devise`, `numero_facture`, `date_facture`, `chrono`, `couverture`, `nom_fichier`) enrichi des métadonnées d'extraction.

---

## InvoiceExtractorSimple._fix_supplier_if_needed()

### In
| Paramètre | Type | Description |
|-----------|------|-------------|
| `data` | `dict` | Données extraites par le LLM |
| `filename` | `str` | Nom du fichier source |

### Transform
Vérifie si le champ `fournisseur` renvoyé par le LLM correspond à un client connu (liste `KNOWN_CLIENTS`). Si c'est le cas, tente de récupérer le vrai fournisseur depuis le nom du fichier via `_extract_supplier_from_filename`. Met `fournisseur` à `None` si l'identification échoue.

### Out
Dictionnaire `data` modifié en place (champ `fournisseur` corrigé ou mis à `None`).

---

## InvoiceExtractorSimple._extract_supplier_from_filename()

### In
| Paramètre | Type | Description |
|-----------|------|-------------|
| `filename` | `str` | Nom du fichier PDF (avec extension) |

### Transform
Opère par élimination sur le nom de fichier (sans extension) :
1. Met en majuscules.
2. Supprime les séquences numériques (dates, chronos…).
3. Supprime les noms de clients connus.
4. Filtre les tokens trop courts et les mots génériques (`_FILENAME_NOISE_WORDS`).
5. Retourne le premier token significatif, mis en forme titre (`capitalize`).

### Out
Chaîne de caractères avec le nom probable du fournisseur, ou `None` si aucun token pertinent n'est trouvé.

---

## InvoiceExtractorSimple._create_prompt()

### In
| Paramètre | Type | Description |
|-----------|------|-------------|
| `pdf_text` | `str` | Texte extrait du PDF (tronqué à 10 000 caractères si nécessaire) |
| `filename` | `str` | Nom du fichier, injecté dans le prompt pour aider le LLM |

### Transform
Construit un prompt structuré en deux étapes pour le LLM : identification du client (entités `KNOWN_CLIENTS`) puis identification du fournisseur. Tronque `pdf_text` à 10 000 caractères si besoin. Injecte la liste des clients connus pour éviter la confusion client/fournisseur.

### Out
Chaîne de caractères contenant le prompt complet prêt à être envoyé à Bedrock.

---

## InvoiceExtractorSimple.process_s3_event()

### In
| Paramètre | Type | Description |
|-----------|------|-------------|
| `event` | `dict` | Événement S3 Lambda avec `Records[0].s3` (bucket + key) |

### Transform
1. Extrait bucket et clé depuis `event["Records"][0]["s3"]`.
2. Télécharge le fichier en `/tmp/<filename>` via le SDK boto3 S3.
3. Appelle `extract_from_pdf` pour obtenir les données structurées.
4. Sauvegarde dans DynamoDB via `DynamoDBClient.save_invoice_data`.
5. Supprime systématiquement le fichier temporaire (bloc `finally`).

### Out
Dictionnaire `{"statusCode": 200, "body": ...}` en cas de succès, ou `{"statusCode": 500, "body": ...}` en cas d'erreur.

---

## PDFExtractorSimple.__init__()

### In
Aucun paramètre.

### Transform
Initialise l'instance sans configuration particulière.

### Out
Aucune valeur de retour.

---

## PDFExtractorSimple.extract_text()

### In
| Paramètre | Type | Description |
|-----------|------|-------------|
| `pdf_path` | `str` | Chemin vers le fichier PDF |

### Transform
Appelle `_extract_with_pypdf2` pour obtenir le texte brut, puis `_clean_extracted_text` pour le normaliser.

### Out
Texte nettoyé et normalisé du PDF, prêt pour le prompt.

---

## PDFExtractorSimple._extract_with_pypdf2()

### In
| Paramètre | Type | Description |
|-----------|------|-------------|
| `pdf_path` | `str` | Chemin vers le fichier PDF |

### Transform
Ouvre le PDF en lecture binaire avec PyPDF2. Itère sur toutes les pages, préfixe chaque bloc de texte par `--- Page N ---`, et ignore les pages qui échouent à l'extraction. Lève `ValueError` si aucun texte n'a pu être extrait.

### Out
Chaîne de caractères brute avec le contenu de toutes les pages, séparées par des lignes vides.

---

## PDFExtractorSimple._clean_extracted_text()

### In
| Paramètre | Type | Description |
|-----------|------|-------------|
| `text` | `str` | Texte brut extrait par PyPDF2 |

### Transform
Applique successivement : suppression des caractères de contrôle, normalisation des espaces multiples, limitation des sauts de ligne à deux consécutifs maximum, suppression des espaces en début/fin de ligne.

### Out
Texte normalisé, plus compact et propre.

---

## PDFExtractorSimple.extract_metadata()

### In
| Paramètre | Type | Description |
|-----------|------|-------------|
| `pdf_path` | `str` | Chemin vers le fichier PDF |

### Transform
Lit les métadonnées PDF (auteur, titre, date de création…) via PyPDF2 et ajoute le nombre de pages. Nettoie les clés en retirant le préfixe `/`. En cas d'erreur, retourne un dictionnaire vide plutôt que de lever une exception.

### Out
Dictionnaire des métadonnées PDF (`{"Title": "...", "num_pages": 3, ...}`).

---

## PDFExtractorSimple.validate_pdf()

### In
| Paramètre | Type | Description |
|-----------|------|-------------|
| `pdf_path` | `str` | Chemin vers le fichier à valider |

### Transform
Vérifie d'abord la signature binaire `%PDF-` en en-tête du fichier, puis tente de l'ouvrir avec PyPDF2 pour confirmer qu'il contient au moins une page.

### Out
`True` si le fichier est un PDF valide et lisible, `False` sinon.

---

## BedrockClient.__init__()

### In
| Paramètre | Type | Description |
|-----------|------|-------------|
| `region` | `str` (optionnel) | Région AWS |
| `model_id` | `str` (optionnel) | Identifiant du modèle Bedrock |

### Transform
Lit la configuration depuis `Config`, instancie le client boto3 `bedrock-runtime`, puis détecte le type de modèle via `_detect_model_type`.

### Out
Aucune valeur de retour. Instance prête à invoquer un modèle.

---

## BedrockClient._detect_model_type()

### In
Aucun paramètre. Utilise `self.model_id`.

### Transform
Analyse l'identifiant du modèle pour déterminer son fournisseur : Anthropic (avec distinction Claude 1/2 vs Claude 3+), Meta, Amazon, AI21, Cohere, ou inconnu. Cette détection pilote le format JSON des requêtes.

### Out
Chaîne parmi `"anthropic_messages"`, `"anthropic_legacy"`, `"meta"`, `"amazon"`, `"ai21"`, `"cohere"`, `"unknown"`.

---

## BedrockClient._create_request_body()

### In
| Paramètre | Type | Description |
|-----------|------|-------------|
| `prompt` | `str` | Texte du prompt à envoyer au modèle |

### Transform
Construit le corps de la requête JSON selon `self.model_type`. Chaque fournisseur attend un format différent (Messages API pour Claude 3+, Completions API pour Claude 1/2, format natif pour Meta/Amazon/AI21/Cohere).

### Out
Dictionnaire prêt à être sérialisé en JSON et envoyé à `invoke_model`.

---

## BedrockClient._parse_response()

### In
| Paramètre | Type | Description |
|-----------|------|-------------|
| `response_body` | `dict` | Corps de la réponse désérialisée du modèle |

### Transform
Extrait le texte généré selon la structure propre à chaque fournisseur (`content[0].text` pour Anthropic Messages, `completion` pour Anthropic legacy, `generation` pour Meta, etc.). Gère un fallback générique pour les types inconnus.

### Out
Texte brut généré par le modèle, sans le contenant JSON.

---

## BedrockClient._extract_json_from_response()

### In
| Paramètre | Type | Description |
|-----------|------|-------------|
| `response_text` | `str` | Réponse texte du modèle |

### Transform
Tente l'extraction JSON en trois passes dans l'ordre de priorité :
1. Blocs délimités par des backticks `` ```json ... ``` ``.
2. Parsing direct de la réponse entière.
3. Parsing brace-balanced : localise la première accolade ouvrante et suit les imbrications pour extraire le premier objet JSON valide.

### Out
Dictionnaire Python si un JSON valide est trouvé, `None` sinon.

---

## BedrockClient._normalize_field_names()

### In
| Paramètre | Type | Description |
|-----------|------|-------------|
| `data` | `dict` | Données JSON avec des noms de champs potentiellement variés |

### Transform
Mappe des noms alternatifs (anglais ou variantes) vers les noms canoniques du schéma cible (`fournisseur`, `montant_ht`, `devise`, `numero_facture`, `date_facture`, `chrono`, `couverture`, `nom_fichier`). Les champs non mappés sont conservés tels quels.

### Out
Dictionnaire avec uniquement les noms de champs canoniques.

---

## BedrockClient.extract_invoice_data()

### In
| Paramètre | Type | Description |
|-----------|------|-------------|
| `prompt` | `str` | Prompt complet contenant le texte PDF et les instructions |

### Transform
1. Construit la requête via `_create_request_body`.
2. Appelle `invoke_model` sur le client Bedrock.
3. Parse la réponse via `_parse_response`.
4. Extrait le JSON via `_extract_json_from_response`.
5. Normalise les noms de champs via `_normalize_field_names`.
6. Valide les champs requis via `_validate_extracted_data`.
7. Si aucun JSON n'est trouvé, tente une extraction par expressions régulières via `_extract_manual_data`.

### Out
Dictionnaire structuré des données de facture selon le schéma canonique.

---

## BedrockClient._validate_extracted_data()

### In
| Paramètre | Type | Description |
|-----------|------|-------------|
| `data` | `dict` | Données extraites à valider |

### Transform
Vérifie la présence des champs obligatoires (`fournisseur`, `montant_ht`, `numero_facture`, `date_facture`) et des champs optionnels (`chrono`, `couverture`, `nom_fichier`). Émet des warnings pour les champs absents et initialise les optionnels à `None` s'ils manquent.

### Out
Aucune valeur de retour. Modifie `data` en place pour les optionnels manquants.

---

## BedrockClient._extract_manual_data()

### In
| Paramètre | Type | Description |
|-----------|------|-------------|
| `response_text` | `str` | Réponse texte du modèle ne contenant pas de JSON structuré |

### Transform
Dernier recours : applique des expressions régulières sur le texte libre pour extraire les champs principaux (`fournisseur`, `montant_ht`, `numero_facture`, `date_facture`). Tente aussi un pattern générique pour les montants en euros.

### Out
Dictionnaire avec les champs canoniques, certains pouvant être `None` si non détectés.

---

## BedrockClient.test_connection()

### In
Aucun paramètre.

### Transform
Envoie un prompt minimaliste (`"TEST_OK"`) à Bedrock pour vérifier que le client est correctement configuré et que les droits IAM sont opérationnels.

### Out
`True` si l'appel réussit, `False` en cas d'exception.

---

## DynamoDBClient.__init__()

### In
| Paramètre | Type | Description |
|-----------|------|-------------|
| `region` | `str` (optionnel) | Région AWS |
| `table_name` | `str` (optionnel) | Nom de la table DynamoDB |

### Transform
Initialise les clients boto3 `dynamodb` (bas niveau) et `dynamodb.resource` (haut niveau), puis appelle `_ensure_table_exists` pour créer la table si besoin.

### Out
Aucune valeur de retour.

---

## DynamoDBClient._ensure_table_exists()

### In
Aucun paramètre. Utilise `self.table_name`.

### Transform
Tente de décrire la table via `describe_table`. Si la réponse est `ResourceNotFoundException`, appelle `_create_table`. Propage toute autre exception.

### Out
Aucune valeur de retour. Garantit que la table existe au retour de la méthode.

---

## DynamoDBClient._create_table()

### In
Aucun paramètre.

### Transform
Crée la table DynamoDB avec `invoice_id` comme clé primaire (HASH) et trois index secondaires globaux (GSI) sur `numero_facture`, `date_facture` et `fournisseur`. Attend que la table soit en état ACTIVE avant de retourner.

### Out
Aucune valeur de retour. Effet de bord : table créée dans AWS.

---

## DynamoDBClient.save_invoice_data()

### In
| Paramètre | Type | Description |
|-----------|------|-------------|
| `invoice_data` | `dict` | Données de facture extraites (schéma canonique + métadonnées) |

### Transform
1. Génère un UUID unique (`invoice_id`).
2. Construit l'item avec les champs plats (pour les GSI) et une copie JSON sérialisée dans `raw_data`.
3. Convertit au format DynamoDB via `_convert_to_dynamo_format`.
4. Persiste avec `put_item`.

### Out
Chaîne UUID identifiant l'enregistrement créé.

---

## DynamoDBClient._convert_to_dynamo_format()

### In
| Paramètre | Type | Description |
|-----------|------|-------------|
| `item` | `dict` | Dictionnaire Python à convertir |

### Transform
Transforme chaque valeur Python en attribut typé DynamoDB (`{"S": ...}`, `{"N": ...}`, `{"BOOL": ...}`, `{"M": ...}`, `{"SS": ...}`, `{"NS": ...}`). Les listes mixtes sont sérialisées en JSON et stockées comme chaîne. Les valeurs `None` sont ignorées. Récursif pour les dictionnaires imbriqués.

### Out
Dictionnaire au format DynamoDB prêt pour `put_item` ou `update_item`.

---

## DynamoDBClient.get_invoice()

### In
| Paramètre | Type | Description |
|-----------|------|-------------|
| `invoice_id` | `str` | UUID de la facture à récupérer |

### Transform
Effectue un `get_item` par clé primaire, puis convertit le résultat via `_convert_from_dynamo_format`. Retourne `None` sans lever d'exception si la facture n'existe pas.

### Out
Dictionnaire Python de la facture, ou `None`.

---

## DynamoDBClient._convert_from_dynamo_format()

### In
| Paramètre | Type | Description |
|-----------|------|-------------|
| `dynamo_item` | `dict` | Item au format DynamoDB (`{"key": {"S": "val"}, ...}`) |

### Transform
Inverse la conversion : mappe les types DynamoDB (`S`, `N`, `BOOL`, `M`, `SS`, `NS`, `NULL`) vers leurs équivalents Python. Tente de parser `raw_data` en JSON pour produire un champ `parsed_data`.

### Out
Dictionnaire Python avec les types natifs.

---

## DynamoDBClient.query_by_invoice_number()

### In
| Paramètre | Type | Description |
|-----------|------|-------------|
| `invoice_number` | `str` | Numéro de facture exact |

### Transform
Requête sur le GSI `numero_facture-index` avec une condition d'égalité. Convertit chaque résultat via `_convert_from_dynamo_format`.

### Out
Liste de dictionnaires Python des factures correspondantes (vide si aucun résultat).

---

## DynamoDBClient.query_by_supplier()

### In
| Paramètre | Type | Description |
|-----------|------|-------------|
| `supplier` | `str` | Nom exact du fournisseur |

### Transform
Requête sur le GSI `fournisseur-index`. Même logique que `query_by_invoice_number`.

### Out
Liste de dictionnaires Python des factures du fournisseur.

---

## DynamoDBClient.query_by_date_range()

### In
| Paramètre | Type | Description |
|-----------|------|-------------|
| `start_date` | `str` | Date de début au format `YYYY-MM-DD` |
| `end_date` | `str` | Date de fin au format `YYYY-MM-DD` |

### Transform
Effectue un scan complet de la table avec un filtre `BETWEEN` sur `date_facture`. Moins performant qu'une requête sur GSI, mais couvre les plages de dates.

### Out
Liste de dictionnaires Python des factures dans l'intervalle.

---

## DynamoDBClient.delete_invoice()

### In
| Paramètre | Type | Description |
|-----------|------|-------------|
| `invoice_id` | `str` | UUID de la facture à supprimer |

### Transform
Appelle `delete_item` par clé primaire. Capture les exceptions boto3 et retourne `False` sans propager.

### Out
`True` si la suppression a réussi, `False` en cas d'erreur.

---

## get_aws_region()

### In
Aucun paramètre. Lit les sources d'information implicites suivantes, par ordre de priorité.

### Transform
1. Variable d'environnement `AWS_REGION`.
2. Région active de la session boto3 (configuration AWS CLI / `~/.aws/config`).
3. Valeur par défaut `"us-west-2"`.

### Out
Chaîne de caractères de la région AWS (`"eu-west-1"`, `"us-west-2"`, etc.).

---

## get_aws_credentials()

### In
Aucun paramètre.

### Transform
Tente de récupérer les credentials via `boto3.Session().get_credentials()` (supporte tous les mécanismes standard : profil, rôle IAM, variables d'environnement…). Retombe sur les variables d'environnement `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_SESSION_TOKEN`.

### Out
Dictionnaire `{"access_key": ..., "secret_key": ..., "token": ...}`.

---

## Config.set_model()

### In
| Paramètre | Type | Description |
|-----------|------|-------------|
| `model_key` | `str` | Clé du modèle dans `BEDROCK_AVAILABLE_MODELS` (ex: `"claude-3-sonnet"`) |

### Transform
Vérifie que la clé existe dans le catalogue, met à jour `Config.BEDROCK_MODEL_ID` à la valeur correspondante.

### Out
`True` si le modèle existe et a été sélectionné, `False` sinon.

---

## Config.get_available_models()

### In
Aucun paramètre.

### Transform
Retourne directement le dictionnaire statique `BEDROCK_AVAILABLE_MODELS`.

### Out
Dictionnaire `{clé_courte: model_id_complet}`.

---

## Config.list_available_models()

### In
Aucun paramètre.

### Transform
Affiche le catalogue des modèles disponibles sur la sortie standard, formaté en tableau.

### Out
Aucune valeur de retour. Effet de bord : affichage console.

---

## Config.validate()

### In
Aucun paramètre.

### Transform
Vérifie la présence des credentials AWS, la validité de `MAX_PDF_SIZE_MB` et `EXTRACTION_TIMEOUT`. Émet un avertissement si `BEDROCK_MODEL_ID` n'est pas dans le catalogue connu (tolérance pour les modèles personnalisés).

### Out
`True` si la configuration est valide, `False` avec affichage des erreurs sinon.

---

## Config.to_dict()

### In
Aucun paramètre.

### Transform
Parcourt les attributs de classe dont le nom est entièrement en majuscules (hors attributs dunder) et les rassemble dans un dictionnaire.

### Out
Dictionnaire de toutes les valeurs de configuration.

---

## Config.print_config()

### In
| Paramètre | Type | Description |
|-----------|------|-------------|
| `hide_secrets` | `bool` | Si `True` (défaut), masque les clés contenant `key`, `secret`, `token`, `password` |

### Transform
Appelle `to_dict()` et affiche chaque clé/valeur, en remplaçant les valeurs sensibles par `***MASQUÉ***`.

### Out
Aucune valeur de retour. Effet de bord : affichage console.

---

## fetch_records()

### In
Aucun paramètre. Lit les variables globales `TABLE_NAME` et `REGION`.

### Transform
Effectue un scan paginé de la table DynamoDB. Pour chaque item, fusionne le contenu de `raw_data` (JSON sérialisé) avec les champs plats DynamoDB. Construit une ligne par facture avec tous les champs des `COLUMNS`. Trie par `date_facture` décroissant.

### Out
Liste de dictionnaires, un par facture, avec les champs de `COLUMNS` plus `invoice_id`.

---

## delete_records()

### In
| Paramètre | Type | Description |
|-----------|------|-------------|
| `invoice_ids` | `list[str]` | Liste des UUIDs à supprimer |

### Transform
Itère sur la liste et appelle `delete_item` pour chaque identifiant.

### Out
Nombre d'éléments supprimés.

---

## upload_to_s3()

### In
| Paramètre | Type | Description |
|-----------|------|-------------|
| `filename` | `str` | Nom de l'objet S3 (clé) |
| `content` | `bytes` | Contenu binaire du fichier |

### Transform
Crée un client S3 et dépose le contenu dans le bucket configuré via `S3_BUCKET`.

### Out
Aucune valeur de retour. Effet de bord : objet créé dans S3, ce qui déclenche la Lambda d'extraction.

---

## build_xlsx()

### In
| Paramètre | Type | Description |
|-----------|------|-------------|
| `records` | `list[dict]` | Liste de lignes factures au format `COLUMNS` |

### Transform
Crée un classeur openpyxl avec une feuille `"Factures"`. Applique un en-tête bleu gras. Formate les cellules `montant_ht` en nombre, `date_facture` en date, `extraction_date` en date-heure. Calcule les largeurs de colonnes automatiquement (max 40 caractères). Active le filtre automatique et fige la première ligne.

### Out
Contenu binaire du fichier XLSX (objet `bytes`).

---

## main_page()

### In
Aucun paramètre. Fonction décorée `@ui.page("/")`, exécutée à chaque chargement de la page NiceGUI.

### Transform
Construit l'interface complète : en-tête, zone d'upload S3, filtres, tableau de données, boutons d'export et de suppression. Définit les fonctions internes suivantes :

- **`handle_upload(e)`** — Lit le fichier uploadé et appelle `upload_to_s3`. Affiche une notification de succès ou d'erreur.
- **`handle_rejected(e)`** — Affiche un avertissement si le fichier n'est pas un PDF.
- **`load_data()`** — Appelle `fetch_records`, peuple `all_records` et `filtered`, met à jour le tableau et le résumé.
- **`apply_filters()`** — Filtre `all_records` par fournisseur (sous-chaîne, insensible à la casse) et par date minimale.
- **`reset_filters()`** — Vide les champs de filtre et restaure la liste complète.
- **`refresh_summary()`** — Recalcule le nombre de factures et la somme des montants HT affichés.
- **`export_selected()`** — Génère et télécharge un XLSX avec les lignes sélectionnées dans le tableau.
- **`export_all()`** — Génère et télécharge un XLSX avec toutes les lignes filtrées.
- **`confirm_delete_selected(selected)`** — Affiche une boîte de confirmation avant suppression des lignes sélectionnées.
- **`do_delete_selected(selected, dlg)`** — Ferme le dialogue, appelle `delete_records`, recharge les données.
- **`confirm_delete_all()`** — Affiche une confirmation avant suppression de toutes les factures.
- **`do_delete_all(dlg)`** — Ferme le dialogue, supprime toutes les factures, recharge.

Déclenche `load_data` au démarrage via `ui.timer(0.1, ..., once=True)`.

### Out
Aucune valeur de retour. Effet de bord : rendu de la page web dans le navigateur.

---

## scan_table()

### In
| Paramètre | Type | Description |
|-----------|------|-------------|
| `fournisseur` | `str` (optionnel) | Filtre sur le nom du fournisseur (sous-chaîne, insensible à la casse) |
| `depuis` | `str` (optionnel) | Date minimale `YYYY-MM-DD` |

### Transform
Scan paginé de DynamoDB, fusion `raw_data` + champs plats (identique à `fetch_records`). Applique les filtres fournisseur et date en mémoire. Trie par date décroissante.

### Out
Liste de dictionnaires Python représentant les factures filtrées.

---

## display_table()

### In
| Paramètre | Type | Description |
|-----------|------|-------------|
| `records` | `list[dict]` | Liste des factures à afficher |

### Transform
Calcule les largeurs de colonnes en fonction du contenu. Affiche un tableau ASCII dans le terminal avec séparateurs, en-tête et données. Calcule et affiche le total des montants HT.

### Out
Aucune valeur de retour. Effet de bord : affichage dans le terminal.

---

## export_xlsx()

### In
| Paramètre | Type | Description |
|-----------|------|-------------|
| `records` | `list[dict]` | Liste des factures à exporter |
| `output_path` | `str` | Chemin du fichier XLSX de destination |

### Transform
Même logique de formatage que `build_xlsx` (en-tête bleu, formatage des montants, dates et date-heures, largeurs auto, filtre, ligne figée). Sauvegarde directement dans un fichier au lieu de retourner des bytes.

### Out
Aucune valeur de retour. Effet de bord : fichier XLSX créé à `output_path`.

---

## main() — view_invoices

### In
Aucun paramètre. Lit les arguments de la ligne de commande (`--export`, `--out`, `--fournisseur`, `--depuis`).

### Transform
Parse les arguments avec `argparse`, appelle `scan_table` avec les filtres éventuels, affiche le résultat via `display_table`, et si `--export` est passé, génère le fichier XLSX via `export_xlsx`.

### Out
Aucune valeur de retour. Effets de bord : affichage terminal, et éventuellement fichier XLSX créé.
