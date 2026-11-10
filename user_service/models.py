from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean

try:
    from .database import Base
except ImportError:
    from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    role = Column(String(50), default="customer", nullable=False)
    password = Column(String(255), nullable=True) # Bcrypt hashed password
    is_blocked = Column(Boolean, default=False, nullable=False) # 0 = Active, 1 = Blocked
    profile_image = Column(Text, nullable=True)        # User profile photo URL
    access_token = Column(Text, nullable=True)     # Active JWT access token
    token_expires_at = Column(DateTime, nullable=True) # Expiration date & time
    last_login = Column(DateTime, nullable=True)       # Timestamp of last login
