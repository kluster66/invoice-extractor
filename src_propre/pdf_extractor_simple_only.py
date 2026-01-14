"""
Extracteur PDF simplifié utilisant seulement PyPDF2 (pas de dépendances C)
"""

import logging
from typing import Optional
import PyPDF2

logger = logging.getLogger(__name__)


class PDFExtractorSimple:
    """Extracteur PDF utilisant seulement PyPDF2"""
    
    def extract_text(self, pdf_path: str) -> Optional[str]:
        """
        Extrait le texte d'un fichier PDF en utilisant PyPDF2
        
        Args:
            pdf_path: Chemin vers le fichier PDF
            
        Returns:
            Texte extrait ou None en cas d'erreur
        """
        try:
            logger.info(f"Extraction du texte avec PyPDF2: {pdf_path}")
            
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                
                # Vérifier si le PDF est chiffré
                if pdf_reader.is_encrypted:
                    logger.warning("PDF chiffré détecté, tentative de déchiffrement...")
                    try:
                        # Essayer avec un mot de passe vide (certains PDFs sont chiffrés sans mot de passe)
                        pdf_reader.decrypt('')
                    except:
                        logger.error("Impossible de déchiffrer le PDF")
                        return None
                
                # Extraire le texte de toutes les pages
                text_parts = []
                for page_num, page in enumerate(pdf_reader.pages):
                    try:
                        page_text = page.extract_text()
                        if page_text:
                            text_parts.append(page_text)
                        else:
                            logger.warning(f"Page {page_num + 1}: Aucun texte extrait")
                    except Exception as e:
                        logger.warning(f"Page {page_num + 1}: Erreur d'extraction: {e}")
                
                if not text_parts:
                    logger.error("Aucun texte extrait du PDF")
                    return None
                
                full_text = "\n".join(text_parts)
                logger.info(f"Texte extrait: {len(full_text)} caractères, {len(pdf_reader.pages)} pages")
                
                return full_text
                
        except Exception as e:
            logger.error(f"Erreur lors de l'extraction PDF avec PyPDF2: {str(e)}")
            return None
    
    def test_extraction(self, pdf_path: str) -> bool:
        """
        Teste l'extraction d'un PDF
        
        Args:
            pdf_path: Chemin vers le fichier PDF
            
        Returns:
            True si l'extraction réussit
        """
        try:
            text = self.extract_text(pdf_path)
            if text and len(text) > 0:
                logger.info(f"Test réussi: {len(text)} caractères extraits")
                return True
            else:
                logger.error("Test échoué: aucun texte extrait")
                return False
        except Exception as e:
            logger.error(f"Test échoué: {str(e)}")
            return False
