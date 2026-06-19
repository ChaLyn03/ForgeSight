from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr

from forgesight_api.db.session import SessionLocal
from forgesight_api.db.models import User
from forgesight_api.auth import create_access_token, get_current_user, hash_password, verify_password

router = APIRouter()


class RegisterIn(BaseModel):
    email: EmailStr
    password: str
    display_name: str | None = None
    role: str | None = "inspector"


class LoginIn(BaseModel):
    email: EmailStr
    password: str


@router.post("/auth/register")
async def register(payload: RegisterIn):
    session = SessionLocal()
    try:
        existing = session.query(User).filter(User.email == payload.email).one_or_none()
        if existing:
            raise HTTPException(status_code=400, detail="Email already registered")

        user = User(
            email=payload.email,
            password_hash=hash_password(payload.password),
            display_name=payload.display_name,
            role=payload.role,
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        return {"user": {"id": user.id, "email": user.email, "displayName": user.display_name, "role": user.role}}
    finally:
        session.close()


@router.post("/auth/login")
async def login(payload: LoginIn):
    session = SessionLocal()
    try:
        user = session.query(User).filter(User.email == payload.email).one_or_none()
        if not user or not verify_password(user.password_hash, payload.password):
            raise HTTPException(status_code=401, detail="Invalid credentials")

        token = create_access_token(data={"sub": user.email})
        return {"access_token": token, "token_type": "bearer", "user": {"id": user.id, "email": user.email, "displayName": user.display_name, "role": user.role}}
    finally:
        session.close()


@router.get("/auth/me")
async def me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "email": current_user.email,
        "displayName": current_user.display_name,
        "role": current_user.role,
    }
