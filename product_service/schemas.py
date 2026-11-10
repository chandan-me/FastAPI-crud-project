from pydantic import BaseModel, Field
from typing import Optional

class ProductBase(BaseModel):
    name: str
    price: float = Field(..., gt=0)
    stock: int = Field(..., ge=0)
    image_url: Optional[str] = None
    is_blocked: Optional[bool] = False

class ProductCreate(ProductBase):
    pass

class ProductUpdate(BaseModel):
    name: Optional[str] = None
    price: Optional[float] = Field(None, gt=0)
    stock: Optional[int] = Field(None, ge=0)
    image_url: Optional[str] = None
    is_blocked: Optional[bool] = None

class ProductReduceStock(BaseModel):
    quantity: int = Field(..., gt=0)

class Product(ProductBase):
    id: int
    is_blocked: bool = False

    class Config:
        from_attributes = True
