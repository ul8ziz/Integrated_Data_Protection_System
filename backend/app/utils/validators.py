"""
Validation utilities
"""
import re
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
        "IBAN_CODE", "IP_ADDRESS", "MEDICAL_LICENSE", "US_SSN"
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

