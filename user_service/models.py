from sqlalchemy import Column, Integer, String
from .database import Base

# =====================================================================
# DATABASE MODEL MODULE (User Service)
# This module defines the SQL schema representations (SQLAlchemy models).
# Database models specify tables, columns, indexes, and primary/foreign keys.
# =====================================================================

class User(Base):
    # Specify the exact table name in the MySQL database schema
    __tablename__ = "users"

    # ID: Primary key, automatically increments on insertion
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # Name: User display name, limited to 255 characters, required
    name = Column(String(255), nullable=False)
    
    # Email: Must be unique, indexed for quick lookups, required
    email = Column(String(255), unique=True, index=True, nullable=False)
