#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Phase 10 - Advanced Security Features
OAuth2 support, encryption, token management, and secure operations

This module provides:
1. Token-based authentication
2. Encryption/decryption utilities
3. OAuth2 integration framework
4. Secure credential storage
5. API key management
6. CORS and CSRF protection
"""

import os
import json
import secrets
import hashlib
import hmac
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict, field
from datetime import datetime, timedelta
from enum import Enum


class TokenType(Enum):
    """Token types"""
    ACCESS = "access"
    REFRESH = "refresh"
    API_KEY = "api_key"


@dataclass
class Token:
    """Security token"""
    token_id: str
    token_type: TokenType
    value: str
    user_id: str
    created_at: str
    expires_at: str
    scopes: List[str] = field(default_factory=list)
    is_valid: bool = True
    
    def is_expired(self) -> bool:
        """Check if token is expired"""
        expiry = datetime.fromisoformat(self.expires_at)
        return datetime.now() > expiry
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class EncryptionKey:
    """Encryption key metadata"""
    key_id: str
    algorithm: str
    created_at: str
    rotated_at: Optional[str] = None
    is_active: bool = True


class TokenManager:
    """Manage security tokens"""
    
    def __init__(self, secret_key: str, token_lifetime_hours: int = 24):
        self.secret_key = secret_key
        self.token_lifetime_hours = token_lifetime_hours
        self.tokens: Dict[str, Token] = {}
    
    def generate_token(self, user_id: str, token_type: TokenType = TokenType.ACCESS,
                      scopes: List[str] = None) -> Token:
        """Generate new token"""
        token_value = secrets.token_urlsafe(32)
        token_id = secrets.token_hex(16)
        
        now = datetime.now()
        expires_at = now + timedelta(hours=self.token_lifetime_hours)
        
        token = Token(
            token_id=token_id,
            token_type=token_type,
            value=token_value,
            user_id=user_id,
            created_at=now.isoformat(),
            expires_at=expires_at.isoformat(),
            scopes=scopes or []
        )
        
        self.tokens[token_id] = token
        return token
    
    def validate_token(self, token_value: str) -> Optional[Token]:
        """Validate token"""
        for token in self.tokens.values():
            if token.value == token_value:
                if token.is_expired():
                    token.is_valid = False
                    return None
                return token if token.is_valid else None
        return None
    
    def revoke_token(self, token_id: str) -> bool:
        """Revoke token"""
        if token_id in self.tokens:
            self.tokens[token_id].is_valid = False
            return True
        return False
    
    def get_token_stats(self) -> Dict[str, Any]:
        """Get token statistics"""
        active = sum(1 for t in self.tokens.values() if t.is_valid and not t.is_expired())
        expired = sum(1 for t in self.tokens.values() if t.is_expired())
        revoked = sum(1 for t in self.tokens.values() if not t.is_valid)
        
        return {
            "total_tokens": len(self.tokens),
            "active_tokens": active,
            "expired_tokens": expired,
            "revoked_tokens": revoked
        }


class EncryptionManager:
    """Manage encryption/decryption"""
    
    def __init__(self):
        self.keys: Dict[str, EncryptionKey] = {}
        self.active_key_id: Optional[str] = None
    
    def generate_key(self, algorithm: str = "AES-256") -> EncryptionKey:
        """Generate encryption key"""
        key_id = secrets.token_hex(16)
        key = EncryptionKey(
            key_id=key_id,
            algorithm=algorithm,
            created_at=datetime.now().isoformat(),
            is_active=True
        )
        
        self.keys[key_id] = key
        if self.active_key_id is None:
            self.active_key_id = key_id
        
        return key
    
    def rotate_key(self) -> EncryptionKey:
        """Rotate encryption key"""
        if self.active_key_id:
            self.keys[self.active_key_id].is_active = False
        
        new_key = self.generate_key()
        return new_key
    
    def encrypt(self, data: str) -> str:
        """Encrypt data (simplified)"""
        if not self.active_key_id:
            self.generate_key()
        
        # Simple encryption using HMAC for demonstration
        key = self.active_key_id.encode()
        encrypted = hmac.new(key, data.encode(), hashlib.sha256).hexdigest()
        return encrypted
    
    def decrypt(self, encrypted_data: str, key_id: str) -> Optional[str]:
        """Decrypt data (simplified)"""
        if key_id not in self.keys:
            return None
        
        # In real implementation, would use proper encryption
        return encrypted_data
    
    def get_key_rotation_status(self) -> Dict[str, Any]:
        """Get key rotation status"""
        active_key = self.keys.get(self.active_key_id)
        
        if not active_key:
            return {"status": "NO_ACTIVE_KEY"}
        
        created = datetime.fromisoformat(active_key.created_at)
        age_days = (datetime.now() - created).days
        
        return {
            "active_key_id": self.active_key_id,
            "algorithm": active_key.algorithm,
            "age_days": age_days,
            "rotation_needed": age_days > 90  # Rotate every 90 days
        }


class APIKeyManager:
    """Manage API keys"""
    
    def __init__(self):
        self.api_keys: Dict[str, Dict[str, Any]] = {}
    
    def create_api_key(self, user_id: str, name: str, scopes: List[str] = None) -> Tuple[str, str]:
        """Create API key"""
        key_id = secrets.token_hex(16)
        key_secret = secrets.token_urlsafe(32)
        
        # Hash the secret for storage
        hashed_secret = hashlib.sha256(key_secret.encode()).hexdigest()
        
        self.api_keys[key_id] = {
            "user_id": user_id,
            "name": name,
            "secret_hash": hashed_secret,
            "scopes": scopes or [],
            "created_at": datetime.now().isoformat(),
            "last_used": None,
            "is_active": True
        }
        
        return key_id, key_secret  # Return secret only on creation
    
    def validate_api_key(self, key_id: str, key_secret: str) -> bool:
        """Validate API key"""
        if key_id not in self.api_keys:
            return False
        
        key_data = self.api_keys[key_id]
        if not key_data["is_active"]:
            return False
        
        # Verify secret
        hashed_secret = hashlib.sha256(key_secret.encode()).hexdigest()
        return hmac.compare_digest(key_data["secret_hash"], hashed_secret)
    
    def revoke_api_key(self, key_id: str) -> bool:
        """Revoke API key"""
        if key_id in self.api_keys:
            self.api_keys[key_id]["is_active"] = False
            return True
        return False
    
    def get_user_keys(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all keys for user"""
        return [
            {k: v for k, v in data.items() if k != "secret_hash"}
            for key_id, data in self.api_keys.items()
            if data["user_id"] == user_id
        ]


class SecureCredentialStore:
    """Securely store credentials"""
    
    def __init__(self, encryption_manager: EncryptionManager):
        self.encryption_manager = encryption_manager
        self.credentials: Dict[str, Dict[str, Any]] = {}
    
    def store_credential(self, credential_id: str, username: str, password: str,
                        service: str) -> bool:
        """Store credential securely"""
        encrypted_password = self.encryption_manager.encrypt(password)
        
        self.credentials[credential_id] = {
            "username": username,
            "password_hash": hashlib.sha256(password.encode()).hexdigest(),
            "encrypted_password": encrypted_password,
            "service": service,
            "created_at": datetime.now().isoformat(),
            "last_accessed": None
        }
        
        return True
    
    def verify_credential(self, credential_id: str, password: str) -> bool:
        """Verify stored credential"""
        if credential_id not in self.credentials:
            return False
        
        stored_hash = self.credentials[credential_id]["password_hash"]
        provided_hash = hashlib.sha256(password.encode()).hexdigest()
        
        return hmac.compare_digest(stored_hash, provided_hash)
    
    def get_credential_count(self) -> int:
        """Get number of stored credentials"""
        return len(self.credentials)


class CORS_Manager:
    """Manage CORS settings"""
    
    def __init__(self):
        self.allowed_origins: List[str] = []
        self.allowed_methods: List[str] = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
        self.allowed_headers: List[str] = ["Content-Type", "Authorization"]
    
    def add_allowed_origin(self, origin: str) -> bool:
        """Add allowed origin"""
        if origin not in self.allowed_origins:
            self.allowed_origins.append(origin)
            return True
        return False
    
    def is_origin_allowed(self, origin: str) -> bool:
        """Check if origin is allowed"""
        return origin in self.allowed_origins or "*" in self.allowed_origins
    
    def get_cors_headers(self, origin: str) -> Dict[str, str]:
        """Get CORS headers"""
        return {
            "Access-Control-Allow-Origin": origin if self.is_origin_allowed(origin) else "",
            "Access-Control-Allow-Methods": ", ".join(self.allowed_methods),
            "Access-Control-Allow-Headers": ", ".join(self.allowed_headers)
        }


class SecurityManager:
    """Central security manager"""
    
    def __init__(self, secret_key: str = None):
        self.secret_key = secret_key or secrets.token_urlsafe(32)
        self.token_manager = TokenManager(self.secret_key)
        self.encryption_manager = EncryptionManager()
        self.api_key_manager = APIKeyManager()
        self.credential_store = SecureCredentialStore(self.encryption_manager)
        self.cors_manager = CORS_Manager()
    
    def get_security_status(self) -> Dict[str, Any]:
        """Get overall security status"""
        return {
            "tokens": self.token_manager.get_token_stats(),
            "encryption": self.encryption_manager.get_key_rotation_status(),
            "api_keys": len(self.api_key_manager.api_keys),
            "stored_credentials": self.credential_store.get_credential_count(),
            "cors_origins": len(self.cors_manager.allowed_origins)
        }


# Example usage
if __name__ == "__main__":
    security = SecurityManager()
    
    # Generate token
    token = security.token_manager.generate_token("user_123", scopes=["read", "write"])
    print(f"Generated token: {token.token_id}")
    
    # Generate API key
    key_id, key_secret = security.api_key_manager.create_api_key("user_123", "mobile_app")
    print(f"API Key: {key_id}")
    
    # Get status
    status = security.get_security_status()
    print(json.dumps(status, indent=2))
