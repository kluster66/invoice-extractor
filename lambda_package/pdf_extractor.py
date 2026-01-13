#!/usr/bin/env python3
"""
Module d'extraction de texte depuis des fichiers PDF
Version simplifiée pour Lambda (PyPDF2 uniquement)
"""

import logging
from typing import Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class PDFExtractor:
    """Extracteur de texte PDF utilisant PyPDF2"""
    
    def __init__(self):
        """Initialise l'extracteur PDF"""
        try:
            import PyPDF2
            self.PyPDF2 = PyPDF2
            logger.info("PyPDF2 importé avec succès")
        except ImportError as e:
            logger.error(f"Impossible d'importer PyPDF2: {e}")
            raise
    
    def extract_text(self, pdf_path: str) -> Optional[str]:
        """
        Extrait le texte d'un fichier PDF
        
        Args:
            pdf_path: Chemin vers le fichier PDF
            
        Returns:
            Texte extrait ou None en cas d'erreur
        """
        try:
            logger.info(f"Extraction du texte depuis: {pdf_path}")
            
            # Vérifier que le fichier existe
            if not Path(pdf_path).exists():
                logger.error(f"Fichier non trouvé: {pdf_path}")
                return None
            
            # Ouvrir le fichier PDF
            with open(pdf_path, 'rb') as file:
                # Créer un lecteur PDF
                pdf_reader = self.PyPDF2.PdfReader(file)
                
                # Extraire le texte de toutes les pages
                text_parts = []
                for page_num in range(len(pdf_reader.pages)):
                    try:
                        page = pdf_reader.pages[page_num]
                        page_text = page.extract_text()
                        if page_text:
                            text_parts.append(page_text)
                    except Exception as page_error:
                        logger.warning(f"Erreur sur la page {page_num}: {page_error}")
                        continue
                
                # Combiner tout le texte
                full_text = "\n".join(text_parts)
                
                if not full_text.strip():
                    logger.warning(f"Aucun texte extrait du PDF: {pdf_path}")
                    return None
                
                logger.info(f"Texte extrait avec succès ({len(full_text)} caractères)")
                return full_text
                
        except Exception as e:
            logger.error(f"Erreur lors de l'extraction PDF: {str(e)}")
            return None
    
    def extract_text_from_bytes(self, pdf_bytes: bytes) -> Optional[str]:
        """
        Extrait le texte depuis des bytes PDF
        
        Args:
            pdf_bytes: Contenu PDF en bytes
            
        Returns:
            Texte extrait ou None en cas d'erreur
        """
        try:
            logger.info("Extraction du texte depuis bytes PDF")
            
            # Créer un lecteur PDF depuis les bytes
            import io
            pdf_stream = io.BytesIO(pdf_bytes)
            pdf_reader = self.PyPDF2.PdfReader(pdf_stream)
            
            # Extraire le texte de toutes les pages
            text_parts = []
            for page_num in range(len(pdf_reader.pages)):
                try:
                    page = pdf_reader.pages[page_num]
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)
                except Exception as page_error:
                    logger.warning(f"Erreur sur la page {page_num}: {page_error}")
                    continue
            
            # Combiner tout le texte
            full_text = "\n".join(text_parts)
            
            if not full_text.strip():
                logger.warning("Aucun texte extrait des bytes PDF")
                return None
            
            logger.info(f"Texte extrait avec succès ({len(full_text)} caractères)")
            return full_text
            
        except Exception as e:
            logger.error(f"Erreur lors de l'extraction PDF depuis bytes: {str(e)}")
            return None
