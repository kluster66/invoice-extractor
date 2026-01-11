"""
Tests pour l'extracteur de factures
"""

import pytest
import json
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from src.main import InvoiceExtractor
from src.pdf_extractor import PDFExtractor
from src.bedrock_client import BedrockClient
from src.dynamodb_client import DynamoDBClient


class TestPDFExtractor:
    """Tests pour l'extracteur PDF"""
    
    def test_extract_text_success(self):
        """Test d'extraction de texte réussie"""
        extractor = PDFExtractor()
        
        # Créer un fichier PDF factice pour le test
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
            # Écrire un header PDF minimal
            tmp.write(b'%PDF-1.4\n')
            tmp.write(b'1 0 obj\n')
            tmp.write(b'<< /Type /Catalog /Pages 2 0 R >>\n')
            tmp.write(b'endobj\n')
            tmp.write(b'2 0 obj\n')
            tmp.write(b'<< /Type /Pages /Kids [] /Count 0 >>\n')
            tmp.write(b'endobj\n')
            tmp.write(b'xref\n')
            tmp.write(b'0 3\n')
            tmp.write(b'0000000000 65535 f\n')
            tmp.write(b'0000000010 00000 n\n')
            tmp.write(b'0000000050 00000 n\n')
            tmp.write(b'trailer\n')
            tmp.write(b'<< /Size 3 /Root 1 0 R >>\n')
            tmp.write(b'startxref\n')
            tmp.write(b'100\n')
            tmp.write(b'%%EOF\n')
            tmp_path = tmp.name
        
        try:
            # Tester l'extraction
            text = extractor.extract_text(tmp_path)
            assert isinstance(text, str)
        finally:
            # Nettoyer
            os.unlink(tmp_path)
    
    def test_extract_text_file_not_found(self):
        """Test avec fichier non trouvé"""
        extractor = PDFExtractor()
        
        with pytest.raises(Exception):
            extractor.extract_text("/chemin/inexistant/facture.pdf")
    
    def test_validate_pdf_valid(self):
        """Test de validation PDF valide"""
        extractor = PDFExtractor()
        
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
            tmp.write(b'%PDF-1.4\n%%EOF\n')
            tmp_path = tmp.name
        
        try:
            assert extractor.validate_pdf(tmp_path) is True
        finally:
            os.unlink(tmp_path)
    
    def test_validate_pdf_invalid(self):
        """Test de validation PDF invalide"""
        extractor = PDFExtractor()
        
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as tmp:
            tmp.write(b'Ceci est un texte, pas un PDF\n')
            tmp_path = tmp.name
        
        try:
            assert extractor.validate_pdf(tmp_path) is False
        finally:
            os.unlink(tmp_path)


class TestBedrockClient:
    """Tests pour le client Bedrock"""
    
    @patch('boto3.client')
    def test_extract_invoice_data_success(self, mock_boto_client):
        """Test d'extraction réussie avec Bedrock"""
        # Mock de la réponse Bedrock
        mock_response = {
            'body': Mock(read=Mock(return_value=json.dumps({
                'content': [{'text': '{"fournisseur": "Test Corp", "montant_ht": 1000.0}'}]
            }).encode('utf-8')))
        }
        
        mock_bedrock = Mock()
        mock_bedrock.invoke_model.return_value = mock_response
        mock_boto_client.return_value = mock_bedrock
        
        client = BedrockClient()
        prompt = "Test prompt"
        
        result = client.extract_invoice_data(prompt)
        
        assert isinstance(result, dict)
        assert "fournisseur" in result
        assert result["fournisseur"] == "Test Corp"
        assert result["montant_ht"] == 1000.0
    
    @patch('boto3.client')
    def test_extract_invoice_data_empty_response(self, mock_boto_client):
        """Test avec réponse vide de Bedrock"""
        mock_response = {
            'body': Mock(read=Mock(return_value=json.dumps({
                'content': []
            }).encode('utf-8')))
        }
        
        mock_bedrock = Mock()
        mock_bedrock.invoke_model.return_value = mock_response
        mock_boto_client.return_value = mock_bedrock
        
        client = BedrockClient()
        
        with pytest.raises(ValueError, match="Réponse vide"):
            client.extract_invoice_data("Test prompt")
    
    def test_clean_json_response(self):
        """Test de nettoyage de réponse JSON"""
        client = BedrockClient()
        
        # Test avec backticks
        response = '```json\n{"test": "value"}\n```'
        cleaned = client._clean_json_response(response)
        assert cleaned == '{"test": "value"}'
        
        # Test sans backticks
        response = '{"test": "value"}'
        cleaned = client._clean_json_response(response)
        assert cleaned == '{"test": "value"}'
    
    def test_extract_json_from_text(self):
        """Test d'extraction JSON depuis texte"""
        client = BedrockClient()
        
        text = 'Voici du texte avant {"key": "value"} et après'
        extracted = client._extract_json_from_text(text)
        assert extracted == '{"key": "value"}'
        
        # Test avec JSON invalide
        text = 'Pas de JSON ici'
        with pytest.raises(ValueError, match="Aucun JSON trouvé"):
            client._extract_json_from_text(text)


class TestDynamoDBClient:
    """Tests pour le client DynamoDB"""
    
    @patch('boto3.client')
    @patch('boto3.resource')
    def test_save_invoice_data(self, mock_resource, mock_client):
        """Test de sauvegarde dans DynamoDB"""
        # Mock DynamoDB
        mock_dynamo = Mock()
        mock_client.return_value = mock_dynamo
        
        mock_table = Mock()
        mock_resource.return_value = mock_table
        
        client = DynamoDBClient()
        
        # Données de test
        invoice_data = {
            "fournisseur": "Test Corp",
            "montant_ht": 1000.0,
            "numero_facture": "TEST-001",
            "filename": "test.pdf"
        }
        
        # Appeler la méthode
        invoice_id = client.save_invoice_data(invoice_data)
        
        # Vérifications
        assert isinstance(invoice_id, str)
        assert len(invoice_id) == 36  # UUID v4
        mock_dynamo.put_item.assert_called_once()
    
    @patch('boto3.client')
    def test_get_invoice(self, mock_client):
        """Test de récupération depuis DynamoDB"""
        # Mock DynamoDB response
        mock_dynamo = Mock()
        mock_client.return_value = mock_dynamo
        
        mock_response = {
            'Item': {
                'invoice_id': {'S': 'test-id'},
                'fournisseur': {'S': 'Test Corp'},
                'raw_data': {'S': '{"test": "data"}'}
            }
        }
        
        mock_dynamo.get_item.return_value = mock_response
        
        client = DynamoDBClient()
        result = client.get_invoice('test-id')
        
        assert result is not None
        assert result['invoice_id'] == 'test-id'
        assert result['fournisseur'] == 'Test Corp'
        assert 'parsed_data' in result
    
    @patch('boto3.client')
    def test_get_invoice_not_found(self, mock_client):
        """Test de récupération avec facture non trouvée"""
        mock_dynamo = Mock()
        mock_client.return_value = mock_dynamo
        
        mock_response = {}
        mock_dynamo.get_item.return_value = mock_response
        
        client = DynamoDBClient()
        result = client.get_invoice('non-existent-id')
        
        assert result is None


class TestInvoiceExtractor:
    """Tests pour l'extracteur principal"""
    
    @patch.object(PDFExtractor, 'extract_text')
    @patch.object(BedrockClient, 'extract_invoice_data')
    def test_extract_from_pdf_success(self, mock_bedrock, mock_pdf):
        """Test d'extraction complète réussie"""
        # Mock PDF extraction
        mock_pdf.return_value = "Texte extrait du PDF"
        
        # Mock Bedrock response
        mock_bedrock.return_value = {
            "fournisseur": "Test Corp",
            "montant_ht": 1000.0,
            "numero_facture": "TEST-001"
        }
        
        extractor = InvoiceExtractor()
        result = extractor.extract_from_pdf("/chemin/facture.pdf", "facture.pdf")
        
        assert isinstance(result, dict)
        assert "fournisseur" in result
        assert "filename" in result
        assert "extraction_date" in result
        assert result["filename"] == "facture.pdf"
    
    @patch.object(PDFExtractor, 'extract_text')
    def test_extract_from_pdf_empty_text(self, mock_pdf):
        """Test avec PDF vide"""
        mock_pdf.return_value = ""
        
        extractor = InvoiceExtractor()
        
        with pytest.raises(ValueError, match="Aucun texte extrait"):
            extractor.extract_from_pdf("/chemin/facture.pdf", "facture.pdf")
    
    def test_create_prompt(self):
        """Test de création du prompt"""
        extractor = InvoiceExtractor()
        
        pdf_text = "Texte de facture"
        filename = "facture.pdf"
        
        prompt = extractor._create_prompt(pdf_text, filename)
        
        assert pdf_text in prompt
        assert filename in prompt
        assert "expert comptable" in prompt
        assert "JSON strict" in prompt


class TestIntegration:
    """Tests d'intégration"""
    
    @patch('boto3.client')
    @patch.object(PDFExtractor, 'extract_text')
    @patch.object(BedrockClient, 'extract_invoice_data')
    @patch.object(DynamoDBClient, 'save_invoice_data')
    def test_full_integration(self, mock_dynamo_save, mock_bedrock, mock_pdf, mock_boto):
        """Test d'intégration complète"""
        # Setup mocks
        mock_pdf.return_value = "Texte facture"
        mock_bedrock.return_value = {
            "fournisseur": "Intégration Test",
            "montant_ht": 2000.0,
            "numero_facture": "INT-001"
        }
        mock_dynamo_save.return_value = "test-uuid"
        
        # Mock S3 download
        mock_s3 = Mock()
        mock_boto.return_value = mock_s3
        
        # Créer un fichier temporaire pour le test
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
            tmp.write(b'%PDF-1.4\n')
            tmp_path = tmp.name
        
        try:
            # Simuler un événement S3
            event = {
                "Records": [{
                    "s3": {
                        "bucket": {"name": "test-bucket"},
                        "object": {"key": "invoices/facture.pdf"}
                    }
                }]
            }
            
            extractor = InvoiceExtractor()
            result = extractor.process_s3_event(event)
            
            # Vérifications
            assert result["statusCode"] == 200
            body = json.loads(result["body"])
            assert body["message"] == "Facture traitée avec succès"
            assert body["invoice_id"] == "test-uuid"
            
        finally:
            # Nettoyer
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
    
    @patch('boto3.client')
    def test_s3_event_processing_error(self, mock_boto):
        """Test de traitement d'événement S3 avec erreur"""
        # Mock S3 pour lever une exception
        mock_s3 = Mock()
        mock_s3.download_file.side_effect = Exception("Erreur S3")
        mock_boto.return_value = mock_s3
        
        event = {
            "Records": [{
                "s3": {
                    "bucket": {"name": "test-bucket"},
                    "object": {"key": "invoices/facture.pdf"}
                }
            }]
        }
        
        extractor = InvoiceExtractor()
        result = extractor.process_s3_event(event)
        
        assert result["statusCode"] == 500
        body = json.loads(result["body"])
        assert "error" in body
        assert body["message"] == "Erreur lors du traitement de la facture"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
