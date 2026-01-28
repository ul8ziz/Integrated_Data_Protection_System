"""
Validation utilities
"""
import re
import html
from typing import List


def validate_ip_address(ip: str) -> bool:
    """
    Validate IP address (IPv4 or IPv6)
    
    Args:
        ip: IP address string
        
    Returns:
        True if valid, False otherwise
    """
    # IPv4 pattern
    ipv4_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
    # IPv6 pattern (simplified)
    ipv6_pattern = r'^([0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}$'
    
    if re.match(ipv4_pattern, ip):
        parts = ip.split('.')
        return all(0 <= int(part) <= 255 for part in parts)
    elif re.match(ipv6_pattern, ip):
        return True
    return False


def validate_entity_types(entity_types: List[str]) -> bool:
    """
    Validate entity types list
    
    Args:
        entity_types: List of entity type names
        
    Returns:
        True if valid, False otherwise
    """
    valid_entities = [
        "PERSON", "PHONE_NUMBER", "EMAIL_ADDRESS", "CREDIT_CARD",
        "ADDRESS", "ORGANIZATION", "DATE_TIME", "LOCATION",
        "IBAN_CODE", "IP_ADDRESS", "MEDICAL_LICENSE", "US_SSN", "MALICIOUS_SCRIPT"
    ]
    return all(entity in valid_entities for entity in entity_types)


def validate_action(action: str) -> bool:
    """
    Validate policy action
    
    Args:
        action: Action string
        
    Returns:
        True if valid, False otherwise
    """
    valid_actions = ["block", "alert", "encrypt", "anonymize"]
    return action in valid_actions


def sanitize_input(input_str: str) -> str:
    """
    Sanitize input by removing/escaping potentially dangerous content
    
    Args:
        input_str: Input string to sanitize
        
    Returns:
        Sanitized string
    """
    if not input_str:
        return input_str
    
    # Remove HTML tags
    input_str = re.sub(r'<[^>]+>', '', input_str)
    
    # Remove script-related patterns (case-insensitive)
    dangerous_patterns = [
        r'<script[^>]*>.*?</script>',
        r'javascript:',
        r'onerror\s*=',
        r'onclick\s*=',
        r'onload\s*=',
        r'onmouseover\s*=',
        r'eval\s*\(',
        r'Function\s*\(',
        r'exec\s*\(',
        r'__import__\s*\(',
        r'bash\s+-c',
        r'sh\s+-c',
    ]
    
    for pattern in dangerous_patterns:
        input_str = re.sub(pattern, '', input_str, flags=re.IGNORECASE)
    
    return input_str.strip()


def encode_special_chars(input_str: str) -> str:
    """
    Encode special characters to prevent injection attacks
    
    Args:
        input_str: Input string to encode
        
    Returns:
        HTML-encoded string
    """
    if not input_str:
        return input_str
    
    # HTML encode special characters
    return html.escape(input_str, quote=True)


def validate_password_strength(password: str) -> tuple[bool, str]:
    """
    Validate password strength
    
    Requirements:
    - Minimum 12 characters
    - At least one uppercase letter (A-Z)
    - At least one lowercase letter (a-z)
    - At least one digit (0-9)
    - At least one special character (!@#$%^&*()_+-=[]{}|;:,.<>?)
    
    Args:
        password: Password to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if len(password) < 12:
        return False, "Password must be at least 12 characters long"
    
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter"
    
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter"
    
    if not re.search(r'[0-9]', password):
        return False, "Password must contain at least one digit"
    
    if not re.search(r'[!@#$%^&*()_+\-=\[\]{}|;:,.<>?]', password):
        return False, "Password must contain at least one special character (!@#$%^&*()_+-=[]{}|;:,.<>?)"
    
    return True, ""


def validate_email_format(email: str) -> tuple[bool, str]:
    """
    Validate email format with strict rules
    
    Args:
        email: Email address to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not email:
        return False, "Email is required"
    
    # Basic email pattern (RFC 5322 simplified)
    email_pattern = r'^[a-zA-Z0-9]([a-zA-Z0-9._-]*[a-zA-Z0-9])?@[a-zA-Z0-9]([a-zA-Z0-9.-]*[a-zA-Z0-9])?\.[a-zA-Z]{2,}$'
    
    if not re.match(email_pattern, email):
        return False, "Invalid email format. Only letters, numbers, dots, hyphens, and underscores are allowed"
    
    # Check for dangerous characters
    dangerous_chars = ['<', '>', '"', "'", '&', ';', '(', ')', '[', ']', '{', '}', '|', '\\', '/', '`']
    for char in dangerous_chars:
        if char in email:
            return False, f"Email contains invalid character: {char}"
    
    # Check length
    if len(email) > 254:  # RFC 5321 limit
        return False, "Email address is too long (maximum 254 characters)"
    
    return True, ""

