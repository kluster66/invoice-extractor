"""
Module d'extraction de texte depuis des fichiers PDF (version simplifiée)
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class PDFExtractorSimple:
    """Classe pour extraire le texte des fichiers PDF (version simplifiée)"""
    
    def __init__(self):
        """Initialise l'extracteur PDF"""
        pass
    
    def extract_text(self, pdf_path: str) -> str:
        """
        Extrait le texte d'un fichier PDF avec PyPDF2 seulement
        
        Args:
            pdf_path: Chemin vers le fichier PDF
            
        Returns:
            Texte extrait du PDF (nettoyé et normalisé)
        """
        try:
            raw_text = self._extract_with_pypdf2(pdf_path)
            cleaned_text = self._clean_extracted_text(raw_text)
            return cleaned_text
        except Exception as e:
            logger.error(f"Erreur lors de l'extraction PDF: {str(e)}")
            raise
    
    def _clean_extracted_text(self, text: str) -> str:
        """
        Nettoie et normalise le texte extrait du PDF
        
        Args:
            text: Texte brut extrait
            
        Returns:
            Texte nettoyé et normalisé
        """
        import re
        
        # Supprimer les caractères de contrôle (sauf \n et \t)
        text = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f-\x9f]', '', text)
        
        # Normaliser les espaces multiples en un seul espace
        text = re.sub(r' +', ' ', text)
        
        # Normaliser les sauts de ligne multiples (max 2)
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # Supprimer les espaces en début et fin de ligne
        lines = [line.strip() for line in text.split('\n')]
        text = '\n'.join(lines)
        
        # Supprimer les lignes vides en début et fin
        text = text.strip()
        
        logger.info(f"Texte nettoyé: {len(text)} caractères")
        return text
    
    def _extract_with_pypdf2(self, pdf_path: str) -> str:
        """
        Extrait le texte avec PyPDF2
        
        Args:
            pdf_path: Chemin vers le fichier PDF
            
        Returns:
            Texte extrait
        """
        text_parts = []
        
        try:
            import PyPDF2
            
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
            
        except ImportError:
            logger.error("PyPDF2 n'est pas installé")
            raise ImportError("PyPDF2 est requis pour l'extraction PDF")
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
            import PyPDF2
            
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
                import PyPDF2
                file.seek(0)
                pdf_reader = PyPDF2.PdfReader(file)
                return len(pdf_reader.pages) > 0
                
        except Exception:
            return False
