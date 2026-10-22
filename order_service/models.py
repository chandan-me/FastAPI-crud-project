from sqlalchemy import Column, Integer, Float, String
from .database import Base

# =====================================================================
# DATABASE MODEL MODULE (Order Service)
# This module defines the SQL schema representations (SQLAlchemy models).
# Database models specify tables, columns, indexes, and primary/foreign keys.
# =====================================================================

class Order(Base):
    # Specify the exact table name in the MySQL database schema
    __tablename__ = "orders"

    # ID: Primary key, automatically increments on insertion
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # User ID: Relates to a user in the User Service DB (Logical/soft relationship)
    user_id = Column(Integer, nullable=False, index=True)
    
    # Product ID: Relates to a product in the Product Service DB (Logical/soft relationship)
    product_id = Column(Integer, nullable=False, index=True)
    
    # Quantity: Number of items bought in this order
    quantity = Column(Integer, nullable=False)
    
    # Total Price: Sum cost calculated dynamically as (unit_price * quantity)
    total_price = Column(Float, nullable=False)
    
    # Status: Current status of the order transaction (PENDING, COMPLETED, etc.)
    status = Column(String(50), default="PENDING")
