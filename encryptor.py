from cryptography.fernet import Fernet
import os

class Encryptor:
    def __init__(self):
        # En producción, esta KEY debería estar en Streamlit Secrets
        self.key = os.getenv("ENCRYPTION_KEY", Fernet.generate_key().decode())
        self.cipher = Fernet(self.key.encode())

    def encrypt(self, text):
        if not text: return ""
        return self.cipher.encrypt(text.encode()).decode()

    def decrypt(self, encrypted_text):
        if not encrypted_text: return ""
        try:
            return self.cipher.decrypt(encrypted_text.encode()).decode()
        except:
            return "Error: No se pudo desencriptar"
