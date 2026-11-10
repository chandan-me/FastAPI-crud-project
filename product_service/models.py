from sqlalchemy import Column, Integer, String, Float, Text, Boolean

try:
    from .database import Base
except ImportError:
    from database import Base

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    price = Column(Float, nullable=False)
    stock = Column(Integer, nullable=False)
    image_url = Column(Text, nullable=True)
    is_blocked = Column(Boolean, default=False, nullable=False) # 0 = Active, 1 = Blocked
