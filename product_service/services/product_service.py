from sqlalchemy.orm import Session
from typing import Optional
import httpx
from fastapi import HTTPException
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

def get_products(
    db: Session, 
    q: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    in_stock: Optional[bool] = None,
    skip: int = 0, 
    limit: int = 100
):
    """
    Returns a list of products supporting pagination, name search, price range filtering, and stock filtering.
    """
    query = db.query(models.Product)
    if q and q.strip():
        query = query.filter(models.Product.name.ilike(f"%{q.strip()}%"))
    if min_price is not None:
        query = query.filter(models.Product.price >= min_price)
    if max_price is not None:
        query = query.filter(models.Product.price <= max_price)
    if in_stock is True:
        query = query.filter(models.Product.stock > 0)
    elif in_stock is False:
        query = query.filter(models.Product.stock == 0)
    return query.offset(skip).limit(limit).all()

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

def restore_stock(db: Session, db_product: models.Product, quantity: int):
    """
    Restores inventory quantity for a product (e.g. upon order cancellation or restocking).
    """
    db_product.stock += quantity
    db.commit()
    db.refresh(db_product)
    return db_product

async def delete_product(db: Session, db_product: models.Product):
    """
    Safely deletes a product from the catalog after asserting no orders depend on it.
    """
    ORDER_SERVICE_URL = "http://localhost:8013"
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            res = await client.get(f"{ORDER_SERVICE_URL}/orders")
            if res.status_code == 200:
                orders = res.json()
                matching_orders = [o for o in orders if o.get("product_id") == db_product.id]
                if matching_orders:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Cannot delete product '{db_product.name}' (ID: {db_product.id}) because it is referenced in {len(matching_orders)} existing order(s). Consider updating stock to 0 instead."
                    )
    except httpx.RequestError:
        pass

    db.delete(db_product)
    db.commit()
    return {"message": f"Product #{db_product.id} ('{db_product.name}') deleted successfully"}
