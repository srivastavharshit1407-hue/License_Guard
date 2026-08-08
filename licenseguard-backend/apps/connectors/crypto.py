"""
Symmetric encryption for vendor credentials at rest.

A stolen database dump should not hand an attacker your Google service-account
key. Everything written to Connection.encrypted_credentials goes through here.

The key lives in CREDENTIALS_ENCRYPTION_KEY. In production put it in a secrets
manager (AWS Secrets Manager, GCP Secret Manager, Doppler...), never in git.
Rotating the key means re-encrypting existing rows, so decide early.
"""
from __future__ import annotations

import json

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


def _fernet() -> Fernet:
    key = settings.CREDENTIALS_ENCRYPTION_KEY
    if not key:
        raise ImproperlyConfigured(
            "CREDENTIALS_ENCRYPTION_KEY is not set. Generate one with:\n"
            '  python -c "from cryptography.fernet import Fernet; '
            'print(Fernet.generate_key().decode())"'
        )
    return Fernet(key.encode() if isinstance(key, str) else key)


def encrypt_dict(data: dict) -> str:
    return _fernet().encrypt(json.dumps(data).encode()).decode()


def decrypt_dict(token: str) -> dict:
    if not token:
        return {}
    try:
        return json.loads(_fernet().decrypt(token.encode()).decode())
    except InvalidToken as exc:
        raise ValueError(
            "Could not decrypt stored credentials. The encryption key has "
            "probably changed since they were saved."
        ) from exc
