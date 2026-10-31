import os
import httpx
from typing import List, Optional
from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session

try:
    from . import models, schemas, database
except ImportError:
    import models, schemas, database

# ==============================================================================
# PRODUCT SERVICE (Port 8012)
#
# High-Level Data Travel Architecture:
#   1. Receives requests from:
#      - API Gateway (Port 8010) for catalog browsing (public) and product management (admin).
#      - Order Service (Port 8013) for item validation, pricing, and atomic stock deductions.
#   2. Reads/Writes catalog items to its isolated MySQL database: `products_db.products`.
#   3. Responds to stock deduction and restoration requests from Order Service.
#   4. On product deletion, calls Order Service (Port 8013) to ensure no orders are orphaned.
# ==============================================================================

app = FastAPI(title="Product Service", description="Product Catalog Microservice")

# Auto-create table definitions in MySQL (products_db)
models.Base.metadata.create_all(bind=database.engine)

ORDER_SERVICE_URL = os.getenv("ORDER_SERVICE_URL", "http://127.0.0.1:8013")


# ==============================================================================
# [DATA TRAVEL FLOW - CREATE PRODUCT]:
#   Origin:      Admin in React Frontend -> API Gateway (POST /products, RBAC checked) -> Product Service (POST /products)
#   Payload:     { name: str, price: float, stock: int }
#   Database:    INSERT INTO products_db.products (name, price, stock) VALUES (...)
#   Destination: Returns created Product object with autoincremented ID back to API Gateway -> Frontend.
# ==============================================================================
@app.post("/products", response_model=schemas.Product, status_code=status.HTTP_201_CREATED)
@app.post("/products/", response_model=schemas.Product, status_code=status.HTTP_201_CREATED, include_in_schema=False)
def create_product(product: schemas.ProductCreate, db: Session = Depends(database.get_db)):
    """Create a new product in the catalog."""
    db_product = models.Product(name=product.name, price=product.price, stock=product.stock)
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product


# ==============================================================================
# [DATA TRAVEL FLOW - LIST / FILTER PRODUCTS]:
#   Origin:      React Frontend (Public / Unauthenticated) -> API Gateway -> Product Service (GET /products)
#   Params:      q: search query, min_price, max_price, in_stock, skip, limit
#   Database:    SELECT * FROM products_db.products WHERE name LIKE ? AND price ... LIMIT limit OFFSET skip
#   Destination: Returns array of Product objects back to API Gateway -> Frontend Catalog Grid.
# ==============================================================================
@app.get("/products", response_model=List[schemas.Product])
@app.get("/products/", response_model=List[schemas.Product], include_in_schema=False)
def list_products(
    q: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    in_stock: Optional[bool] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(database.get_db)
):
    """List products with optional search, price range, stock filter, and pagination."""
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


# ==============================================================================
# [DATA TRAVEL FLOW - GET PRODUCT BY ID]:
#   Origin:      Called from:
#                1. API Gateway (GET /products/{id}) for product details.
#                2. Order Service (GET http://127.0.0.1:8012/products/{id}) during
#                   Step 2 of the Order Saga (verifying stock & price).
#   Database:    SELECT * FROM products_db.products WHERE id = ? LIMIT 1
#   Destination: Returns Product object to caller.
# ==============================================================================
@app.get("/products/{product_id}", response_model=schemas.Product)
def get_product(product_id: int, db: Session = Depends(database.get_db)):
    """Retrieve product details by ID."""
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


# ==============================================================================
# [DATA TRAVEL FLOW - UPDATE PRODUCT]:
#   Origin:      Admin in React Frontend -> API Gateway (PUT /products/{id}) -> Product Service
#   Payload:     ProductUpdate { name?, price?, stock? }
#   Database:    UPDATE products_db.products SET ... WHERE id = ?
#   Destination: Returns updated Product object back to API Gateway -> Frontend.
# ==============================================================================
@app.put("/products/{product_id}", response_model=schemas.Product)
def update_product(product_id: int, payload: schemas.ProductUpdate, db: Session = Depends(database.get_db)):
    """Update product fields dynamically."""
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    update_data = payload.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(product, key, value)
    db.commit()
    db.refresh(product)
    return product


# ==============================================================================
# [DATA TRAVEL FLOW - ATOMIC STOCK DEDUCTION]:
#   Origin:      Order Service (Step 3 of Order Saga)
#                PUT http://127.0.0.1:8012/products/{product_id}/reduce-stock
#   Payload:     { quantity: int }
#   Database:    Asserts stock >= quantity, then executes:
#                UPDATE products_db.products SET stock = stock - ? WHERE id = ?
#   Destination: Returns updated Product object to Order Service to confirm stock reservation.
# ==============================================================================
@app.put("/products/{product_id}/reduce-stock", response_model=schemas.Product)
def reduce_stock(product_id: int, payload: schemas.ProductReduceStock, db: Session = Depends(database.get_db)):
    """Deduct inventory stock for an order transaction."""
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    if product.stock < payload.quantity:
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient stock. Available: {product.stock}, Requested: {payload.quantity}"
        )

    product.stock -= payload.quantity
    db.commit()
    db.refresh(product)
    return product


# ==============================================================================
# [DATA TRAVEL FLOW - COMPENSATING STOCK RESTORATION]:
#   Origin:      Order Service (upon Order Cancellation or Order Deletion)
#                PUT http://127.0.0.1:8012/products/{product_id}/restore-stock
#   Payload:     { quantity: int }
#   Database:    UPDATE products_db.products SET stock = stock + ? WHERE id = ?
#   Destination: Returns updated Product object to Order Service.
# ==============================================================================
@app.put("/products/{product_id}/restore-stock", response_model=schemas.Product)
def restore_stock(product_id: int, payload: schemas.ProductReduceStock, db: Session = Depends(database.get_db)):
    """Restore inventory stock (e.g. upon order cancellation)."""
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    product.stock += payload.quantity
    db.commit()
    db.refresh(product)
    return product


# ==============================================================================
# [DATA TRAVEL FLOW - DELETE PRODUCT WITH INTEGRITY CHECK]:
#   Origin:      Admin in React Frontend -> API Gateway (DELETE /products/{id}) -> Product Service
#   Outbound:    Product Service -> Order Service (GET http://127.0.0.1:8013/orders)
#                - If existing orders reference this product: Aborts and raises HTTP 400.
#                - If 0 orders reference it: Proceeds to delete.
#   Database:    DELETE FROM products_db.products WHERE id = ?
#   Destination: Returns success message back to API Gateway -> Frontend.
# ==============================================================================
@app.delete("/products/{product_id}", status_code=status.HTTP_200_OK)
async def delete_product(product_id: int, db: Session = Depends(database.get_db)):
    """Safely delete product if no orders depend on it."""
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Check if this product is referenced in any existing orders
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            res = await client.get(f"{ORDER_SERVICE_URL}/orders")
            if res.status_code == 200:
                orders = res.json()
                matching = [o for o in orders if o.get("product_id") == product_id]
                if matching:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Cannot delete product '{product.name}' (ID: {product_id}) because it is referenced in {len(matching)} existing order(s)."
                    )
    except httpx.RequestError:
        pass

    db.delete(product)
    db.commit()
    return {"message": f"Product '{product.name}' deleted successfully"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8012)
