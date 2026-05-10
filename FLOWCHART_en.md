# Flow Diagram — Invoice Extractor

```mermaid
flowchart TD
    %% ── User inputs ────────────────────────────────────────────────────────
    S3_UPLOAD([PDF upload via S3\nupload_to_s3 / UI])
    CLI_START([CLI startup\nview_invoices.py])
    UI_START([Browser open\nui_invoices.py])

    %% ── Lambda trigger ──────────────────────────────────────────────────────
    S3_EVENT["S3 Event\nRecords[0].s3"]
    LAMBDA[lambda_handler\nreads AWS_REGION]
    PROCESS_S3[process_s3_event\nextracts bucket + key]
    S3_DOWNLOAD[S3 download\n/tmp/file.pdf]

    %% ── PDF extraction ──────────────────────────────────────────────────────
    EXTRACT_PDF[extract_from_pdf\npdf_path + filename]
    PYPDF2[_extract_with_pypdf2\npage by page]
    CLEAN_TEXT[_clean_extracted_text\nnormalization]
    PDF_TEXT[(Cleaned text\nmax 10,000 chars)]

    %% ── Prompt ──────────────────────────────────────────────────────────────
    CREATE_PROMPT[_create_prompt\nclient vs supplier]

    %% ── Bedrock ─────────────────────────────────────────────────────────────
    DETECT_MODEL[_detect_model_type\nAnthropic / Meta / Amazon…]
    CREATE_BODY[_create_request_body\nJSON format per provider]
    BEDROCK_API([AWS Bedrock\ninvoke_model])
    PARSE_RESP[_parse_response\nextracts text]
    EXTRACT_JSON[_extract_json_from_response\nbackticks → direct → brace-balanced]

    %% ── Post-processing ─────────────────────────────────────────────────────
    JSON_FOUND{Valid JSON\nfound?}
    MANUAL[_extract_manual_data\nregex fallback]
    NORMALIZE[_normalize_field_names\ncanonical schema]
    VALIDATE[_validate_extracted_data\nrequired fields]
    FIX_SUPPLIER[_fix_supplier_if_needed\nknown client in supplier field?]
    SUPPLIER_FROM_FILENAME{Supplier\nin filename?}
    EXTRACT_SUPP[_extract_supplier_from_filename\nelimination + tokenization]

    %% ── DynamoDB ─────────────────────────────────────────────────────────────
    ADD_META[Add metadata\nextraction_date, pdf_path]
    SAVE_DDB[save_invoice_data\ngenerates UUID]
    CONVERT_DDB[_convert_to_dynamo_format\nDynamoDB typing]
    DYNAMO_TABLE[(DynamoDB\ninvoices table)]

    %% ── Lambda response ──────────────────────────────────────────────────────
    LAMBDA_OK([Response 200\ninvoice_id + data])
    LAMBDA_ERR([Response 500\nerror message])

    %% ── NiceGUI interface ────────────────────────────────────────────────────
    MAIN_PAGE[main_page\nbuilds UI]
    LOAD_DATA[load_data\ntriggered on startup]
    FETCH_RECORDS[fetch_records\npaginated DynamoDB scan]
    APPLY_FILTERS[apply_filters\nsupplier + date]
    REFRESH_SUMMARY[refresh_summary\ncount + total HT]
    TABLE_UI[(NiceGUI table\nrows updated)]

    EXPORT_SEL[export_selected\nchecked rows]
    EXPORT_ALL[export_all\nfiltered list]
    BUILD_XLSX[build_xlsx\nopenpyxl]
    XLSX_DL([XLSX download\nbrowser])

    DEL_CONFIRM[confirm_delete_selected\nor confirm_delete_all]
    DO_DELETE[do_delete_selected\nor do_delete_all]
    DELETE_RECORDS[delete_records\ndelete_item per ID]

    %% ── CLI ──────────────────────────────────────────────────────────────────
    CLI_MAIN[main\nargparse]
    SCAN_TABLE[scan_table\npaginated scan + filters]
    DISPLAY_TABLE[display_table\nASCII table terminal]
    EXPORT_XLSX_CLI[export_xlsx\n.xlsx file]
    XLSX_FILE([XLSX file\non disk])

    %% ─────────────────────────────────────────────────────────────────────────
    %% Main Lambda pipeline
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

    JSON_FOUND -- Yes --> NORMALIZE
    JSON_FOUND -- No  --> MANUAL
    MANUAL      --> NORMALIZE
    NORMALIZE   --> VALIDATE
    VALIDATE    --> FIX_SUPPLIER

    FIX_SUPPLIER --> SUPPLIER_FROM_FILENAME
    SUPPLIER_FROM_FILENAME -- Supplier found --> EXTRACT_SUPP
    SUPPLIER_FROM_FILENAME -- No confusion   --> ADD_META
    EXTRACT_SUPP --> ADD_META

    ADD_META  --> SAVE_DDB
    SAVE_DDB  --> CONVERT_DDB
    CONVERT_DDB --> DYNAMO_TABLE

    DYNAMO_TABLE --> LAMBDA_OK
    PROCESS_S3 -- Error --> LAMBDA_ERR

    %% NiceGUI interface
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

    %% UI upload → Lambda
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
