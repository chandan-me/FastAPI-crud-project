from sqlalchemy.orm import Session
from .. import models, schemas

# =====================================================================
# SERVICE LAYER MODULE (Product Service)
# This module encapsulates core database query logic and transactions.
# Separating query operations into a Service layer allows for reusability,
# easier testing, and keeps route handlers (routers) lightweight.
# =====================================================================

def get_product_by_id(db: Session, product_id: int):
    """
    Fetches a single product record by its primary key ID.
    """
    return db.query(models.Product).filter(models.Product.id == product_id).first()

def get_products(db: Session, skip: int = 0, limit: int = 100):
    """
    Returns a list of products supporting pagination (offset/limit).
    """
    return db.query(models.Product).offset(skip).limit(limit).all()

def create_product(db: Session, product: schemas.ProductCreate):
    """
    Inserts a new product record into the database catalog.
    """
    db_product = models.Product(name=product.name, price=product.price, stock=product.stock)
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product

def reduce_stock(db: Session, db_product: models.Product, quantity: int):
    """
    Deducts a specific quantity from the stock inventory of a product.
    Note: The calling handler must assert sufficient stock availability beforehand.
    """
    db_product.stock -= quantity
    db.commit()
    db.refresh(db_product)
    return db_product

def update_product(db: Session, db_product: models.Product, product_update: schemas.ProductUpdate):
    """
    Modifies specific properties of a product dynamically.
    Only fields sent in the request body (exclude_unset=True) will be updated.
    """
    update_data = product_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_product, key, value) # Apply updates to database model attributes
    db.commit()
    db.refresh(db_product)
    return db_product
