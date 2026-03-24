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
            # Classic SELECT ... WHERE ... OR '1'='1'
            (r"SELECT\s+\*\s+FROM\s+\w+\s+WHERE\s+[^;]+OR\s+['\"]1['\"]\s*=\s*['\"]1", 'SQL injection SELECT WHERE OR', 0.92),
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

    def _scan_ibans(self, text: str) -> List[Dict[str, Any]]:
        """
        IBAN detection (same rules everywhere). Used by regex analyzer and post-processing Presidio results.
        """
        out: List[Dict[str, Any]] = []
        # Do not use \s in the capture group — it matches newlines and can swallow the next line (e.g. "US SSN")
        iban_labeled_pattern = r'(?:IBAN|الآيبان|رقم الآيبان)\s*:?\s*([A-Z0-9][A-Z0-9 ]{14,34})'
        for match in re.finditer(iban_labeled_pattern, text, re.IGNORECASE):
            iban_value = match.group(1).strip()
            iban_value = re.sub(r'\s*\([^)]*\).*$', '', iban_value).strip().replace(' ', '')
            if 15 <= len(iban_value) <= 34 and re.match(r'^[A-Z]{2}\d{2}[A-Z0-9]+$', iban_value):
                if iban_value.startswith('SA') and len(iban_value) != 24:
                    continue
                out.append({
                    "entity_type": "IBAN_CODE",
                    "start": match.start(1),
                    "end": match.end(1),
                    "score": 0.85,
                    "value": iban_value
                })
        iban_pattern = r'\b([A-Z]{2}\d{2}[A-Z0-9]{4,30})\b'
        for match in re.finditer(iban_pattern, text):
            value = match.group(1)
            if 15 <= len(value) <= 34:
                if value.startswith('SA') and len(value) != 24:
                    continue
                out.append({
                    "entity_type": "IBAN_CODE",
                    "start": match.start(),
                    "end": match.end(),
                    "score": 0.75,
                    "value": value
                })
        return out

    @staticmethod
    def _span_inside_spans(start: int, end: int, spans: List[tuple]) -> bool:
        for s, e in spans:
            if s <= start and end <= e:
                return True
        return False

    @staticmethod
    def _spans_overlap(a: tuple, b: tuple) -> bool:
        s1, e1 = a
        s2, e2 = b
        return not (e1 <= s2 or e2 <= s1)

    def _dedupe_ibans(self, ibans: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Keep one IBAN per normalized value; prefer longer span (labeled line), then higher score."""
        by_val: Dict[str, Dict[str, Any]] = {}
        for e in ibans:
            if e.get("entity_type") != "IBAN_CODE":
                continue
            v = (e.get("value") or "").strip().replace(" ", "").upper()
            if not v:
                continue
            cur = by_val.get(v)
            span_len = e["end"] - e["start"]
            if cur is None:
                by_val[v] = e
                continue
            cur_len = cur["end"] - cur["start"]
            if span_len > cur_len:
                by_val[v] = e
            elif span_len == cur_len and e.get("score", 0) > cur.get("score", 0):
                by_val[v] = e
        return list(by_val.values())

    def _dedupe_locations(self, entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Drop duplicate LOCATION with same normalized value (keep highest score)."""
        locs = [e for e in entities if e.get("entity_type") == "LOCATION"]
        rest = [e for e in entities if e.get("entity_type") != "LOCATION"]
        seen: Dict[str, Dict[str, Any]] = {}
        for e in locs:
            key = (e.get("value") or "").strip().lower()
            if not key:
                rest.append(e)
                continue
            prev = seen.get(key)
            if prev is None or e.get("score", 0) > prev.get("score", 0):
                seen[key] = e
            elif e.get("score", 0) == prev.get("score", 0) and (e["end"] - e["start"]) > (prev["end"] - prev["start"]):
                seen[key] = e
        rest.extend(seen.values())
        return rest

    @staticmethod
    def _strip_address_false_ips(entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Drop ADDRESS when value is only an IPv4 (Presidio sometimes labels 'IP Address' lines as ADDRESS)."""
        ipv4 = re.compile(
            r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'
        )
        out: List[Dict[str, Any]] = []
        for e in entities:
            if e.get("entity_type") == "ADDRESS" and ipv4.match((e.get("value") or "").strip()):
                continue
            out.append(e)
        return out

    def _supplement_labeled_fields(self, text: str, entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Add PERSON / ADDRESS / ORGANIZATION from labeled lines when Presidio missed them
        and no existing entity of the same type overlaps the span (LOCATION etc. may overlap ADDRESS text).
        """
        def overlaps_same_type(start: int, end: int, entity_type: str) -> bool:
            for e in entities:
                if e.get("entity_type") != entity_type:
                    continue
                if e["end"] <= start or e["start"] >= end:
                    continue
                return True
            return False

        extra: List[Dict[str, Any]] = []
        # Name: rest of line (supports hyphenated surnames e.g. Ahmed Al-Qahtani)
        for match in re.finditer(r'(?:^|\n)\s*(?:Name|اسم)\s*:?\s*([^\n]+)', text):
            raw = match.group(1).strip()
            if len(raw) < 2 or '@' in raw or re.match(r'^\d', raw):
                continue
            if overlaps_same_type(match.start(1), match.end(1), "PERSON"):
                continue
            extra.append({
                "entity_type": "PERSON",
                "start": match.start(1),
                "end": match.end(1),
                "score": 0.88,
                "value": raw,
            })
        # Line must start with "Address" — avoids matching "IP Address:"
        address_labeled_pattern = rf'(?:^|\n)\s*(?:Address|العنوان)\s*:?\s*([^\n]{{10,100}})'
        for match in re.finditer(address_labeled_pattern, text, re.IGNORECASE):
            address_value = match.group(1).strip()
            address_value = re.sub(r'\s*\([^)]*\).*$', '', address_value).strip()
            if len(address_value) < 10 or '@' in address_value:
                continue
            if overlaps_same_type(match.start(1), match.end(1), "ADDRESS"):
                continue
            extra.append({
                "entity_type": "ADDRESS",
                "start": match.start(1),
                "end": match.end(1),
                "score": 0.86,
                "value": address_value,
            })
        org_labeled_pattern = rf'(?:^|\n)\s*(?:Organization|المنظمة|الشركة)\s*:?\s*([^\n]{{3,80}})'
        for match in re.finditer(org_labeled_pattern, text, re.IGNORECASE):
            org_value = match.group(1).strip()
            org_value = re.sub(r'\s*\([^)]*\).*$', '', org_value).strip()
            if len(org_value) < 3:
                continue
            if overlaps_same_type(match.start(1), match.end(1), "ORGANIZATION"):
                continue
            extra.append({
                "entity_type": "ORGANIZATION",
                "start": match.start(1),
                "end": match.end(1),
                "score": 0.86,
                "value": org_value,
            })
        return extra

    def _post_process_entities(self, text: str, entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        - Merge regex IBANs (fixes Presidio missing IBAN + CC false positives inside IBAN).
        - Remove CREDIT_CARD fully contained in any IBAN span.
        - Deduplicate LOCATION by value.
        - Add labeled PERSON/ADDRESS/ORGANIZATION when missing.
        """
        iban_from_regex = self._scan_ibans(text)
        iban_existing = [e for e in entities if e.get("entity_type") == "IBAN_CODE"]
        merged_ibans = self._dedupe_ibans(iban_existing + iban_from_regex)
        iban_spans = [(e["start"], e["end"]) for e in merged_ibans]

        non_iban = [e for e in entities if e.get("entity_type") != "IBAN_CODE"]
        filtered = []
        for e in non_iban:
            if e.get("entity_type") == "CREDIT_CARD" and self._span_inside_spans(e["start"], e["end"], iban_spans):
                continue
            filtered.append(e)
        merged = filtered + merged_ibans
        merged = self._dedupe_locations(merged)
        merged = self._strip_address_false_ips(merged)
        merged.sort(key=lambda x: x["start"])
        supplements = self._supplement_labeled_fields(text, merged)
        merged.extend(supplements)
        merged.sort(key=lambda x: x["start"])
        return merged
    
    def _analyze_with_regex(self, text: str) -> List[Dict[str, Any]]:
        """Fallback regex-based analysis"""
        detected_entities = []

        def _is_ssn_format(s: str) -> bool:
            """True if value looks like US SSN (XXX-XX-XXXX) so we don't tag as phone."""
            c = re.sub(r'[-.\s]', '', s)
            return len(c) == 9 and c.isdigit()

        def _is_long_digit_only(s: str) -> bool:
            """True if value is long digit string (e.g. VAT/tax ID), not a phone."""
            c = re.sub(r'[-.\s]', '', s)
            return len(c) >= 14 and c.isdigit()

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
                if _is_ssn_format(phone_value) or _is_long_digit_only(phone_value):
                    continue
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
            value = match.group()
            if re.match(r'^\d{4}[-.\s]?\d{4}[-.\s]?\d{4}[-.\s]?\d{4}$', value):
                continue  # Credit card
            if _is_ssn_format(value) or _is_long_digit_only(value):
                continue  # SSN or VAT/tax ID, not phone
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
        
        detected_entities.extend(self._scan_ibans(text))
        
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
        address_keywords_en = r'(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Lane|Ln|Drive|Dr|City|State|Zip|Postal Code)'
        # Pattern 1: line starts with "Address:" (not "IP Address:")
        address_labeled_pattern = rf'(?:^|\n)\s*(?:Address|العنوان)\s*:?\s*([^\n]{10,100})'
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
        # Pattern 1: line starts with "Organization:" (avoid matching mid-line "Organization")
        org_labeled_pattern = rf'(?:^|\n)\s*(?:Organization|المنظمة|الشركة)\s*:?\s*([^\n]{3,80})'
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
                
                # Skip common false positives (labels, not person names)
                skip_keywords = ['email', 'phone', 'address', 'company', 'شركة', 'organization', 'منظمة']
                person_label_false_positives = {
                    'credit card', 'stock symbol', 'stock market', 'tax number', 'vat id',
                    'isin', 'revenue', 'profit', 'organization', 'address', 'location',
                    'date', 'ip address', 'phone number', 'email address'
                }
                if value.lower().strip() in person_label_false_positives:
                    continue
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
        
        # Tax patterns (الضرائب) — value must be the tax number only, not "ID: ..." or "Number: ..."
        tax_labeled_pattern = r'(?:Tax|VAT|الضريبة|رقم الضريبة|VAT ID|Tax ID|Tax Number)\s*:?\s*([^\n]{5,35})'
        for match in re.finditer(tax_labeled_pattern, text, re.IGNORECASE):
            tax_value = match.group(1).strip()
            tax_value = re.sub(r'\s*\([^)]*\).*$', '', tax_value).strip()
            # Strip label prefixes so value is only the number (e.g. "ID: 300..." -> "300...", "Number: SA..." -> "SA...")
            for prefix in (r'^ID\s*:\s*', r'^Number\s*:\s*', r'^رقم\s*:\s*', r'^الرقم\s*:\s*'):
                tax_value = re.sub(prefix, '', tax_value, flags=re.IGNORECASE).strip()
            if len(tax_value) >= 5:
                detected_entities.append({
                    "entity_type": "TAX",
                    "start": match.start(1),
                    "end": match.end(1),
                    "score": 0.85,
                    "value": tax_value
                })
        # Pattern 2: Saudi VAT number (SA + 9 digits) or tax percentage
        tax_sa_pattern = r'\b(SA\d{9})\b'
        for match in re.finditer(tax_sa_pattern, text):
            detected_entities.append({
                "entity_type": "TAX",
                "start": match.start(),
                "end": match.end(),
                "score": 0.9,
                "value": match.group()
            })
        tax_pct_pattern = r'(?:Tax|الضريبة|VAT)\s*:?\s*(\d{1,3}(?:\.\d+)?\s*%)'
        for match in re.finditer(tax_pct_pattern, text, re.IGNORECASE):
            detected_entities.append({
                "entity_type": "TAX",
                "start": match.start(1),
                "end": match.end(1),
                "score": 0.8,
                "value": match.group(1).strip()
            })
        
        # Stock patterns (الأسهم)
        # Skip words that are labels or market suffixes (SR, SA = Tadawul), not ticker symbols
        stock_label_blocklist = {'ISIN', 'SEC', 'ETF', 'NYSE', 'NASDAQ', 'TICKER', 'SYMBOL', 'MARKET', 'SR', 'SA'}
        # Pattern 1: Stock symbols (e.g. AAPL, MSFT, 2222.SR)
        stock_symbol_pattern = r'\b([A-Z]{2,5}(?:\.[A-Z]{2})?)\b'
        stock_keywords = r'(?:Stock|Share|سهم|أسهم|رمز السهم|Ticker|Market|تداول)'
        for match in re.finditer(stock_symbol_pattern, text):
            value = match.group(1)
            if value.upper() in stock_label_blocklist:
                continue
            # Check context for stock-related keywords
            ctx_start = max(0, match.start() - 40)
            ctx_end = min(len(text), match.end() + 40)
            context = text[ctx_start:ctx_end]
            if re.search(stock_keywords, context, re.IGNORECASE) or re.search(r'\.(SR|SA|TADAWUL)', value):
                detected_entities.append({
                    "entity_type": "STOCK",
                    "start": match.start(),
                    "end": match.end(),
                    "score": 0.8,
                    "value": value
                })
        # Tadawul-style numeric tickers (e.g. 2222.SR)
        for match in re.finditer(r'\b(\d{4}\.(?:SR|SA|TADAWUL))\b', text, re.IGNORECASE):
            value = match.group(1)
            ctx_start = max(0, match.start() - 50)
            ctx_end = min(len(text), match.end() + 40)
            context = text[ctx_start:ctx_end]
            if re.search(stock_keywords, context, re.IGNORECASE):
                detected_entities.append({
                    "entity_type": "STOCK",
                    "start": match.start(),
                    "end": match.end(),
                    "score": 0.82,
                    "value": value
                })
        # Pattern 2: ISIN (2 letters + 9 alphanumeric + 1 digit) — report as ISIN_CODE
        isin_pattern = r'\b([A-Z]{2}[A-Z0-9]{9}\d)\b'
        for match in re.finditer(isin_pattern, text):
            detected_entities.append({
                "entity_type": "ISIN_CODE",
                "start": match.start(),
                "end": match.end(),
                "score": 0.85,
                "value": match.group()
            })
        
        # Profit patterns (الأرباح)
        profit_labeled_pattern = r'(?:Profit|Revenue|الربح|صافي الدخل|الأرباح|Net Income|Gross Profit)\s*:?\s*([^\n]{3,50})'
        for match in re.finditer(profit_labeled_pattern, text, re.IGNORECASE):
            profit_value = match.group(1).strip()
            profit_value = re.sub(r'\s*\([^)]*\).*$', '', profit_value).strip()
            if len(profit_value) >= 3:
                money_match = re.search(r'[\d,.]+\s*(?:USD|SAR|ريال|دولار|\$)?', profit_value)
                if money_match:
                    val = money_match.group().strip()
                    start_off = match.start(1) + money_match.start()
                    end_off = match.start(1) + money_match.end()
                else:
                    val = profit_value
                    start_off = match.start(1)
                    end_off = match.end(1)
                detected_entities.append({
                    "entity_type": "PROFIT",
                    "start": start_off,
                    "end": end_off,
                    "score": 0.85,
                    "value": val
                })
        
        return detected_entities
    
    def _detect_custom_financial_entities(self, text: str) -> List[Dict[str, Any]]:
        """
        Detect TAX, STOCK, PROFIT - custom entities not supported by Presidio.
        Used when Presidio is available to supplement its results.
        """
        detected = []
        # Tax patterns — value = tax number only (strip "ID:", "Number:", etc.)
        tax_labeled_pattern = r'(?:Tax|VAT|الضريبة|رقم الضريبة|VAT ID|Tax ID|Tax Number)\s*:?\s*([^\n]{5,35})'
        for match in re.finditer(tax_labeled_pattern, text, re.IGNORECASE):
            tax_value = match.group(1).strip()
            tax_value = re.sub(r'\s*\([^)]*\).*$', '', tax_value).strip()
            for prefix in (r'^ID\s*:\s*', r'^Number\s*:\s*', r'^رقم\s*:\s*', r'^الرقم\s*:\s*'):
                tax_value = re.sub(prefix, '', tax_value, flags=re.IGNORECASE).strip()
            if len(tax_value) >= 5:
                detected.append({"entity_type": "TAX", "start": match.start(1), "end": match.end(1), "score": 0.85, "value": tax_value})
        for match in re.finditer(r'\b(SA\d{9})\b', text):
            detected.append({"entity_type": "TAX", "start": match.start(), "end": match.end(), "score": 0.9, "value": match.group()})
        for match in re.finditer(r'(?:Tax|الضريبة|VAT)\s*:?\s*(\d{1,3}(?:\.\d+)?\s*%)', text, re.IGNORECASE):
            detected.append({"entity_type": "TAX", "start": match.start(1), "end": match.end(1), "score": 0.8, "value": match.group(1).strip()})
        # Stock patterns (skip label words and market suffixes SR, SA)
        stock_label_blocklist = {'ISIN', 'SEC', 'ETF', 'NYSE', 'NASDAQ', 'TICKER', 'SYMBOL', 'MARKET', 'SR', 'SA'}
        stock_keywords = r'(?:Stock|Share|سهم|أسهم|رمز السهم|Ticker|Market|تداول)'
        for match in re.finditer(r'\b([A-Z]{2,5}(?:\.[A-Z]{2})?)\b', text):
            value = match.group(1)
            if value.upper() in stock_label_blocklist:
                continue
            ctx = text[max(0, match.start() - 40):min(len(text), match.end() + 40)]
            if re.search(stock_keywords, ctx, re.IGNORECASE) or re.search(r'\.(SR|SA|TADAWUL)', value):
                detected.append({"entity_type": "STOCK", "start": match.start(), "end": match.end(), "score": 0.8, "value": value})
        for match in re.finditer(r'\b(\d{4}\.(?:SR|SA|TADAWUL))\b', text, re.IGNORECASE):
            ctx = text[max(0, match.start() - 50):min(len(text), match.end() + 40)]
            if re.search(stock_keywords, ctx, re.IGNORECASE):
                detected.append({"entity_type": "STOCK", "start": match.start(), "end": match.end(), "score": 0.82, "value": match.group(1)})
        for match in re.finditer(r'\b([A-Z]{2}[A-Z0-9]{9}\d)\b', text):
            detected.append({"entity_type": "ISIN_CODE", "start": match.start(), "end": match.end(), "score": 0.85, "value": match.group()})
        # Profit patterns
        profit_labeled_pattern = r'(?:Profit|Revenue|الربح|صافي الدخل|الأرباح|Net Income|Gross Profit)\s*:?\s*([^\n]{3,50})'
        for match in re.finditer(profit_labeled_pattern, text, re.IGNORECASE):
            profit_value = match.group(1).strip()
            profit_value = re.sub(r'\s*\([^)]*\).*$', '', profit_value).strip()
            if len(profit_value) >= 3:
                money_match = re.search(r'[\d,.]+\s*(?:USD|SAR|ريال|دولار|\$)?', profit_value)
                if money_match:
                    val, start_off, end_off = money_match.group().strip(), match.start(1) + money_match.start(), match.start(1) + money_match.end()
                else:
                    val, start_off, end_off = profit_value, match.start(1), match.end(1)
                detected.append({"entity_type": "PROFIT", "start": start_off, "end": end_off, "score": 0.85, "value": val})
        return detected
    
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
        
        # Presidio built-in entities (TAX, STOCK, PROFIT are custom - detected via regex)
        PRESIDIO_BUILTIN = {
            "PERSON", "PHONE_NUMBER", "EMAIL_ADDRESS", "CREDIT_CARD", "ADDRESS",
            "ORGANIZATION", "DATE_TIME", "LOCATION", "IBAN_CODE", "IP_ADDRESS",
            "US_SSN", "MEDICAL_LICENSE", "US_BANK_NUMBER", "US_ITIN", "CRYPTO",
            "MAC_ADDRESS", "NRP", "URL"
        }
        
        # Use Presidio if available for sensitive data detection
        if self.analyzer is not None:
            try:
                language = language or settings.PRESIDIO_LANGUAGE
                entities_for_presidio = [e for e in self.supported_entities if e in PRESIDIO_BUILTIN]
                
                # Analyze text with Presidio (only built-in entities)
                results = self.analyzer.analyze(
                    text=text,
                    language=language,
                    entities=entities_for_presidio if entities_for_presidio else self.supported_entities
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
                
                # Add custom financial entities (TAX, STOCK, ISIN_CODE, PROFIT) via regex
                if any(e in self.supported_entities for e in ("TAX", "STOCK", "ISIN_CODE", "PROFIT")):
                    custom_financial = self._detect_custom_financial_entities(text)
                    detected_entities.extend(custom_financial)
                # Prefer TAX over IBAN when same value (e.g. SA123456789012345 as Tax Number)
                tax_values = {e.get("value", "").strip() for e in detected_entities if e.get("entity_type") == "TAX"}
                detected_entities = [
                    e for e in detected_entities
                    if not (e.get("entity_type") == "IBAN_CODE" and e.get("value", "").strip() in tax_values)
                ]
                
                detected_entities = self._post_process_entities(text, detected_entities)
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
            # Drop CREDIT_CARD when its span is fully inside an IBAN (e.g. IBAN body mistaken as card)
            iban_spans = [(e['start'], e['end']) for e in filtered_data if e.get('entity_type') == 'IBAN_CODE']
            filtered_data = [
                e for e in filtered_data
                if not (e.get('entity_type') == 'CREDIT_CARD' and any(
                    s <= e['start'] and e['end'] <= t for s, t in iban_spans
                ))
            ]
            # Drop IBAN when same value was already detected as TAX (e.g. SA123456789012345 as Tax Number)
            tax_values = {e.get('value', '').strip() for e in filtered_data if e.get('entity_type') == 'TAX'}
            filtered_data = [
                e for e in filtered_data
                if not (e.get('entity_type') == 'IBAN_CODE' and e.get('value', '').strip() in tax_values)
            ]
            sensitive_data = filtered_data
        
        detected_entities.extend(sensitive_data)
        detected_entities = self._post_process_entities(text, detected_entities)
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

