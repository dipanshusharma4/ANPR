from passlib.context import CryptContext
from jose import jwt, JWTError
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv("JWT_SECRET")
ALGORITHM = os.getenv("JWT_ALGORITHM")


pwd_context = CryptContext(schemes=["bcrypt_sha256", "pbkdf2_sha256"], deprecated="auto")

def hash_password(password: str) -> str:
    """Hash a password safely.

    Uses the preferred scheme (bcrypt_sha256). If hashing fails (e.g. backend error),
    fall back to a supported scheme to avoid raising a ValueError at runtime.
    """
    try:
        return pwd_context.hash(password)
    except ValueError:
        return pwd_context.hash(password, scheme="pbkdf2_sha256")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta=timedelta(hours=1)):
    to_encode = data.copy()
    to_encode.update({"exp": datetime.utcnow() + expires_delta})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def decode_access_token(token: str):
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None
