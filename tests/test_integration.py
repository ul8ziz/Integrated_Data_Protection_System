"""
Integration tests
"""
import pytest
from app.services.policy_service import PolicyService
from app.services.encryption_service import EncryptionService


def test_encryption_service():
    """Test encryption service"""
    service = EncryptionService()
    original_text = "Sensitive data: 123-456-7890"
    
    # Encrypt
    encrypted = service.encrypt(original_text)
    assert encrypted != original_text
    assert len(encrypted) > 0
    
    # Decrypt
    decrypted = service.decrypt(encrypted)
    assert decrypted == original_text


def test_hash_text():
    """Test text hashing"""
    service = EncryptionService()
    text = "Test text"
    hash1 = service.hash_text(text)
    hash2 = service.hash_text(text)
    
    # Same text should produce same hash
    assert hash1 == hash2
    
    # Different text should produce different hash
    hash3 = service.hash_text("Different text")
    assert hash1 != hash3


def test_policy_service_initialization():
    """Test policy service initialization"""
    service = PolicyService()
    assert service is not None
    assert service.presidio is not None
    assert service.mydlp is not None
    assert service.encryption is not None

