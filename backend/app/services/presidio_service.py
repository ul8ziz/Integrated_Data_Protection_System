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
                # Try to use installed model, fallback to None if not found
                try:
                    import spacy
                    if not spacy.util.is_package("en_core_web_sm"):
                        if spacy.util.is_package("xx_core_web_sm"):
                            model_name = "xx_core_web_sm"
                        else:
                            # No model found, force fallback
                            raise OSError("No spacy model found")
                    else:
                        model_name = "en_core_web_sm"
                except (ImportError, OSError):
                    # Spacy model not found - this is expected in some environments
                    # Will use regex fallback instead
                    raise

                configuration = {
                    "nlp_engine_name": "spacy",
                    "models": [
                        {"lang_code": settings.PRESIDIO_LANGUAGE, "model_name": model_name},
                        {"lang_code": "en", "model_name": model_name}
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
                # Presidio initialization failed (likely missing Spacy models)
                # This is expected and handled gracefully with regex fallback
                self.analyzer = None
                logger.info(f"Presidio not available (missing Spacy models). Using regex fallback for entity detection.")
        else:
            self.analyzer = None
            logger.info("Presidio not installed. Using regex fallback for entity detection.")
    
    def _detect_malicious_scripts(self, text: str) -> List[Dict[str, Any]]:
        """
        Detect malicious scripts and code injection patterns
        
        Args:
            text: Text to analyze
            
        Returns:
            List of detected malicious script entities
        """
        detected_scripts = []
        text_lower = text.lower()
        
        # JavaScript patterns
        js_patterns = [
            (r'<script[^>]*>.*?</script>', 'JavaScript script tag', 0.95),
            (r'javascript\s*:', 'JavaScript protocol', 0.9),
            (r'eval\s*\(', 'JavaScript eval()', 0.9),
            (r'Function\s*\(', 'JavaScript Function()', 0.85),
            (r'setTimeout\s*\(.*?["\']', 'JavaScript setTimeout with string', 0.8),
            (r'setInterval\s*\(.*?["\']', 'JavaScript setInterval with string', 0.8),
            (r'document\.(write|writeln|cookie)', 'JavaScript DOM manipulation', 0.85),
            (r'window\.(location|open)', 'JavaScript window manipulation', 0.8),
            (r'innerHTML\s*=', 'JavaScript innerHTML injection', 0.85),
        ]
        
        # Python patterns
        python_patterns = [
            (r'exec\s*\(', 'Python exec()', 0.9),
            (r'eval\s*\(', 'Python eval()', 0.9),
            (r'__import__\s*\(', 'Python __import__()', 0.85),
            (r'compile\s*\(', 'Python compile()', 0.8),
            (r'__builtins__', 'Python builtins access', 0.75),
        ]
        
        # Shell/Command injection patterns
        shell_patterns = [
            (r'bash\s+-c\s+["\']', 'Bash command execution', 0.9),
            (r'sh\s+-c\s+["\']', 'Shell command execution', 0.9),
            (r'cmd\s+/c\s+', 'Windows CMD execution', 0.9),
            (r'powershell\s+-Command', 'PowerShell execution', 0.85),
            (r'`[^`]*`', 'Backtick command substitution', 0.7),
            (r'\$\s*\([^)]+\)', 'Command substitution $()', 0.7),
        ]
        
        # SQL Injection patterns
        sql_patterns = [
            (r"'\s*OR\s*['\"]?\s*1\s*=\s*1", 'SQL injection OR 1=1', 0.95),
            (r"'\s*OR\s*['\"]?\s*'['\"]?\s*=\s*['\"]", 'SQL injection OR condition', 0.9),
            (r'UNION\s+SELECT', 'SQL UNION SELECT', 0.95),
            (r'DROP\s+TABLE', 'SQL DROP TABLE', 0.9),
            (r'DELETE\s+FROM', 'SQL DELETE', 0.85),
            (r'INSERT\s+INTO', 'SQL INSERT', 0.8),
            (r';\s*--', 'SQL comment injection', 0.75),
        ]
        
        # XSS patterns
        xss_patterns = [
            (r'<img[^>]*onerror\s*=', 'XSS img onerror', 0.95),
            (r'<img[^>]*onload\s*=', 'XSS img onload', 0.9),
            (r'onclick\s*=\s*["\']', 'XSS onclick', 0.9),
            (r'onmouseover\s*=\s*["\']', 'XSS onmouseover', 0.85),
            (r'onfocus\s*=\s*["\']', 'XSS onfocus', 0.85),
            (r'<iframe[^>]*src\s*=', 'XSS iframe', 0.8),
            (r'<svg[^>]*onload\s*=', 'XSS SVG onload', 0.9),
        ]
        
        # Combine all patterns
        all_patterns = (
            [('js', p) for p in js_patterns] +
            [('python', p) for p in python_patterns] +
            [('shell', p) for p in shell_patterns] +
            [('sql', p) for p in sql_patterns] +
            [('xss', p) for p in xss_patterns]
        )
        
        # Search for patterns
        for script_type, (pattern, description, score) in all_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE | re.DOTALL):
                detected_scripts.append({
                    "entity_type": "MALICIOUS_SCRIPT",
                    "start": match.start(),
                    "end": match.end(),
                    "score": score,
                    "value": match.group()[:100],  # Limit value length
                    "script_type": script_type,
                    "description": description
                })
        
        return detected_scripts
    
    def _analyze_with_regex(self, text: str) -> List[Dict[str, Any]]:
        """Fallback regex-based analysis"""
        detected_entities = []
        
        # Phone number patterns (supports various formats)
        # Pattern 1: "Phone:" or "الهاتف:" followed by phone
        phone_labeled_pattern = r'(?:Phone|الهاتف|رقم الهاتف)\s*:?\s*([^\n]{7,20})'
        for match in re.finditer(phone_labeled_pattern, text, re.IGNORECASE):
            phone_value = match.group(1).strip()
            # Remove trailing parentheses
            phone_value = re.sub(r'\s*\([^)]*\).*$', '', phone_value).strip()
            # Extract just the phone number part
            phone_match = re.search(r'[\d\s\-+()]{7,20}', phone_value)
            if phone_match:
                phone_value = phone_match.group().strip()
                detected_entities.append({
                    "entity_type": "PHONE_NUMBER",
                    "start": match.start(1) + phone_match.start(),
                    "end": match.start(1) + phone_match.end(),
                    "score": 0.9,
                    "value": phone_value
                })
        
        # Pattern 2: Standalone phone numbers
        phone_pattern = r'\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{2,4}\)?[-.\s]?\d{2,4}[-.\s]?\d{2,4}[-.\s]?\d{2,7}\b'
        for match in re.finditer(phone_pattern, text):
            # Skip if it's part of credit card or IBAN
            value = match.group()
            if not re.match(r'^\d{4}[-.\s]?\d{4}[-.\s]?\d{4}[-.\s]?\d{4}$', value):  # Not credit card
                detected_entities.append({
                    "entity_type": "PHONE_NUMBER",
                    "start": match.start(),
                    "end": match.end(),
                    "score": 0.8,
                    "value": value
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
        
        # Credit card pattern (16 digits with optional separators)
        # Pattern 1: "Credit Card:" or "البطاقة:" followed by card number
        cc_labeled_pattern = r'(?:Credit Card|البطاقة|رقم البطاقة)\s*:?\s*([^\n]{15,25})'
        for match in re.finditer(cc_labeled_pattern, text, re.IGNORECASE):
            cc_value = match.group(1).strip()
            # Remove trailing parentheses
            cc_value = re.sub(r'\s*\([^)]*\).*$', '', cc_value).strip()
            # Extract just the card number part
            cc_match = re.search(r'\d{4}[-.\s]?\d{4}[-.\s]?\d{4}[-.\s]?\d{4}', cc_value)
            if cc_match:
                detected_entities.append({
                    "entity_type": "CREDIT_CARD",
                    "start": match.start(1) + cc_match.start(),
                    "end": match.start(1) + cc_match.end(),
                    "score": 0.85,
                    "value": cc_match.group()
                })
        
        # Pattern 2: Standalone credit card numbers
        cc_pattern = r'\b\d{4}[-.\s]?\d{4}[-.\s]?\d{4}[-.\s]?\d{4}\b'
        for match in re.finditer(cc_pattern, text):
            detected_entities.append({
                "entity_type": "CREDIT_CARD",
                "start": match.start(),
                "end": match.end(),
                "score": 0.7,
                "value": match.group()
            })
        
        # IP Address pattern (IPv4)
        # Pattern 1: "IP:" or "الآيبي:" followed by IP
        ip_labeled_pattern = r'(?:IP|الآيبي|عنوان الآيبي)\s*:?\s*([^\n]{7,20})'
        for match in re.finditer(ip_labeled_pattern, text, re.IGNORECASE):
            ip_value = match.group(1).strip()
            # Remove trailing parentheses
            ip_value = re.sub(r'\s*\([^)]*\).*$', '', ip_value).strip()
            # Extract IP address
            ip_match = re.search(r'(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)', ip_value)
            if ip_match:
                detected_entities.append({
                    "entity_type": "IP_ADDRESS",
                    "start": match.start(1) + ip_match.start(),
                    "end": match.start(1) + ip_match.end(),
                    "score": 0.9,
                    "value": ip_match.group()
                })
        
        # Pattern 2: Standalone IP addresses
        ip_pattern = r'\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b'
        for match in re.finditer(ip_pattern, text):
            # Skip if it's part of email or other context
            value = match.group()
            context_start = max(0, match.start() - 10)
            context_end = min(len(text), match.end() + 10)
            context = text[context_start:context_end]
            if '@' not in context:  # Not part of email
                detected_entities.append({
                    "entity_type": "IP_ADDRESS",
                    "start": match.start(),
                    "end": match.end(),
                    "score": 0.85,
                    "value": value
                })
        
        # IBAN Code pattern (2 letters + 2 digits + up to 30 alphanumeric)
        # Pattern 1: "IBAN:" or "الآيبان:" followed by IBAN
        iban_labeled_pattern = r'(?:IBAN|الآيبان|رقم الآيبان)\s*:?\s*([A-Z0-9\s]{15,35})'
        for match in re.finditer(iban_labeled_pattern, text, re.IGNORECASE):
            iban_value = match.group(1).strip()
            # Remove trailing parentheses and spaces
            iban_value = re.sub(r'\s*\([^)]*\).*$', '', iban_value).strip().replace(' ', '')
            # Basic IBAN validation (length should be between 15-34)
            if 15 <= len(iban_value) <= 34 and re.match(r'^[A-Z]{2}\d{2}[A-Z0-9]+$', iban_value):
                detected_entities.append({
                    "entity_type": "IBAN_CODE",
                    "start": match.start(1),
                    "end": match.end(1),
                    "score": 0.85,
                    "value": iban_value
                })
        
        # Pattern 2: Standalone IBAN codes
        iban_pattern = r'\b[A-Z]{2}\d{2}[A-Z0-9]{4,30}\b'
        for match in re.finditer(iban_pattern, text):
            value = match.group()
            # Basic IBAN validation (length should be between 15-34)
            if 15 <= len(value) <= 34:
                detected_entities.append({
                    "entity_type": "IBAN_CODE",
                    "start": match.start(),
                    "end": match.end(),
                    "score": 0.75,
                    "value": value
                })
        
        # US SSN pattern (XXX-XX-XXXX or XXX XX XXXX)
        ssn_pattern = r'\b\d{3}[-.\s]?\d{2}[-.\s]?\d{4}\b'
        for match in re.finditer(ssn_pattern, text):
            value = match.group()
            # Skip if it's part of date or phone
            if not re.search(r'\d{4}[-.\s]?\d{2}[-.\s]?\d{2}', text[max(0, match.start()-5):match.end()+5]):  # Not date
                detected_entities.append({
                    "entity_type": "US_SSN",
                    "start": match.start(),
                    "end": match.end(),
                    "score": 0.8,
                    "value": value
                })
        
        # Date/Time patterns (various formats)
        # Arabic dates: 15 يناير 2024, 15/01/2024
        # English dates: January 15, 2024, 01/15/2024, 2024-01-15
        # Pattern 1: "Date:" or "التاريخ:" followed by date
        date_labeled_pattern = rf'(?:Date|التاريخ|الوقت)\s*:?\s*([^\n]{5,50})'
        for match in re.finditer(date_labeled_pattern, text, re.IGNORECASE):
            date_value = match.group(1).strip()
            # Remove trailing parentheses
            date_value = re.sub(r'\s*\([^)]*\).*$', '', date_value).strip()
            if len(date_value) >= 5:
                detected_entities.append({
                    "entity_type": "DATE_TIME",
                    "start": match.start(1),
                    "end": match.end(1),
                    "score": 0.85,
                    "value": date_value
                })
        
        # Pattern 2: Various date formats
        date_patterns = [
            (r'\b\d{1,2}\s+(?:يناير|فبراير|مارس|أبريل|مايو|يونيو|يوليو|أغسطس|سبتمبر|أكتوبر|نوفمبر|ديسمبر)\s+\d{4}\b', 'ar_date'),
            (r'\b(?:يناير|فبراير|مارس|أبريل|مايو|يونيو|يوليو|أغسطس|سبتمبر|أكتوبر|نوفمبر|ديسمبر)\s+\d{1,2},?\s+\d{4}\b', 'ar_date'),
            (r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b', 'date'),
            (r'\b\d{4}[/-]\d{1,2}[/-]\d{1,2}\b', 'date'),
            (r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}\b', 'en_date'),
            (r'\b\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}\b', 'en_date'),
            (r'\b\d{1,2}:\d{2}(?::\d{2})?\s*(?:AM|PM|am|pm)?\b', 'time'),
            (r'\b\d{4}[/-]\d{1,2}[/-]\d{1,2}\s+\d{1,2}:\d{2}(?::\d{2})?\b', 'datetime'),
        ]
        for pattern, pattern_type in date_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                detected_entities.append({
                    "entity_type": "DATE_TIME",
                    "start": match.start(),
                    "end": match.end(),
                    "score": 0.75,
                    "value": match.group()
                })
        
        # Address patterns (look for common address indicators)
        # Arabic: شارع، طريق، حي، مدينة
        # English: Street, Avenue, Road, City, State
        address_keywords_ar = r'(?:شارع|طريق|حي|مدينة|مبنى|مكتب|ص\.ب|صندوق بريد|Address|العنوان)'
        address_keywords_en = r'(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Lane|Ln|Drive|Dr|City|State|Zip|Postal Code|Address)'
        # Pattern 1: "Address:" or "العنوان:" followed by address
        address_labeled_pattern = rf'(?:Address|العنوان)\s*:?\s*([^\n]{10,100})'
        for match in re.finditer(address_labeled_pattern, text, re.IGNORECASE):
            address_value = match.group(1).strip()
            # Remove trailing parentheses and extra info
            address_value = re.sub(r'\s*\([^)]*\).*$', '', address_value).strip()
            if len(address_value) >= 10 and '@' not in address_value:
                detected_entities.append({
                    "entity_type": "ADDRESS",
                    "start": match.start(1),
                    "end": match.end(1),
                    "score": 0.85,
                    "value": address_value
                })
        
        # Pattern 2: Keyword followed by address text
        address_pattern = rf'(?:{address_keywords_ar}|{address_keywords_en})\s*:?\s*([^\n,]{10,80})'
        for match in re.finditer(address_pattern, text, re.IGNORECASE):
            address_value = match.group(1).strip()
            # Remove trailing parentheses
            address_value = re.sub(r'\s*\([^)]*\).*$', '', address_value).strip()
            if len(address_value) >= 10 and '@' not in address_value and not re.search(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', address_value):
                detected_entities.append({
                    "entity_type": "ADDRESS",
                    "start": match.start(1),
                    "end": match.end(1),
                    "score": 0.7,
                    "value": address_value
                })
        
        # Organization patterns (look for common organization indicators)
        # Arabic: شركة، مؤسسة، بنك، جمعية
        # English: Inc, Corp, LLC, Ltd, Company, Bank, Organization
        org_keywords_ar = r'(?:شركة|مؤسسة|بنك|جمعية|هيئة|منظمة)'
        org_keywords_en = r'(?:Inc|Corp|LLC|Ltd|Company|Co|Bank|Organization|Org|Corporation)'
        # Pattern 1: "Organization:" or "المنظمة:" followed by name
        org_labeled_pattern = rf'(?:Organization|المنظمة|الشركة)\s*:?\s*([^\n]{3,80})'
        for match in re.finditer(org_labeled_pattern, text, re.IGNORECASE):
            org_value = match.group(1).strip()
            # Remove trailing parentheses
            org_value = re.sub(r'\s*\([^)]*\).*$', '', org_value).strip()
            if len(org_value) >= 3:
                detected_entities.append({
                    "entity_type": "ORGANIZATION",
                    "start": match.start(1),
                    "end": match.end(1),
                    "score": 0.85,
                    "value": org_value
                })
        
        # Pattern 2: keyword followed by organization name (3-50 chars)
        org_pattern = rf'(?:{org_keywords_ar}|{org_keywords_en})\s+([A-Za-z\u0600-\u06FF0-9\s]{{3,50}}?)(?:[,\n\.]|\(|$)'
        for match in re.finditer(org_pattern, text, re.IGNORECASE):
            # Extract organization name (group 1)
            org_name = match.group(1).strip()
            # Remove trailing parentheses
            org_name = re.sub(r'\s*\([^)]*\).*$', '', org_name).strip()
            if org_name and len(org_name) >= 3:
                # Find actual start (before keyword)
                start_pos = match.start()
                end_pos = match.end()
                # Adjust to include keyword
                keyword_match = re.search(rf'(?:{org_keywords_ar}|{org_keywords_en})', text[start_pos:end_pos], re.IGNORECASE)
                if keyword_match:
                    start_pos = start_pos + keyword_match.start()
                detected_entities.append({
                    "entity_type": "ORGANIZATION",
                    "start": start_pos,
                    "end": end_pos,
                    "score": 0.7,
                    "value": text[start_pos:end_pos].strip()
                })
        
        # Person names (look for common name patterns)
        # Arabic: اسم عربي (2-4 words)
        # English: First Last, First Middle Last
        # Look for capitalized words that might be names
        # This is less reliable, so lower score
        name_patterns = [
            # Arabic names (2-4 Arabic words, after "Name:" or "اسم:")
            (r'(?:Name|اسم)\s*:?\s*([\u0600-\u06FF]{3,15}\s+[\u0600-\u06FF]{3,15}(?:\s+[\u0600-\u06FF]{3,15}){0,2})', 'ar_name_labeled'),
            # Arabic names standalone (2-4 words) - more specific
            (r'\b([\u0600-\u06FF]{3,15}\s+[\u0600-\u06FF]{3,15}(?:\s+[\u0600-\u06FF]{3,15}){0,2})\b', 'ar_name'),
            # English names (Title? First Last or First Middle Last)
            (r'(?:Name|اسم)\s*:?\s*((?:Mr|Mrs|Ms|Dr|Prof)\.?\s+[A-Z][a-z]+\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)', 'en_name_labeled'),
            (r'\b((?:Mr|Mrs|Ms|Dr|Prof)\.?\s+[A-Z][a-z]+\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b', 'en_name_title'),
            (r'\b([A-Z][a-z]+\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b', 'en_name'),
        ]
        for pattern, pattern_type in name_patterns:
            for match in re.finditer(pattern, text):
                # Extract name (group 1 if labeled, full match if standalone)
                if 'labeled' in pattern_type:
                    value = match.group(1).strip()
                    start_pos = match.start(1)
                    end_pos = match.end(1)
                else:
                    # For standalone patterns, check if there's a group
                    if match.groups():
                        value = match.group(1).strip()
                        start_pos = match.start(1)
                        end_pos = match.end(1)
                    else:
                        value = match.group().strip()
                        start_pos = match.start()
                        end_pos = match.end()
                
                # Skip if it's part of email, organization, or address
                context_start = max(0, start_pos - 15)
                context_end = min(len(text), end_pos + 15)
                context = text[context_start:context_end].lower()
                
                # Skip common false positives
                skip_keywords = ['email', 'phone', 'address', 'company', 'شركة', 'organization', 'منظمة']
                # But allow if it's labeled as "Name:"
                if 'labeled' in pattern_type or not any(keyword in context for keyword in skip_keywords):
                    # Skip if it's part of an email address
                    if '@' not in context and value:
                        detected_entities.append({
                            "entity_type": "PERSON",
                            "start": start_pos,
                            "end": end_pos,
                            "score": 0.75 if 'labeled' in pattern_type else 0.65,
                            "value": value
                        })
        
        # Location patterns (city names, countries)
        # Pattern 1: "Location:" or "الموقع:" followed by location
        location_labeled_pattern = rf'(?:Location|الموقع|المدينة)\s*:?\s*([^\n]{2,50})'
        for match in re.finditer(location_labeled_pattern, text, re.IGNORECASE):
            location_value = match.group(1).strip()
            # Remove trailing parentheses
            location_value = re.sub(r'\s*\([^)]*\).*$', '', location_value).strip()
            if len(location_value) >= 2:
                detected_entities.append({
                    "entity_type": "LOCATION",
                    "start": match.start(1),
                    "end": match.end(1),
                    "score": 0.85,
                    "value": location_value
                })
        
        # Pattern 2: Known city names
        # Arabic city names
        arabic_cities = r'(?:الرياض|جدة|دبي|أبوظبي|الكويت|الدوحة|المنامة|بيروت|القاهرة|الإسكندرية|الخرطوم|تونس|الجزائر|الرباط)'
        # Common English city names
        english_cities = r'(?:New York|London|Paris|Tokyo|Berlin|Madrid|Rome|Moscow|Dubai|Cairo|Riyadh|Jeddah)'
        location_pattern = rf'\b(?:{arabic_cities}|{english_cities})\b'
        for match in re.finditer(location_pattern, text, re.IGNORECASE):
            detected_entities.append({
                "entity_type": "LOCATION",
                "start": match.start(),
                "end": match.end(),
                "score": 0.7,
                "value": match.group()
            })
        
        return detected_entities
    
    def analyze(self, text: str, language: str = None) -> List[Dict[str, Any]]:
        """
        Analyze text and detect sensitive data and malicious scripts
        
        Args:
            text: Text to analyze
            language: Language code (defaults to configured language)
            
        Returns:
            List of detected entities with their positions and confidence scores
        """
        if not text:
            return []
        
        detected_entities = []
        
        # First, detect malicious scripts (always check for these)
        malicious_scripts = self._detect_malicious_scripts(text)
        detected_entities.extend(malicious_scripts)
        
        if malicious_scripts:
            logger.warning(f"Detected {len(malicious_scripts)} malicious script patterns in text")
        
        # Use Presidio if available for sensitive data detection
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
                for result in results:
                    detected_entities.append({
                        "entity_type": result.entity_type,
                        "start": result.start,
                        "end": result.end,
                        "score": result.score,
                        "value": text[result.start:result.end]
                    })
                
                logger.info(f"Detected {len(detected_entities)} entities in text (including {len(malicious_scripts)} scripts)")
                return detected_entities
                
            except Exception as e:
                # Presidio failed, will use regex fallback (this is expected if Spacy models are missing)
                logger.debug(f"Presidio analysis failed: {e}, using regex fallback")
        
        # Fallback to regex for sensitive data
        sensitive_data = self._analyze_with_regex(text)
        
        # Remove duplicates and overlapping entities (keep higher score)
        if sensitive_data:
            # Sort by start position, then by score (descending)
            sensitive_data.sort(key=lambda x: (x['start'], -x['score']))
            filtered_data = []
            for entity in sensitive_data:
                # Check for overlaps with existing entities
                overlap = False
                for i, existing in enumerate(filtered_data):
                    # Check if entities overlap (same type and overlapping position)
                    if (entity['entity_type'] == existing['entity_type'] and 
                        not (entity['end'] <= existing['start'] or entity['start'] >= existing['end'])):
                        # Overlap detected - keep the one with higher score or longer match
                        if entity['score'] > existing['score'] or (entity['score'] == existing['score'] and 
                            (entity['end'] - entity['start']) > (existing['end'] - existing['start'])):
                            filtered_data[i] = entity
                        overlap = True
                        break
                    # Also check if different types overlap - prefer more specific types
                    elif not (entity['end'] <= existing['start'] or entity['start'] >= existing['end']):
                        # Different types overlapping - keep both if scores are close, otherwise prefer higher score
                        score_diff = abs(entity['score'] - existing['score'])
                        if score_diff > 0.15:  # Significant difference
                            if entity['score'] > existing['score']:
                                filtered_data[i] = entity
                                overlap = True
                                break
                        # If scores are close, keep both (they might be different entities)
                
                if not overlap:
                    filtered_data.append(entity)
            sensitive_data = filtered_data
        
        detected_entities.extend(sensitive_data)
        
        logger.info(f"Detected {len(detected_entities)} entities using regex patterns (including {len(malicious_scripts)} scripts)")
        return detected_entities
    
    def get_supported_entities(self) -> List[str]:
        """
        Get list of supported entity types
        
        Returns:
            List of supported entity type names (including MALICIOUS_SCRIPT)
        """
        entities = list(self.supported_entities)
        if "MALICIOUS_SCRIPT" not in entities:
            entities.append("MALICIOUS_SCRIPT")
        return entities
    
    def is_sensitive(self, text: str, threshold: float = 0.5) -> bool:
        """
        Check if text contains sensitive data or malicious scripts
        
        Args:
            text: Text to check
            threshold: Minimum confidence score to consider as sensitive
            
        Returns:
            True if sensitive data or malicious scripts detected, False otherwise
        """
        entities = self.analyze(text)
        return any(entity["score"] >= threshold for entity in entities)

