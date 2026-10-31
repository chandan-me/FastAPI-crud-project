from pydantic import BaseModel, Field
from typing import Optional

class OrderBase(BaseModel):
    user_id: int
    product_id: int
    quantity: int = Field(..., gt=0)

class OrderCreate(OrderBase):
    pass

class OrderUpdate(BaseModel):
    status: Optional[str] = None

class Order(OrderBase):
    id: int
    total_price: float
    status: str

    class Config:
        from_attributes = True

class OrderDetail(Order):
    user_details: Optional[dict] = None
    product_details: Optional[dict] = None
