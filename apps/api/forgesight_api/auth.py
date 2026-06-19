import os
from datetime import datetime, timedelta
from typing import Optional

from argon2 import PasswordHasher
from jose import jwt, JWTError
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from forgesight_api.db.session import SessionLocal
from forgesight_api.db.models import User

SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 60 * 24))

ph = PasswordHasher()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def hash_password(password: str) -> str:
    return ph.hash(password)


def verify_password(hash: str, password: str) -> bool:
    try:
        return ph.verify(hash, password)
    except Exception:
        return False


def create_access_token(*, data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    encoded = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded


async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    # Developer/testing override
    if os.getenv("DISABLE_AUTH", "0") == "1":
        session = SessionLocal()
        try:
            user = session.query(User).first()
            if user:
                return user
            # create a default dev user
            u = User(email="dev@local", password_hash=hash_password("devpass"), display_name="Dev", role="admin")
            session.add(u)
            session.commit()
            session.refresh(u)
            return u
        finally:
            session.close()

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str | None = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    session = SessionLocal()
    try:
        user = session.query(User).filter(User.email == email).one_or_none()
        if user is None:
            raise credentials_exception
        return user
    finally:
        session.close()
