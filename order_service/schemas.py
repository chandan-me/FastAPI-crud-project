from pydantic import BaseModel, Field
from typing import Optional

# =====================================================================
# PYDANTIC SCHEMAS MODULE (Order Service)
# This module defines schemas for Request/Response validation.
# Separation of concerns:
#   - Database Models (models.py): Represent rows in SQL.
#   - Pydantic Schemas (schemas.py): Represent HTTP request & response payloads.
# =====================================================================

# Base schema containing fields shared between creation and reading requests
class OrderBase(BaseModel):
    user_id: int
    product_id: int
    quantity: int = Field(..., gt=0) # Must buy at least 1 item

# Schema for incoming request data when creating a new Order
class OrderCreate(OrderBase):
    pass

# Schema representing the structured response returned to the client
class Order(OrderBase):
    id: int
    total_price: float
    status: str

    class Config:
        # Configures Pydantic to read ORM objects (like SQLAlchemy instances) 
        # instead of only standard dictionary structures.
        from_attributes = True

# Aggregated detailed schema representing federated data from multiple services
# This combines:
#   1. Order database details (id, status, quantity, total_price)
#   2. User Service data (name, email)
#   3. Product Service data (name, price)
class OrderDetail(Order):
    user_details: Optional[dict] = None
    product_details: Optional[dict] = None
