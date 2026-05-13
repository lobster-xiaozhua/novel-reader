from datetime import datetime, timedelta
from typing import Optional, Tuple
import hashlib
import hmac
import base64
import secrets

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jwt import PyJWTError as JWTError, encode, decode

from .config import get_settings

settings = get_settings()
security = HTTPBearer()


def hash_password(password: str) -> str:
    """使用纯Python的PBKDF2-HMAC-SHA256进行密码哈希（跨平台兼容）"""
    salt = secrets.token_bytes(16)
    password_bytes = password.encode("utf-8")
    hashed = hashlib.pbkdf2_hmac(
        "sha256",
        password_bytes,
        salt,
        iterations=100000
    )
    salt_b64 = base64.b64encode(salt).decode("utf-8")
    hash_b64 = base64.b64encode(hashed).decode("utf-8")
    return f"pbkdf2_sha256$100000${salt_b64}${hash_b64}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码（纯Python实现）"""
    try:
        if hashed_password.startswith("pbkdf2_sha256$"):
            parts = hashed_password.split("$")
            if len(parts) != 4:
                return False
            algo, iterations_str, salt_b64, hash_b64 = parts
            iterations = int(iterations_str)
            
            password_bytes = plain_password.encode("utf-8")
            salt = base64.b64decode(salt_b64.encode("utf-8"))
            expected_hash = base64.b64decode(hash_b64.encode("utf-8"))
            
            computed_hash = hashlib.pbkdf2_hmac(
                "sha256",
                password_bytes,
                salt,
                iterations
            )
            
            return hmac.compare_digest(computed_hash, expected_hash)
        else:
            try:
                import bcrypt
                return bcrypt.checkpw(
                    plain_password.encode("utf-8"),
                    hashed_password.encode("utf-8"),
                )
            except ImportError:
                return False
    except (ValueError, TypeError, IndexError):
        return False


def validate_password_strength(password: str) -> Tuple[bool, str]:
    if len(password) < settings.PASSWORD_MIN_LENGTH:
        return False, f"密码至少 {settings.PASSWORD_MIN_LENGTH} 位"
    if not any(c.isupper() for c in password):
        return False, "需要包含大写字母"
    if not any(c.islower() for c in password):
        return False, "需要包含小写字母"
    if not any(c.isdigit() for c in password):
        return False, "需要包含数字"
    return True, "密码强度合格"


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire, "type": "access"})
    return encode(to_encode, settings.SECRET_KEY, algorithm="HS256")


def create_refresh_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    return encode(to_encode, settings.SECRET_KEY, algorithm="HS256")


def decode_token(token: str) -> Optional[dict]:
    try:
        payload = decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        return payload
    except JWTError:
        return None


async def get_current_user_id(credentials: HTTPAuthorizationCredentials = Depends(security)) -> int:
    token = credentials.credentials
    payload = decode_token(token)

    if not payload or payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证令牌",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id: int = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证令牌",
        )

    return int(user_id)


async def get_current_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    return credentials.credentials


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    from app.database import AsyncSessionLocal
    from app.models import User
    from sqlalchemy import select
    
    token = credentials.credentials
    payload = decode_token(token)
    
    if not payload or payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证令牌",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证令牌",
        )
    
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.id == int(user_id)))
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户不存在",
            )
        
        return user


def require_admin(user):
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限",
        )
