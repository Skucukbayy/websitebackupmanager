from cryptography.fernet import Fernet
import os
import logging

logger = logging.getLogger(__name__)

class EncryptionManager:
    """
    Manages symmetric encryption for sensitive data using Fernet.
    """
    def __init__(self, key=None):
        """
        Initialize with a key. If no key is provided, it tries to get it from env.
        """
        if key:
            self.cipher_suite = Fernet(key)
        else:
            # Try to get from config/env, otherwise generate one (warning: data loss on restart if not saved)
            env_key = os.environ.get('ENCRYPTION_KEY')
            if env_key:
                try:
                    self.cipher_suite = Fernet(env_key)
                except Exception as e:
                    logger.error(f"Invalid encryption key in environment: {e}")
                    raise
            else:
                logger.warning("No ENCRYPTION_KEY found. Generating a temporary one. Passwords will be lost on restart!")
                self.cipher_suite = Fernet(Fernet.generate_key())

    def encrypt(self, data: str) -> str:
        """Encrypts a string and returns the encrypted token as a string."""
        if not data:
            return None
        try:
            encrypted_bytes = self.cipher_suite.encrypt(data.encode('utf-8'))
            return encrypted_bytes.decode('utf-8')
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise

    def decrypt(self, token: str) -> str:
        """Decrypts a token string and returns the original string."""
        if not token:
            return None
        try:
            decrypted_bytes = self.cipher_suite.decrypt(token.encode('utf-8'))
            return decrypted_bytes.decode('utf-8')
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise

# Global instance will be initialized with app config
encryption_manager = None

def init_encryption(key):
    global encryption_manager
    encryption_manager = EncryptionManager(key)

def encrypt_password(password):
    if encryption_manager:
        return encryption_manager.encrypt(password)
    return password

def decrypt_password(encrypted_password):
    if encryption_manager:
        return encryption_manager.decrypt(encrypted_password)
    return encrypted_password
