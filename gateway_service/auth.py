import os
import jwt
from datetime import datetime, timedelta
from typing import Optional
from dotenv import load_dotenv

# =====================================================================
# JWT AUTHENTICATION GATEKEEPER (API Gateway)
# This module is responsible for encoding and decoding JSON Web Tokens.
# It enforces user authentication checks at the gateway boundary.
# =====================================================================

# Load root-level .env file
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

SECRET_KEY = os.getenv("JWT_SECRET", "default_secret_key_change_me")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = 1

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Generates a secure signed JWT token containing user identity details."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    # Add token expiration timestamp
    to_encode.update({"exp": expire})
    # Encode and sign the JWT payload
    print(f"Creating JWT token with payload: {to_encode}")
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    print(f"Encoded JWT token: {encoded_jwt}")
    return encoded_jwt

def decode_access_token(token: str) -> Optional[dict]:
    """Decodes and validates a JWT token. Returns payload if valid, None if expired/corrupted."""
    try:
        decoded_payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return decoded_payload
    except jwt.PyJWTError:
        return None
