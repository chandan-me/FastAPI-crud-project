from pydantic import BaseModel

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

# Schema for incoming request data when creating a new User
class UserCreate(UserBase):
    pass # Inherits name and email from UserBase

# Schema representing the structured response returned to the client
class User(UserBase):
    id: int # The returned object will include the database-generated ID

    class Config:
        # Configures Pydantic to read ORM objects (like SQLAlchemy instances) 
        # instead of only standard dictionary structures.
        from_attributes = True
