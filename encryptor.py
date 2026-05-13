from cryptography.fernet import Fernet
import os
import base64
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

class Encryptor:
    def __init__(self):
        # Tomamos la frase del usuario y la convertimos en una llave válida de 32 bytes
        passphrase = os.getenv("ENCRYPTION_KEY", "default-secret-key-123")
        
        # Derivamos una llave segura de la frase (PBKDF2)
        salt = b'pagarqr-salt-123' # Sal fija para este caso simple
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(passphrase.encode()))
        self.cipher = Fernet(key)

    def encrypt(self, text):
        if not text: return ""
        return self.cipher.encrypt(text.encode()).decode()

    def decrypt(self, encrypted_text):
        if not encrypted_text: return ""
        try:
            return self.cipher.decrypt(encrypted_text.encode()).decode()
        except:
            return "Error: No se pudo desencriptar"
