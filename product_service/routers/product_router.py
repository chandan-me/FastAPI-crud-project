from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from .. import schemas, database
from ..services import product_service

# =====================================================================
# API ROUTER MODULE (Product Service)
# This module defines the HTTP endpoints (routes) for the Product Service.
# Routers are responsible for mapping HTTP methods (GET, POST, etc.) and paths
# to controller functions, injecting DB dependencies, and raising HTTP exceptions.
# =====================================================================

# Initialize the router with a prefix so all endpoints start with '/products'
router = APIRouter(prefix="/products", tags=["products"])

@router.post("", response_model=schemas.Product, status_code=status.HTTP_201_CREATED, include_in_schema=False)
@router.post("/", response_model=schemas.Product, status_code=status.HTTP_201_CREATED)
def create_product(product: schemas.ProductCreate, db: Session = Depends(database.get_db)):
    """
    Endpoint to create a new product in the catalog.
    """
    return product_service.create_product(db=db, product=product)

@router.get("", response_model=List[schemas.Product], include_in_schema=False)
@router.get("/", response_model=List[schemas.Product])
def read_products(
    q: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    in_stock: Optional[bool] = None,
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(database.get_db)
):
    """
    Endpoint to list products with pagination, search, price range and stock filtering.
    """
    return product_service.get_products(
        db, 
        q=q, 
        min_price=min_price, 
        max_price=max_price, 
        in_stock=in_stock, 
        skip=skip, 
        limit=limit
    )

@router.get("/{product_id}", response_model=schemas.Product)
def read_product(product_id: int, db: Session = Depends(database.get_db)):
    """
    Endpoint to retrieve details of a specific product.
    This is also called internally by the Order Service to validate product existance & pricing.
    """
    db_product = product_service.get_product_by_id(db, product_id=product_id)
    if db_product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return db_product

@router.put("/{product_id}/reduce-stock", response_model=schemas.Product)
def reduce_stock(product_id: int, payload: schemas.ProductReduceStock, db: Session = Depends(database.get_db)):
    """
    Endpoint to reduce inventory stock for a product.
    Called by the Order Service during transaction handling to reserve items.
    """
    db_product = product_service.get_product_by_id(db, product_id=product_id)
    if db_product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Assert sufficient stock level
    if db_product.stock < payload.quantity:
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient stock. Available: {db_product.stock}, Requested: {payload.quantity}"
        )
    
    # Process stock deduction transaction
    return product_service.reduce_stock(db=db, db_product=db_product, quantity=payload.quantity)

@router.put("/{product_id}/restore-stock", response_model=schemas.Product)
def restore_stock(product_id: int, payload: schemas.ProductReduceStock, db: Session = Depends(database.get_db)):
    """
    Endpoint to restore inventory stock for a product (e.g. upon order cancellation).
    """
    db_product = product_service.get_product_by_id(db, product_id=product_id)
    if db_product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    
    return product_service.restore_stock(db=db, db_product=db_product, quantity=payload.quantity)

@router.put("/{product_id}", response_model=schemas.Product)
def update_product(product_id: int, payload: schemas.ProductUpdate, db: Session = Depends(database.get_db)):
    """
    Endpoint to update name, price, or stock levels of a product (e.g. restocking).
    """
    db_product = product_service.get_product_by_id(db, product_id=product_id)
    if db_product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Process dynamic properties updates
    return product_service.update_product(db=db, db_product=db_product, product_update=payload)

@router.delete("/{product_id}", status_code=status.HTTP_200_OK)
async def delete_product(product_id: int, db: Session = Depends(database.get_db)):
    """
    Endpoint to safely delete a product if no orders depend on it.
    """
    db_product = product_service.get_product_by_id(db, product_id=product_id)
    if db_product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    
    return await product_service.delete_product(db=db, db_product=db_product)
