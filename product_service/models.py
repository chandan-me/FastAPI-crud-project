from sqlalchemy import Column, Integer, String, Float
from .database import Base

# =====================================================================
# DATABASE MODEL MODULE (Product Service)
# This module defines the SQL schema representations (SQLAlchemy models).
# Database models specify tables, columns, indexes, and primary/foreign keys.
# =====================================================================

class Product(Base):
    # Specify the exact table name in the MySQL database schema
    __tablename__ = "products"

    # ID: Primary key, automatically increments on insertion
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # Name: Product catalog item name, limited to 255 characters, required
    name = Column(String(255), nullable=False)
    
    # Price: Unit cost of the product (represented as floating-point float)
    price = Column(Float, nullable=False)
    
    # Stock: Inventory quantity left in database, required
    stock = Column(Integer, nullable=False)
