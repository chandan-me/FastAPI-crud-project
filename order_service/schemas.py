from pydantic import BaseModel, Field
from typing import Optional, List

class OrderBase(BaseModel):
    user_id: int
    product_id: int
    quantity: int = Field(..., gt=0)
    payment_method: Optional[str] = "COD"
    payment_id: Optional[str] = None
    order_group_id: Optional[str] = None

class OrderCreate(OrderBase):
    pass

class OrderUpdate(BaseModel):
    status: Optional[str] = None
    payment_method: Optional[str] = None
    payment_id: Optional[str] = None
    order_group_id: Optional[str] = None

class Order(OrderBase):
    id: int
    total_price: float
    status: str

    class Config:
        from_attributes = True

class OrderDetail(Order):
    user_details: Optional[dict] = None
    product_details: Optional[dict] = None

class CartItemCheckout(BaseModel):
    product_id: int
    quantity: int = Field(..., gt=0)

class CheckoutRequest(BaseModel):
    user_id: Optional[int] = None
    items: List[CartItemCheckout]
    payment_method: Optional[str] = "COD"
    payment_id: Optional[str] = None

class RazorpayCreateOrderRequest(BaseModel):
    amount: float
    currency: Optional[str] = "INR"

class RazorpayVerifyRequest(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str
    items: List[CartItemCheckout]
    user_id: Optional[int] = None
