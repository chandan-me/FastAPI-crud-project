from sqlalchemy.orm import Session
import httpx
from fastapi import HTTPException
from typing import Optional
from .. import models, schemas

# =====================================================================
# SERVICE LAYER MODULE (Order Service)
# This module encapsulates core database query logic and is responsible
# for inter-service communication over HTTP using 'httpx.AsyncClient'.
# =====================================================================

# Hardcoded service endpoints (typically these are loaded from env configurations)
USER_SERVICE_URL = "http://localhost:8011"
PRODUCT_SERVICE_URL = "http://localhost:8012"

def get_order_by_id(db: Session, order_id: int):
    """
    Fetches a single order record by its primary key ID from the local database.
    """
    return db.query(models.Order).filter(models.Order.id == order_id).first()

def get_orders(db: Session, user_id: Optional[int] = None, skip: int = 0, limit: int = 100):
    """
    Returns a list of orders supporting pagination (offset/limit).
    If user_id is provided, filters orders by user_id.
    """
    query = db.query(models.Order)
    if user_id is not None:
        query = query.filter(models.Order.user_id == user_id)
    return query.offset(skip).limit(limit).all()

async def create_order(db: Session, order: schemas.OrderCreate):
    """
    Orchestrates order placement. This demonstrates a multi-step transaction
    relying on synchronous API calls (inter-service communication):
      1. Calls User Service to verify the user exists.
      2. Calls Product Service to verify product details and stock.
      3. Requests Product Service to deduct inventory.
      4. Inserts the order record in the local database.
    """
    async with httpx.AsyncClient() as client:
        # -------------------------------------------------------------
        # STEP 1: Verify user exists in User Service
        # -------------------------------------------------------------
        try:
            user_response = await client.get(f"{USER_SERVICE_URL}/users/{order.user_id}")
            if user_response.status_code == 404:
                # User was not found in the remote service
                raise HTTPException(status_code=400, detail=f"User with ID {order.user_id} not found.")
            elif user_response.status_code != 200:
                # Service responded with server errors
                raise HTTPException(status_code=500, detail="Failed to verify user from User Service.")
        except httpx.RequestError:
            # Network issue / User Service is offline
            raise HTTPException(status_code=503, detail="User Service is unavailable.")

        # -------------------------------------------------------------
        # STEP 2: Verify product exists in Product Service
        # -------------------------------------------------------------
        try:
            product_response = await client.get(f"{PRODUCT_SERVICE_URL}/products/{order.product_id}")
            if product_response.status_code == 404:
                # Product was not found in the remote catalog
                raise HTTPException(status_code=400, detail=f"Product with ID {order.product_id} not found.")
            elif product_response.status_code != 200:
                raise HTTPException(status_code=500, detail="Failed to verify product from Product Service.")
        except httpx.RequestError:
            # Network issue / Product Service is offline
            raise HTTPException(status_code=503, detail="Product Service is unavailable.")

        # Extract product details from JSON payload
        product_data = product_response.json()

        # -------------------------------------------------------------
        # STEP 3: Verify stock levels
        # -------------------------------------------------------------
        if product_data["stock"] < order.quantity:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient stock for product '{product_data['name']}'. "
                       f"Available: {product_data['stock']}, Requested: {order.quantity}"
            )

        # -------------------------------------------------------------
        # STEP 4: Request stock reduction from Product Service
        # -------------------------------------------------------------
        try:
            reduce_stock_response = await client.put(
                f"{PRODUCT_SERVICE_URL}/products/{order.product_id}/reduce-stock",
                json={"quantity": order.quantity}
            )
            if reduce_stock_response.status_code != 200:
                raise HTTPException(status_code=500, detail="Failed to update inventory in Product Service.")
        except httpx.RequestError:
            raise HTTPException(status_code=503, detail="Product Service is unavailable during stock deduction.")

        # -------------------------------------------------------------
        # STEP 5: Create and save the Order record locally
        # -------------------------------------------------------------
        total_price = product_data["price"] * order.quantity
        db_order = models.Order(
            user_id=order.user_id,
            product_id=order.product_id,
            quantity=order.quantity,
            total_price=total_price,
            status="COMPLETED"
        )
        db.add(db_order)
        db.commit()
        db.refresh(db_order)
        return db_order

async def get_order_details(db: Session, order_id: int):
    """
    Implements Data Federation / Aggregated Read.
    Fetches the base order locally, then performs concurrent/sequential calls
    to fetch data from User and Product services.
    Includes error fallback logic if remote services are offline.
    """
    db_order = get_order_by_id(db, order_id)
    if db_order is None:
        return None
    
    user_details = None
    product_details = None

    async with httpx.AsyncClient() as client:
        # -------------------------------------------------------------
        # Call User Service (with Graceful Degradation / Fallback)
        # -------------------------------------------------------------
        try:
            user_res = await client.get(f"{USER_SERVICE_URL}/users/{db_order.user_id}")
            if user_res.status_code == 200:
                user_details = user_res.json()
        except httpx.RequestError:
            # Fallback error dict if remote service is offline
            user_details = {"error": "User Service unavailable"}

        # -------------------------------------------------------------
        # Call Product Service (with Graceful Degradation / Fallback)
        # -------------------------------------------------------------
        try:
            product_res = await client.get(f"{PRODUCT_SERVICE_URL}/products/{db_order.product_id}")
            if product_res.status_code == 200:
                product_details = product_res.json()
        except httpx.RequestError:
            # Fallback error dict if remote service is offline
            product_details = {"error": "Product Service unavailable"}

    # Return the combined schema response
    return {
        "id": db_order.id,
        "user_id": db_order.user_id,
        "product_id": db_order.product_id,
        "quantity": db_order.quantity,
        "total_price": db_order.total_price,
        "status": db_order.status,
        "user_details": user_details,
        "product_details": product_details
    }
