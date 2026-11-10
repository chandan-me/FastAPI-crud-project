from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class UserBase(BaseModel):
    name: str
    email: str
    role: Optional[str] = "customer"
    is_blocked: Optional[bool] = False
    profile_image: Optional[str] = None

class UserCreate(UserBase):
    password: str

class UserLogin(BaseModel):
    email: str
    password: str

class UserTokenUpdate(BaseModel):
    access_token: Optional[str] = None
    token_expires_at: Optional[datetime] = None
    last_login: Optional[datetime] = None

class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    password: Optional[str] = None
    role: Optional[str] = None
    is_blocked: Optional[bool] = None
    profile_image: Optional[str] = None

class User(UserBase):
    id: int
    role: str = "customer"
    is_blocked: bool = False
    access_token: Optional[str] = None
    token_expires_at: Optional[datetime] = None
    last_login: Optional[datetime] = None
    profile_image: Optional[str] = None

    class Config:
        from_attributes = True

class UserWithPassword(User):
    password: Optional[str] = None
