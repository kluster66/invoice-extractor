# Function Reference — Invoice Extractor

## lambda_handler()

### In
| Parameter | Type | Description |
|-----------|------|-------------|
| `event` | `dict` | AWS Lambda event containing the S3 trigger record |
| `context` | `Any` | Lambda execution context (not used directly) |

### Transform
Main entry point for AWS Lambda. Reads the `AWS_REGION` environment variable, instantiates `InvoiceExtractorSimple`, and delegates processing to `process_s3_event`.

### Out
HTTP-like dictionary with `statusCode` (200 or 500) and a JSON `body` describing the result or the error.

---

## InvoiceExtractorSimple.__init__()

### In
| Parameter | Type | Description |
|-----------|------|-------------|
| `region` | `str` (optional) | AWS region; falls back to `Config.AWS_REGION` if omitted |

### Transform
Instantiates the three sub-clients — `PDFExtractorSimple`, `BedrockClient`, and `DynamoDBClient` — all targeting the same AWS region.

### Out
No return value. Prepares the instance for subsequent calls.

---

## InvoiceExtractorSimple.extract_from_pdf()

### In
| Parameter | Type | Description |
|-----------|------|-------------|
| `pdf_path` | `str` | Local path to the PDF file |
| `filename` | `str` | Original file name (used in the prompt and metadata) |

### Transform
Orchestrates the full pipeline in five steps:
1. Extracts raw text via `PDFExtractorSimple.extract_text`.
2. Builds the extraction prompt via `_create_prompt`.
3. Calls `BedrockClient.extract_invoice_data` to get structured data.
4. Optionally corrects the supplier field via `_fix_supplier_if_needed`.
5. Appends metadata (`extraction_date`, `pdf_path`, `nom_fichier`).

### Out
Dictionary containing all invoice fields (`fournisseur`, `montant_ht`, `devise`, `numero_facture`, `date_facture`, `chrono`, `couverture`, `nom_fichier`) plus extraction metadata.

---

## InvoiceExtractorSimple._fix_supplier_if_needed()

### In
| Parameter | Type | Description |
|-----------|------|-------------|
| `data` | `dict` | Data extracted by the LLM |
| `filename` | `str` | Source file name |

### Transform
Checks whether the `fournisseur` field returned by the LLM matches a known client entity (`KNOWN_CLIENTS`). If so, attempts to recover the real supplier from the file name via `_extract_supplier_from_filename`. Sets `fournisseur` to `None` if identification fails.

### Out
Modified `data` dictionary (field `fournisseur` corrected or set to `None`).

---

## InvoiceExtractorSimple._extract_supplier_from_filename()

### In
| Parameter | Type | Description |
|-----------|------|-------------|
| `filename` | `str` | PDF file name (with extension) |

### Transform
Works by elimination on the bare file name (no extension):
1. Uppercases the string.
2. Removes purely numeric sequences (dates, sequential numbers…).
3. Removes known client names.
4. Filters out short tokens and generic billing words (`_FILENAME_NOISE_WORDS`).
5. Returns the first meaningful token, title-cased.

### Out
String with the likely supplier name, or `None` if no meaningful token is found.

---

## InvoiceExtractorSimple._create_prompt()

### In
| Parameter | Type | Description |
|-----------|------|-------------|
| `pdf_text` | `str` | Text extracted from the PDF (truncated to 10,000 characters if necessary) |
| `filename` | `str` | File name injected into the prompt to help the LLM |

### Transform
Builds a two-step structured prompt for the LLM: first identify the client (using `KNOWN_CLIENTS` as a hard constraint), then identify the supplier. Truncates `pdf_text` to 10,000 characters if needed and injects the known-client list to prevent client/supplier confusion.

### Out
Complete prompt string ready to be sent to Bedrock.

---

## InvoiceExtractorSimple.process_s3_event()

### In
| Parameter | Type | Description |
|-----------|------|-------------|
| `event` | `dict` | S3 Lambda event with `Records[0].s3` (bucket + key) |

### Transform
1. Extracts bucket name and object key from `event["Records"][0]["s3"]`.
2. Downloads the file to `/tmp/<filename>` via the boto3 S3 SDK.
3. Calls `extract_from_pdf` to produce structured data.
4. Saves to DynamoDB via `DynamoDBClient.save_invoice_data`.
5. Always deletes the temp file in a `finally` block.

### Out
`{"statusCode": 200, "body": ...}` on success, or `{"statusCode": 500, "body": ...}` on failure.

---

## PDFExtractorSimple.__init__()

### In
No parameters.

### Transform
Initializes the instance with no special configuration.

### Out
No return value.

---

## PDFExtractorSimple.extract_text()

### In
| Parameter | Type | Description |
|-----------|------|-------------|
| `pdf_path` | `str` | Path to the PDF file |

### Transform
Calls `_extract_with_pypdf2` to get raw text, then `_clean_extracted_text` to normalize it.

### Out
Clean, normalized text from the PDF, ready for prompting.

---

## PDFExtractorSimple._extract_with_pypdf2()

### In
| Parameter | Type | Description |
|-----------|------|-------------|
| `pdf_path` | `str` | Path to the PDF file |

### Transform
Opens the PDF in binary mode with PyPDF2. Iterates over all pages, prefixes each text block with `--- Page N ---`, and skips pages that fail to extract. Raises `ValueError` if no text could be extracted at all.

### Out
Raw string containing the content of all pages, separated by blank lines.

---

## PDFExtractorSimple._clean_extracted_text()

### In
| Parameter | Type | Description |
|-----------|------|-------------|
| `text` | `str` | Raw text extracted by PyPDF2 |

### Transform
Applies a sequence of normalizations: strips control characters, collapses multiple spaces, limits consecutive newlines to two, trims whitespace at the start and end of each line.

### Out
Normalized, compact text.

---

## PDFExtractorSimple.extract_metadata()

### In
| Parameter | Type | Description |
|-----------|------|-------------|
| `pdf_path` | `str` | Path to the PDF file |

### Transform
Reads PDF metadata (author, title, creation date…) via PyPDF2 and appends the page count. Cleans keys by stripping the leading `/` prefix. Returns an empty dict rather than raising on error.

### Out
Dictionary of PDF metadata (`{"Title": "...", "num_pages": 3, ...}`).

---

## PDFExtractorSimple.validate_pdf()

### In
| Parameter | Type | Description |
|-----------|------|-------------|
| `pdf_path` | `str` | Path to the file to validate |

### Transform
Checks the binary `%PDF-` header first, then attempts to open the file with PyPDF2 to confirm it contains at least one page.

### Out
`True` if the file is a valid, readable PDF; `False` otherwise.

---

## BedrockClient.__init__()

### In
| Parameter | Type | Description |
|-----------|------|-------------|
| `region` | `str` (optional) | AWS region |
| `model_id` | `str` (optional) | Bedrock model identifier |

### Transform
Reads configuration from `Config`, instantiates the boto3 `bedrock-runtime` client, then detects the model type via `_detect_model_type`.

### Out
No return value. Instance ready to invoke a model.

---

## BedrockClient._detect_model_type()

### In
No parameters. Uses `self.model_id`.

### Transform
Parses the model identifier to determine its provider: Anthropic (distinguishing Claude 1/2 from Claude 3+), Meta, Amazon, AI21, Cohere, or unknown. This detection drives the JSON request format used in every subsequent call.

### Out
One of `"anthropic_messages"`, `"anthropic_legacy"`, `"meta"`, `"amazon"`, `"ai21"`, `"cohere"`, `"unknown"`.

---

## BedrockClient._create_request_body()

### In
| Parameter | Type | Description |
|-----------|------|-------------|
| `prompt` | `str` | Prompt text to send to the model |

### Transform
Builds the JSON request body according to `self.model_type`. Each provider expects a different structure (Messages API for Claude 3+, Completions API for Claude 1/2, native formats for Meta/Amazon/AI21/Cohere).

### Out
Dictionary ready to be JSON-serialized and passed to `invoke_model`.

---

## BedrockClient._parse_response()

### In
| Parameter | Type | Description |
|-----------|------|-------------|
| `response_body` | `dict` | Deserialized response body from the model |

### Transform
Extracts the generated text using the structure specific to each provider (`content[0].text` for Anthropic Messages, `completion` for legacy Anthropic, `generation` for Meta, etc.). Falls back to a generic extraction for unknown types.

### Out
Plain generated text string, without the JSON wrapper.

---

## BedrockClient._extract_json_from_response()

### In
| Parameter | Type | Description |
|-----------|------|-------------|
| `response_text` | `str` | Raw text response from the model |

### Transform
Attempts JSON extraction in three passes, in order of priority:
1. Backtick-delimited blocks (`` ```json ... ``` ``).
2. Direct parsing of the entire response.
3. Brace-balanced parsing: finds the first opening brace and tracks nesting depth to extract the first valid JSON object.

### Out
Python dictionary if valid JSON is found, `None` otherwise.

---

## BedrockClient._normalize_field_names()

### In
| Parameter | Type | Description |
|-----------|------|-------------|
| `data` | `dict` | JSON data with potentially varied field names |

### Transform
Maps alternative names (English variants or synonyms) to the canonical schema fields: `fournisseur`, `montant_ht`, `devise`, `numero_facture`, `date_facture`, `chrono`, `couverture`, `nom_fichier`. Unmapped fields are preserved as-is.

### Out
Dictionary with only canonical field names.

---

## BedrockClient.extract_invoice_data()

### In
| Parameter | Type | Description |
|-----------|------|-------------|
| `prompt` | `str` | Full prompt containing PDF text and extraction instructions |

### Transform
1. Builds the request via `_create_request_body`.
2. Calls `invoke_model` on the Bedrock client.
3. Parses the response via `_parse_response`.
4. Extracts JSON via `_extract_json_from_response`.
5. Normalizes field names via `_normalize_field_names`.
6. Validates required fields via `_validate_extracted_data`.
7. Falls back to regex extraction via `_extract_manual_data` if no JSON is found.

### Out
Structured dictionary of invoice data following the canonical schema.

---

## BedrockClient._validate_extracted_data()

### In
| Parameter | Type | Description |
|-----------|------|-------------|
| `data` | `dict` | Extracted data to validate |

### Transform
Checks for required fields (`fournisseur`, `montant_ht`, `numero_facture`, `date_facture`) and optional fields (`chrono`, `couverture`, `nom_fichier`). Logs warnings for missing fields and initializes absent optionals to `None`.

### Out
No return value. Modifies `data` in place for missing optionals.

---

## BedrockClient._extract_manual_data()

### In
| Parameter | Type | Description |
|-----------|------|-------------|
| `response_text` | `str` | Model text response that contained no structured JSON |

### Transform
Last resort: applies regular expressions to free-form text to extract the main fields (`fournisseur`, `montant_ht`, `numero_facture`, `date_facture`). Also tries a generic euro-amount pattern.

### Out
Dictionary with canonical fields, some potentially `None` if not matched.

---

## BedrockClient.test_connection()

### In
No parameters.

### Transform
Sends a minimal test prompt to Bedrock to verify that the client is correctly configured and that IAM permissions are operational.

### Out
`True` if the call succeeds, `False` on any exception.

---

## DynamoDBClient.__init__()

### In
| Parameter | Type | Description |
|-----------|------|-------------|
| `region` | `str` (optional) | AWS region |
| `table_name` | `str` (optional) | DynamoDB table name |

### Transform
Initializes both boto3 `dynamodb` (low-level client) and `dynamodb.resource` (high-level resource), then calls `_ensure_table_exists` to create the table if needed.

### Out
No return value.

---

## DynamoDBClient._ensure_table_exists()

### In
No parameters. Uses `self.table_name`.

### Transform
Attempts to describe the table via `describe_table`. If the response is `ResourceNotFoundException`, calls `_create_table`. Any other exception is re-raised.

### Out
No return value. Guarantees the table exists when the method returns.

---

## DynamoDBClient._create_table()

### In
No parameters.

### Transform
Creates the DynamoDB table with `invoice_id` as the primary hash key, plus three Global Secondary Indexes (GSIs) on `numero_facture`, `date_facture`, and `fournisseur`. Waits for the table to reach ACTIVE state before returning.

### Out
No return value. Side effect: table created in AWS.

---

## DynamoDBClient.save_invoice_data()

### In
| Parameter | Type | Description |
|-----------|------|-------------|
| `invoice_data` | `dict` | Extracted invoice data (canonical schema + metadata) |

### Transform
1. Generates a unique UUID (`invoice_id`).
2. Builds the item with flat fields (for GSI lookups) and a JSON-serialized copy in `raw_data`.
3. Converts to DynamoDB format via `_convert_to_dynamo_format`.
4. Persists with `put_item`.

### Out
UUID string identifying the created record.

---

## DynamoDBClient._convert_to_dynamo_format()

### In
| Parameter | Type | Description |
|-----------|------|-------------|
| `item` | `dict` | Python dictionary to convert |

### Transform
Transforms each Python value into a typed DynamoDB attribute (`{"S": ...}`, `{"N": ...}`, `{"BOOL": ...}`, `{"M": ...}`, `{"SS": ...}`, `{"NS": ...}`). Mixed-type lists are JSON-serialized and stored as strings. `None` values are omitted. Recursively handles nested dictionaries.

### Out
Dictionary in DynamoDB format, ready for `put_item` or `update_item`.

---

## DynamoDBClient.get_invoice()

### In
| Parameter | Type | Description |
|-----------|------|-------------|
| `invoice_id` | `str` | UUID of the invoice to retrieve |

### Transform
Performs a `get_item` by primary key, then converts the result via `_convert_from_dynamo_format`. Returns `None` without raising if the invoice does not exist.

### Out
Python dictionary of the invoice, or `None`.

---

## DynamoDBClient._convert_from_dynamo_format()

### In
| Parameter | Type | Description |
|-----------|------|-------------|
| `dynamo_item` | `dict` | Item in DynamoDB format |

### Transform
Reverses the conversion: maps DynamoDB types (`S`, `N`, `BOOL`, `M`, `SS`, `NS`, `NULL`) back to native Python types. Attempts to parse `raw_data` as JSON to produce a `parsed_data` field.

### Out
Python dictionary with native types.

---

## DynamoDBClient.query_by_invoice_number()

### In
| Parameter | Type | Description |
|-----------|------|-------------|
| `invoice_number` | `str` | Exact invoice number |

### Transform
Queries the `numero_facture-index` GSI with an equality condition. Converts each result via `_convert_from_dynamo_format`.

### Out
List of matching invoice dictionaries (empty list if none found).

---

## DynamoDBClient.query_by_supplier()

### In
| Parameter | Type | Description |
|-----------|------|-------------|
| `supplier` | `str` | Exact supplier name |

### Transform
Queries the `fournisseur-index` GSI. Same logic as `query_by_invoice_number`.

### Out
List of invoice dictionaries for the supplier.

---

## DynamoDBClient.query_by_date_range()

### In
| Parameter | Type | Description |
|-----------|------|-------------|
| `start_date` | `str` | Start date in `YYYY-MM-DD` format |
| `end_date` | `str` | End date in `YYYY-MM-DD` format |

### Transform
Performs a full table scan with a `BETWEEN` filter on `date_facture`. Less efficient than a GSI query, but handles arbitrary date ranges.

### Out
List of invoice dictionaries within the date range.

---

## DynamoDBClient.delete_invoice()

### In
| Parameter | Type | Description |
|-----------|------|-------------|
| `invoice_id` | `str` | UUID of the invoice to delete |

### Transform
Calls `delete_item` by primary key. Catches boto3 exceptions and returns `False` rather than propagating.

### Out
`True` if deletion succeeded, `False` on error.

---

## get_aws_region()

### In
No parameters. Reads from the following implicit sources, in priority order.

### Transform
1. `AWS_REGION` environment variable.
2. Active region from the boto3 session (AWS CLI config / `~/.aws/config`).
3. Default value `"us-west-2"`.

### Out
AWS region string (`"eu-west-1"`, `"us-west-2"`, etc.).

---

## get_aws_credentials()

### In
No parameters.

### Transform
Attempts to retrieve credentials via `boto3.Session().get_credentials()` (supports all standard mechanisms: profile, IAM role, environment variables…). Falls back to the `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_SESSION_TOKEN` environment variables.

### Out
Dictionary `{"access_key": ..., "secret_key": ..., "token": ...}`.

---

## Config.set_model()

### In
| Parameter | Type | Description |
|-----------|------|-------------|
| `model_key` | `str` | Key in `BEDROCK_AVAILABLE_MODELS` (e.g. `"claude-3-sonnet"`) |

### Transform
Checks that the key exists in the catalog and updates `Config.BEDROCK_MODEL_ID` to the corresponding value.

### Out
`True` if the model was found and selected, `False` otherwise.

---

## Config.get_available_models()

### In
No parameters.

### Transform
Returns the static `BEDROCK_AVAILABLE_MODELS` dictionary directly.

### Out
Dictionary `{short_key: full_model_id}`.

---

## Config.list_available_models()

### In
No parameters.

### Transform
Prints the model catalog to stdout in a formatted table.

### Out
No return value. Side effect: console output.

---

## Config.validate()

### In
No parameters.

### Transform
Checks AWS credentials, `MAX_PDF_SIZE_MB`, and `EXTRACTION_TIMEOUT`. Issues a warning (not an error) if `BEDROCK_MODEL_ID` is not in the known catalog, to allow custom or newer models.

### Out
`True` if configuration is valid, `False` with printed errors otherwise.

---

## Config.to_dict()

### In
No parameters.

### Transform
Iterates over class attributes whose names are fully uppercase (excluding dunder attributes) and collects them into a dictionary.

### Out
Dictionary of all configuration values.

---

## Config.print_config()

### In
| Parameter | Type | Description |
|-----------|------|-------------|
| `hide_secrets` | `bool` | If `True` (default), masks values whose keys contain `key`, `secret`, `token`, or `password` |

### Transform
Calls `to_dict()` and prints each key/value pair, replacing sensitive values with `***MASKED***`.

### Out
No return value. Side effect: console output.

---

## fetch_records()

### In
No parameters. Reads global variables `TABLE_NAME` and `REGION`.

### Transform
Performs a paginated DynamoDB scan. For each item, merges the `raw_data` JSON payload with the flat DynamoDB fields. Builds one row per invoice with all `COLUMNS` fields. Sorts by `date_facture` descending.

### Out
List of dictionaries, one per invoice, containing all `COLUMNS` fields plus `invoice_id`.

---

## delete_records()

### In
| Parameter | Type | Description |
|-----------|------|-------------|
| `invoice_ids` | `list[str]` | List of UUIDs to delete |

### Transform
Iterates over the list and calls `delete_item` for each identifier.

### Out
Number of items deleted.

---

## upload_to_s3()

### In
| Parameter | Type | Description |
|-----------|------|-------------|
| `filename` | `str` | S3 object name (key) |
| `content` | `bytes` | Binary file content |

### Transform
Creates an S3 client and uploads the content to the bucket configured in `S3_BUCKET`.

### Out
No return value. Side effect: object created in S3, which triggers the extraction Lambda.

---

## build_xlsx()

### In
| Parameter | Type | Description |
|-----------|------|-------------|
| `records` | `list[dict]` | Invoice rows in `COLUMNS` format |

### Transform
Creates an openpyxl workbook with a `"Factures"` sheet. Applies a bold blue header. Formats `montant_ht` cells as numbers, `date_facture` as dates, and `extraction_date` as datetime. Auto-sizes columns (max 40 characters). Activates auto-filter and freezes the first row.

### Out
Binary XLSX file content (`bytes`).

---

## main_page()

### In
No parameters. Decorated with `@ui.page("/")`, executed on each NiceGUI page load.

### Transform
Builds the complete UI: header, S3 upload zone, filter panel, data table, export and delete buttons. Defines the following inner functions:

- **`handle_upload(e)`** — Reads the uploaded file and calls `upload_to_s3`. Displays a success or error notification.
- **`handle_rejected(e)`** — Displays a warning if the file is not a PDF.
- **`load_data()`** — Calls `fetch_records`, populates `all_records` and `filtered`, updates the table and summary.
- **`apply_filters()`** — Filters `all_records` by supplier substring (case-insensitive) and minimum date.
- **`reset_filters()`** — Clears filter inputs and restores the full record list.
- **`refresh_summary()`** — Recalculates the invoice count and total HT amount shown in the toolbar.
- **`export_selected()`** — Generates and triggers a browser download of an XLSX for selected rows.
- **`export_all()`** — Generates and triggers a browser download of an XLSX for all filtered rows.
- **`confirm_delete_selected(selected)`** — Shows a confirmation dialog before deleting selected rows.
- **`do_delete_selected(selected, dlg)`** — Closes the dialog, calls `delete_records`, reloads data.
- **`confirm_delete_all()`** — Shows a confirmation dialog before deleting all invoices.
- **`do_delete_all(dlg)`** — Closes the dialog, deletes all invoices, reloads data.

Triggers `load_data` on startup via `ui.timer(0.1, ..., once=True)`.

### Out
No return value. Side effect: web page rendered in the browser.

---

## scan_table()

### In
| Parameter | Type | Description |
|-----------|------|-------------|
| `fournisseur` | `str` (optional) | Supplier name filter (substring, case-insensitive) |
| `depuis` | `str` (optional) | Minimum date `YYYY-MM-DD` |

### Transform
Paginated DynamoDB scan with `raw_data` / flat-field merge. Applies supplier and date filters in memory. Sorts by date descending.

### Out
List of filtered Python dictionaries representing invoices.

---

## display_table()

### In
| Parameter | Type | Description |
|-----------|------|-------------|
| `records` | `list[dict]` | Invoices to display |

### Transform
Calculates column widths from content. Prints an ASCII table to the terminal with separators, header row, and data rows. Calculates and prints the total HT amount.

### Out
No return value. Side effect: terminal output.

---

## export_xlsx()

### In
| Parameter | Type | Description |
|-----------|------|-------------|
| `records` | `list[dict]` | Invoices to export |
| `output_path` | `str` | Destination XLSX file path |

### Transform
Same formatting logic as `build_xlsx` (blue header, number/date/datetime formatting, auto-width, filter, frozen row). Saves directly to a file instead of returning bytes.

### Out
No return value. Side effect: XLSX file created at `output_path`.

---

## main() — view_invoices

### In
No parameters. Reads CLI arguments: `--export`, `--out`, `--fournisseur`, `--depuis`.

### Transform
Parses arguments with `argparse`, calls `scan_table` with any filters, displays results via `display_table`, and if `--export` is set, generates the XLSX file via `export_xlsx`.

### Out
No return value. Side effects: terminal display, and optionally an XLSX file.
