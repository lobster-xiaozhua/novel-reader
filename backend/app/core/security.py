from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
import bcrypt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import get_settings
from app.database import get_db
from app.models import User

settings = get_settings()
security = HTTPBearer()

def hash_password(password: str):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(rounds=settings.BCRYPT_ROUNDS)).decode('utf-8')

def verify_password(plain: str, hashed: str):
    try:
        return bcrypt.checkpw(plain.encode('utf-8'), hashed.encode('utf-8'))
    except Exception:
        return False

def validate_password_strength(password):
    if len(password) < settings.PASSWORD_MIN_LENGTH:
        return False, f"Need at least {settings.PASSWORD_MIN_LENGTH} chars"
    if not any(c.isupper() for c in password):
        return False, "Need uppercase letter"
    if not any(c.islower() for c in password):
        return False, "Need lowercase letter"
    if not any(c.isdigit() for c in password):
        return False, "Need digit"
    return True, "OK"

def create_access_token(data: dict, exp_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    exp = datetime.utcnow() + (exp_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({'exp': exp, 'type': 'access'})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm='HS256')

def create_refresh_token(data: dict):
    to_encode = data.copy()
    exp = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({'exp': exp, 'type': 'refresh'})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm='HS256')

def decode_token(token):
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
    except JWTError:
        return None

async def _validate_get_payload(credentials):
    token = credentials.credentials
    from app.services.auth_service import auth_service
    if await auth_service.is_token_blacklisted(token):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token", headers={"WWW-Authenticate": "Bearer"})
    payload = decode_token(token)
    if not payload or payload.get('type') != 'access':
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token", headers={"WWW-Authenticate": "Bearer"})
    return payload

async def get_current_user_id(credentials=Depends(security)):
    payload = await _validate_get_payload(credentials)
    user_id = payload.get('sub')
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    try:
        return int(user_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

async def get_current_token(credentials=Depends(security)):
    return credentials.credentials

async def get_current_user(credentials=Depends(security), db=Depends(get_db)):
    user_id = await get_current_user_id(credentials)
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user

def require_admin(user):
    if not user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin required")
    return user