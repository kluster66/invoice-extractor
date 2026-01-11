"""
Module d'extraction de texte depuis des fichiers PDF
"""

import logging
from typing import Optional
import PyPDF2
import pdfplumber

logger = logging.getLogger(__name__)


class PDFExtractor:
    """Classe pour extraire le texte des fichiers PDF"""
    
    def __init__(self):
        """Initialise l'extracteur PDF"""
        self.use_pdfplumber = True  # pdfplumber est généralement meilleur
    
    def extract_text(self, pdf_path: str) -> str:
        """
        Extrait le texte d'un fichier PDF
        
        Args:
            pdf_path: Chemin vers le fichier PDF
            
        Returns:
            Texte extrait du PDF
        """
        try:
            if self.use_pdfplumber:
                return self._extract_with_pdfplumber(pdf_path)
            else:
                return self._extract_with_pypdf2(pdf_path)
        except Exception as e:
            logger.error(f"Erreur lors de l'extraction PDF: {str(e)}")
            raise
    
    def _extract_with_pdfplumber(self, pdf_path: str) -> str:
        """
        Extrait le texte avec pdfplumber (meilleur pour les tableaux)
        
        Args:
            pdf_path: Chemin vers le fichier PDF
            
        Returns:
            Texte extrait
        """
        text_parts = []
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    try:
                        page_text = page.extract_text()
                        if page_text:
                            text_parts.append(f"--- Page {page_num} ---\n{page_text}")
                        else:
                            # Essayer l'extraction avec une méthode différente
                            page_text = page.extract_text(x_tolerance=3, y_tolerance=3)
                            if page_text:
                                text_parts.append(f"--- Page {page_num} (alternative) ---\n{page_text}")
                    except Exception as page_error:
                        logger.warning(f"Erreur sur la page {page_num}: {str(page_error)}")
                        continue
            
            if not text_parts:
                logger.warning("Aucun texte extrait avec pdfplumber, tentative avec PyPDF2")
                return self._extract_with_pypdf2(pdf_path)
            
            return "\n\n".join(text_parts)
            
        except Exception as e:
            logger.error(f"Erreur pdfplumber: {str(e)}")
            # Fallback sur PyPDF2
            return self._extract_with_pypdf2(pdf_path)
    
    def _extract_with_pypdf2(self, pdf_path: str) -> str:
        """
        Extrait le texte avec PyPDF2 (fallback)
        
        Args:
            pdf_path: Chemin vers le fichier PDF
            
        Returns:
            Texte extrait
        """
        text_parts = []
        
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                
                for page_num in range(len(pdf_reader.pages)):
                    try:
                        page = pdf_reader.pages[page_num]
                        page_text = page.extract_text()
                        if page_text:
                            text_parts.append(f"--- Page {page_num + 1} ---\n{page_text}")
                    except Exception as page_error:
                        logger.warning(f"Erreur sur la page {page_num + 1}: {str(page_error)}")
                        continue
            
            if not text_parts:
                raise ValueError("Impossible d'extraire du texte du PDF")
            
            return "\n\n".join(text_parts)
            
        except Exception as e:
            logger.error(f"Erreur PyPDF2: {str(e)}")
            raise
    
    def extract_metadata(self, pdf_path: str) -> dict:
        """
        Extrait les métadonnées du PDF
        
        Args:
            pdf_path: Chemin vers le fichier PDF
            
        Returns:
            Métadonnées du PDF
        """
        metadata = {}
        
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                
                if pdf_reader.metadata:
                    for key, value in pdf_reader.metadata.items():
                        if value:
                            # Nettoyer les clés (enlever le préfixe '/')
                            clean_key = key.replace('/', '') if key.startswith('/') else key
                            metadata[clean_key] = str(value)
                
                metadata["num_pages"] = len(pdf_reader.pages)
                
        except Exception as e:
            logger.warning(f"Erreur lors de l'extraction des métadonnées: {str(e)}")
        
        return metadata
    
    def validate_pdf(self, pdf_path: str) -> bool:
        """
        Valide qu'un fichier est un PDF valide
        
        Args:
            pdf_path: Chemin vers le fichier
            
        Returns:
            True si le PDF est valide
        """
        try:
            with open(pdf_path, 'rb') as file:
                # Vérifier le header PDF
                header = file.read(5)
                if header != b'%PDF-':
                    return False
                
                # Essayer de lire le PDF
                file.seek(0)
                pdf_reader = PyPDF2.PdfReader(file)
                return len(pdf_reader.pages) > 0
                
        except Exception:
            return False
