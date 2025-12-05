"""
Presidio service for text analysis and sensitive data detection
"""
from typing import List, Dict, Any
import logging
import re
from app.config import settings

logger = logging.getLogger(__name__)

# Try to import Presidio, fallback to simple regex if not available
try:
    from presidio_analyzer import AnalyzerEngine
    from presidio_analyzer.nlp_engine import NlpEngineProvider
    PRESIDIO_AVAILABLE = True
except ImportError:
    PRESIDIO_AVAILABLE = False
    logger.warning("Presidio not available, using simple regex patterns")


class PresidioService:
    """Service for analyzing text and detecting sensitive data using Presidio"""
    
    def __init__(self):
        """Initialize Presidio analyzer"""
        self.supported_entities = settings.PRESIDIO_SUPPORTED_ENTITIES.split(",")
        
        if PRESIDIO_AVAILABLE:
            try:
                # Configure NLP engine
                configuration = {
                    "nlp_engine_name": "spacy",
                    "models": [
                        {"lang_code": settings.PRESIDIO_LANGUAGE, "model_name": "xx_core_web_sm"}
                    ]
                }
                
                provider = NlpEngineProvider(nlp_configuration=configuration)
                nlp_engine = provider.create_engine()
                
                # Create analyzer
                self.analyzer = AnalyzerEngine(
                    nlp_engine=nlp_engine,
                    supported_languages=[settings.PRESIDIO_LANGUAGE, "en"]
                )
                logger.info(f"Presidio service initialized with entities: {self.supported_entities}")
                
            except Exception as e:
                logger.error(f"Error initializing Presidio: {e}")
                # Fallback to simple analyzer
                self.analyzer = None
                logger.info("Using fallback regex patterns")
        else:
            self.analyzer = None
            logger.info("Using fallback regex patterns")
    
    def _analyze_with_regex(self, text: str) -> List[Dict[str, Any]]:
        """Fallback regex-based analysis"""
        detected_entities = []
        
        # Phone number patterns
        phone_pattern = r'\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b'
        for match in re.finditer(phone_pattern, text):
            detected_entities.append({
                "entity_type": "PHONE_NUMBER",
                "start": match.start(),
                "end": match.end(),
                "score": 0.8,
                "value": match.group()
            })
        
        # Email pattern
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        for match in re.finditer(email_pattern, text):
            detected_entities.append({
                "entity_type": "EMAIL_ADDRESS",
                "start": match.start(),
                "end": match.end(),
                "score": 0.9,
                "value": match.group()
            })
        
        # Credit card pattern (simplified)
        cc_pattern = r'\b\d{4}[-.\s]?\d{4}[-.\s]?\d{4}[-.\s]?\d{4}\b'
        for match in re.finditer(cc_pattern, text):
            detected_entities.append({
                "entity_type": "CREDIT_CARD",
                "start": match.start(),
                "end": match.end(),
                "score": 0.7,
                "value": match.group()
            })
        
        return detected_entities
    
    def analyze(self, text: str, language: str = None) -> List[Dict[str, Any]]:
        """
        Analyze text and detect sensitive data
        
        Args:
            text: Text to analyze
            language: Language code (defaults to configured language)
            
        Returns:
            List of detected entities with their positions and confidence scores
        """
        if not text:
            return []
        
        # Use Presidio if available
        if self.analyzer is not None:
            try:
                language = language or settings.PRESIDIO_LANGUAGE
                
                # Analyze text
                results = self.analyzer.analyze(
                    text=text,
                    language=language,
                    entities=self.supported_entities
                )
                
                # Format results
                detected_entities = []
                for result in results:
                    detected_entities.append({
                        "entity_type": result.entity_type,
                        "start": result.start,
                        "end": result.end,
                        "score": result.score,
                        "value": text[result.start:result.end]
                    })
                
                logger.info(f"Detected {len(detected_entities)} entities in text")
                return detected_entities
                
            except Exception as e:
                logger.error(f"Error analyzing text with Presidio: {e}, using fallback")
        
        # Fallback to regex
        detected_entities = self._analyze_with_regex(text)
        logger.info(f"Detected {len(detected_entities)} entities using regex patterns")
        return detected_entities
    
    def get_supported_entities(self) -> List[str]:
        """
        Get list of supported entity types
        
        Returns:
            List of supported entity type names
        """
        return self.supported_entities
    
    def is_sensitive(self, text: str, threshold: float = 0.5) -> bool:
        """
        Check if text contains sensitive data
        
        Args:
            text: Text to check
            threshold: Minimum confidence score to consider as sensitive
            
        Returns:
            True if sensitive data detected, False otherwise
        """
        entities = self.analyze(text)
        return any(entity["score"] >= threshold for entity in entities)
    
    def get_supported_entities(self) -> List[str]:
        """
        Get list of supported entity types
        
        Returns:
            List of supported entity type names
        """
        return self.supported_entities

