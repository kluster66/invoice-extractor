# Diagramme de flux — Invoice Extractor

```mermaid
flowchart TD
    %% ── Entrées utilisateur ────────────────────────────────────────────────
    S3_UPLOAD([Dépôt PDF via S3\nupload_to_s3 / UI])
    CLI_START([Démarrage CLI\nview_invoices.py])
    UI_START([Ouverture navigateur\nui_invoices.py])

    %% ── Déclenchement Lambda ───────────────────────────────────────────────
    S3_EVENT[Événement S3\nRecords\[0\].s3]
    LAMBDA[lambda_handler\nrécupère AWS_REGION]
    PROCESS_S3[process_s3_event\nextrait bucket + key]
    S3_DOWNLOAD[Téléchargement S3\n/tmp/fichier.pdf]

    %% ── Extraction PDF ──────────────────────────────────────────────────────
    EXTRACT_PDF[extract_from_pdf\npdf_path + filename]
    PYPDF2[_extract_with_pypdf2\npage par page]
    CLEAN_TEXT[_clean_extracted_text\nnormalisation]
    PDF_TEXT[(Texte nettoyé\n10 000 car. max)]

    %% ── Prompt ──────────────────────────────────────────────────────────────
    CREATE_PROMPT[_create_prompt\nclient vs fournisseur]

    %% ── Bedrock ─────────────────────────────────────────────────────────────
    DETECT_MODEL[_detect_model_type\nAnthropid / Meta / Amazon…]
    CREATE_BODY[_create_request_body\nformat JSON par fournisseur]
    BEDROCK_API([AWS Bedrock\ninvoke_model])
    PARSE_RESP[_parse_response\nextrait le texte]
    EXTRACT_JSON[_extract_json_from_response\nbackticks → direct → brace-balanced]

    %% ── Post-traitement ─────────────────────────────────────────────────────
    JSON_FOUND{JSON valide\ntrouvé ?}
    MANUAL[_extract_manual_data\nregex de secours]
    NORMALIZE[_normalize_field_names\nschéma canonique]
    VALIDATE[_validate_extracted_data\nchamps requis]
    FIX_SUPPLIER[_fix_supplier_if_needed\nclient connu dans fournisseur ?]
    SUPPLIER_FROM_FILENAME{Fournisseur\ndans nom fichier ?}
    EXTRACT_SUPP[_extract_supplier_from_filename\nélimination + tokenisation]

    %% ── DynamoDB ─────────────────────────────────────────────────────────────
    ADD_META[Ajout métadonnées\nextraction_date, pdf_path]
    SAVE_DDB[save_invoice_data\ngénère UUID]
    CONVERT_DDB[_convert_to_dynamo_format\ntypage DynamoDB]
    DYNAMO_TABLE[(DynamoDB\ntable invoices)]

    %% ── Réponse Lambda ───────────────────────────────────────────────────────
    LAMBDA_OK([Réponse 200\ninvoice_id + data])
    LAMBDA_ERR([Réponse 500\nmessage d'erreur])

    %% ── Interface NiceGUI ────────────────────────────────────────────────────
    MAIN_PAGE[main_page\nconstruit l'interface]
    LOAD_DATA[load_data\ndéclenché au démarrage]
    FETCH_RECORDS[fetch_records\nscan paginé DynamoDB]
    APPLY_FILTERS[apply_filters\nfournisseur + date]
    REFRESH_SUMMARY[refresh_summary\ncompte + total HT]
    TABLE_UI[(Tableau NiceGUI\nmise à jour rows)]

    EXPORT_SEL[export_selected\nligne(s) cochée(s)]
    EXPORT_ALL[export_all\nliste filtrée]
    BUILD_XLSX[build_xlsx\nopenpyxl]
    XLSX_DL([Téléchargement XLSX\nnavigateur])

    DEL_CONFIRM[confirm_delete_selected\nou confirm_delete_all]
    DO_DELETE[do_delete_selected\nou do_delete_all]
    DELETE_RECORDS[delete_records\ndelete_item par ID]

    %% ── CLI ──────────────────────────────────────────────────────────────────
    CLI_MAIN[main\nparse argparse]
    SCAN_TABLE[scan_table\nscan paginé + filtres]
    DISPLAY_TABLE[display_table\ntableau ASCII terminal]
    EXPORT_XLSX_CLI[export_xlsx\nfichier .xlsx]
    XLSX_FILE([Fichier XLSX\nsur disque])

    %% ─────────────────────────────────────────────────────────────────────────
    %% Pipeline Lambda principal
    S3_UPLOAD --> S3_EVENT
    S3_EVENT  --> LAMBDA
    LAMBDA    --> PROCESS_S3
    PROCESS_S3 --> S3_DOWNLOAD
    S3_DOWNLOAD --> EXTRACT_PDF

    EXTRACT_PDF --> PYPDF2
    PYPDF2      --> CLEAN_TEXT
    CLEAN_TEXT  --> PDF_TEXT
    PDF_TEXT    --> CREATE_PROMPT

    CREATE_PROMPT --> DETECT_MODEL
    DETECT_MODEL  --> CREATE_BODY
    CREATE_BODY   --> BEDROCK_API
    BEDROCK_API   --> PARSE_RESP
    PARSE_RESP    --> EXTRACT_JSON
    EXTRACT_JSON  --> JSON_FOUND

    JSON_FOUND -- Oui --> NORMALIZE
    JSON_FOUND -- Non --> MANUAL
    MANUAL      --> NORMALIZE
    NORMALIZE   --> VALIDATE
    VALIDATE    --> FIX_SUPPLIER

    FIX_SUPPLIER --> SUPPLIER_FROM_FILENAME
    SUPPLIER_FROM_FILENAME -- Fournisseur trouvé --> EXTRACT_SUPP
    SUPPLIER_FROM_FILENAME -- Pas de confusion --> ADD_META
    EXTRACT_SUPP --> ADD_META

    ADD_META  --> SAVE_DDB
    SAVE_DDB  --> CONVERT_DDB
    CONVERT_DDB --> DYNAMO_TABLE

    DYNAMO_TABLE --> LAMBDA_OK
    PROCESS_S3 -- Erreur --> LAMBDA_ERR

    %% Interface NiceGUI
    UI_START     --> MAIN_PAGE
    MAIN_PAGE    --> LOAD_DATA
    LOAD_DATA    --> FETCH_RECORDS
    FETCH_RECORDS --> DYNAMO_TABLE
    DYNAMO_TABLE  --> TABLE_UI
    TABLE_UI     --> APPLY_FILTERS
    APPLY_FILTERS --> REFRESH_SUMMARY
    REFRESH_SUMMARY --> TABLE_UI

    TABLE_UI --> EXPORT_SEL
    TABLE_UI --> EXPORT_ALL
    EXPORT_SEL --> BUILD_XLSX
    EXPORT_ALL --> BUILD_XLSX
    BUILD_XLSX --> XLSX_DL

    TABLE_UI --> DEL_CONFIRM
    DEL_CONFIRM --> DO_DELETE
    DO_DELETE --> DELETE_RECORDS
    DELETE_RECORDS --> DYNAMO_TABLE
    DELETE_RECORDS --> LOAD_DATA

    %% Upload UI → Lambda
    MAIN_PAGE --> S3_UPLOAD

    %% CLI
    CLI_START --> CLI_MAIN
    CLI_MAIN  --> SCAN_TABLE
    SCAN_TABLE --> DYNAMO_TABLE
    DYNAMO_TABLE --> DISPLAY_TABLE
    CLI_MAIN -- --export --> EXPORT_XLSX_CLI
    DISPLAY_TABLE --> EXPORT_XLSX_CLI
    EXPORT_XLSX_CLI --> XLSX_FILE
```
