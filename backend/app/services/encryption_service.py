"""
Encryption service for sensitive data using AES
"""
import re
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
import base64
import hashlib
from app.config import settings


class EncryptionService:
    """Service for encrypting and decrypting sensitive data"""
    
    def __init__(self):
        """Initialize encryption service with key from settings"""
        self.key = self._derive_key(settings.ENCRYPTION_KEY.encode())
        self.cipher = Fernet(self.key)
    
    def _derive_key(self, password: bytes) -> bytes:
        """
        Derive a Fernet key from a password using PBKDF2
        """
        # Use a fixed salt for consistency (in production, consider storing salt separately)
        salt = b'Secure_salt_2024'  # Should be unique per installation
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )
        key = base64.urlsafe_b64encode(kdf.derive(password))
        return key
    
    def encrypt(self, data: str) -> str:
        """
        Encrypt sensitive data
        
        Args:
            data: Plain text data to encrypt
            
        Returns:
            Encrypted data as base64 string
        """
        if not data:
            return ""
        encrypted = self.cipher.encrypt(data.encode())
        return encrypted.decode()
    
    def decrypt(self, encrypted_data: str) -> str:
        """
        Decrypt sensitive data
        
        Args:
            encrypted_data: Encrypted data as base64 string
            
        Returns:
            Decrypted plain text data
        """
        if not encrypted_data:
            return ""
        decrypted = self.cipher.decrypt(encrypted_data.encode())
        return decrypted.decode()
    
    def decrypt_mixed_content(self, text: str) -> str:
        """
        Decrypt content that may contain both plain text and Fernet-encrypted tokens.
        Finds all base64url tokens that look like Fernet (e.g. gAAAAA...), decrypts each,
        and returns the text with tokens replaced by decrypted values.
        """
        if not text or not text.strip():
            return text
        # Fernet tokens are base64url: start with gAAAAA, then 35+ chars, optional = padding
        pattern = re.compile(r"gAAAAA[A-Za-z0-9_-]{35,}=*")
        result = text
        # Process from end to start so positions don't shift
        matches = list(pattern.finditer(result))
        for m in reversed(matches):
            token = m.group(0)
            try:
                decrypted = self.decrypt(token)
                result = result[: m.start()] + decrypted + result[m.end() :]
            except Exception:
                pass
        return result
    
    @staticmethod
    def hash_text(text: str) -> str:
        """
        Create SHA-256 hash of text (one-way, for indexing)
        
        Args:
            text: Text to hash
            
        Returns:
            SHA-256 hash as hex string
        """
        return hashlib.sha256(text.encode()).hexdigest()

