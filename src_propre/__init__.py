"""
Package d'extraction de factures PDF avec AWS Bedrock
"""

__version__ = "1.0.0"
__author__ = "Invoice Extractor Team"

from .main import InvoiceExtractor, lambda_handler
from .pdf_extractor import PDFExtractor
from .bedrock_client import BedrockClient
from .dynamodb_client import DynamoDBClient

__all__ = [
    "InvoiceExtractor",
    "lambda_handler",
    "PDFExtractor",
    "BedrockClient",
    "DynamoDBClient"
]
