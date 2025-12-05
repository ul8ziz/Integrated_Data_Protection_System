"""
Encryption service for sensitive data using AES
"""
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
        salt = b'athier_salt_2024'  # Should be unique per installation
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

