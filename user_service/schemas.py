from pydantic import BaseModel
from typing import Optional

# =====================================================================
# PYDANTIC SCHEMAS MODULE (User Service)
# This module defines schemas for Request/Response validation.
# Separation of concerns:
#   - Database Models (models.py): Represent rows in SQL.
#   - Pydantic Schemas (schemas.py): Represent HTTP request & response payloads.
# =====================================================================

# Base schema containing fields shared between creation and reading requests
class UserBase(BaseModel):
    name: str
    email: str
    role: Optional[str] = "customer"

# Schema for incoming request data when creating a new User
class UserCreate(UserBase):
    pass # Inherits name, email, and optional role

# Schema for incoming request data when updating an existing User
class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None

# Schema representing the structured response returned to the client
class User(UserBase):
    id: int
    role: str = "customer"

    class Config:
        # Configures Pydantic to read ORM objects (like SQLAlchemy instances) 
        # instead of only standard dictionary structures.
        from_attributes = True
