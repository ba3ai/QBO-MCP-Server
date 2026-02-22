import os
from cryptography.fernet import Fernet

def _fernet() -> Fernet:
    key = os.getenv("FERNET_KEY")
    if not key:
        raise RuntimeError("FERNET_KEY is not set")
    return Fernet(key.encode() if isinstance(key, str) else key)

def encrypt(plaintext: str) -> str:
    f = _fernet()
    return f.encrypt(plaintext.encode("utf-8")).decode("utf-8")

def decrypt(ciphertext: str) -> str:
    f = _fernet()
    return f.decrypt(ciphertext.encode("utf-8")).decode("utf-8")
