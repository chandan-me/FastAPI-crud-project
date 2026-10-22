from pydantic import BaseModel, Field
from typing import Optional

# =====================================================================
# PYDANTIC SCHEMAS MODULE (Product Service)
# This module defines schemas for Request/Response validation.
# Separation of concerns:
#   - Database Models (models.py): Represent rows in SQL.
#   - Pydantic Schemas (schemas.py): Represent HTTP request & response payloads.
# =====================================================================

# Base schema containing fields shared between creation and reading requests
class ProductBase(BaseModel):
    name: str
    price: float = Field(..., gt=0) # Price must be strictly greater than 0
    stock: int = Field(..., ge=0)   # Stock must be greater than or equal to 0 (cannot be negative)

# Schema for incoming request data when creating a new Product
class ProductCreate(ProductBase):
    pass

# Schema for incoming request data when updating fields of a Product (all fields optional)
class ProductUpdate(BaseModel):
    name: Optional[str] = None
    price: Optional[float] = Field(None, gt=0)
    stock: Optional[int] = Field(None, ge=0)

# Schema representing parameters for deducting items from stock (order validation)
class ProductReduceStock(BaseModel):
    quantity: int = Field(..., gt=0) # Quantity requested to deduct must be greater than 0

# Schema representing the structured response returned to the client
class Product(ProductBase):
    id: int # The returned object will include the database-generated ID

    class Config:
        # Configures Pydantic to read ORM objects (like SQLAlchemy instances) 
        # instead of only standard dictionary structures.
        from_attributes = True
