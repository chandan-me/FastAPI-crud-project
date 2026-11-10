import os
import time
import httpx
from typing import List, Optional
from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from dotenv import load_dotenv

# Load root .env
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"), override=True)

try:
    from . import models, schemas, database
except ImportError:
    import models, schemas, database

def get_razorpay_keys():
    """Dynamically reads RAZORPAY_KEY_ID & RAZORPAY_KEY_SECRET from .env with override."""
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"), override=True)
    key_id = os.getenv("RAZORPAY_KEY_ID", "").strip()
    key_secret = os.getenv("RAZORPAY_KEY_SECRET", "").strip()
    return key_id, key_secret

# ==============================================================================
# ORDER SERVICE (Port 8013)
#
# High-Level Data Travel Architecture:
#   1. Acts as the Distributed Saga Coordinator for transactions:
#      - Calls User Service (Port 8011) to assert customer validity.
#      - Calls Product Service (Port 8012) to verify catalog pricing and stock.
#      - Calls Product Service (Port 8012) to deduct stock atomically.
#      - Writes the confirmed order into its isolated MySQL database: `orders_db.orders`.
#   2. Performs Data Federation (GET /orders/{id}/details):
#      - Aggregates local order row + remote user details + remote product details.
#   3. Executes Compensating Transactions (Order Cancellation / Deletion):
#      - Calls Product Service (Port 8012) to restore inventory if an order is cancelled.
#   4. Responds to Referential Checks from User & Product services before deletions.
# ==============================================================================

app = FastAPI(title="Order Service", description="Order Processing & Distributed Saga Microservice")

# Auto-create table definitions in MySQL (orders_db)
models.Base.metadata.create_all(bind=database.engine)

# Inter-Service Connection Endpoints
USER_SERVICE_URL = os.getenv("USER_SERVICE_URL", "http://127.0.0.1:8011")
PRODUCT_SERVICE_URL = os.getenv("PRODUCT_SERVICE_URL", "http://127.0.0.1:8012")


# ==============================================================================
# [DATA TRAVEL FLOW - DISTRIBUTED ORDER PLACEMENT SAGA]:
#   Origin:      API Gateway (POST /orders with JWT user_id) -> Order Service (POST /orders)
#   Payload:     { user_id: int, product_id: int, quantity: int }
#
#   SAGA TRAVERSAL:
#     Step 1: Order Service -> User Service
#             GET http://127.0.0.1:8011/users/{user_id}
#             -> Asserts user exists in users_db.users
#
#     Step 2: Order Service -> Product Service
#             GET http://127.0.0.1:8012/products/{product_id}
#             -> Fetches item price & verifies available stock >= quantity
#
#     Step 3: Order Service -> Product Service (Atomic Deduction)
#             PUT http://127.0.0.1:8012/products/{product_id}/reduce-stock
#             -> Deducts quantity from products_db.products
#
#     Step 4: Order Service -> Local MySQL
#             INSERT INTO orders_db.orders (user_id, product_id, quantity, total_price, status)
#             -> Sets status = "COMPLETED"
#
#   Destination: Returns confirmed Order object back to API Gateway -> Frontend.
# ==============================================================================
@app.post("/orders", response_model=schemas.Order, status_code=status.HTTP_201_CREATED)
@app.post("/orders/", response_model=schemas.Order, status_code=status.HTTP_201_CREATED, include_in_schema=False)
async def create_order(order: schemas.OrderCreate, db: Session = Depends(database.get_db)):
    """Orchestrates order placement with distributed verification and stock deduction."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        # Step 1: Verify user exists in User Service
        try:
            user_res = await client.get(f"{USER_SERVICE_URL}/users/{order.user_id}")
            if user_res.status_code == 404:
                raise HTTPException(status_code=400, detail=f"User with ID {order.user_id} not found.")
            elif user_res.status_code != 200:
                raise HTTPException(status_code=500, detail="Failed to verify user from User Service.")
            user_data = user_res.json()
            if user_data.get("is_blocked"):
                raise HTTPException(status_code=403, detail="Your user account is blocked and cannot place orders.")
        except httpx.RequestError:
            raise HTTPException(status_code=503, detail="User Service is unavailable.")

        # Step 2: Verify product exists in Product Service & check stock
        try:
            prod_res = await client.get(f"{PRODUCT_SERVICE_URL}/products/{order.product_id}")
            if prod_res.status_code == 404:
                raise HTTPException(status_code=400, detail=f"Product with ID {order.product_id} not found.")
            elif prod_res.status_code != 200:
                raise HTTPException(status_code=500, detail="Failed to verify product from Product Service.")
        except httpx.RequestError:
            raise HTTPException(status_code=503, detail="Product Service is unavailable.")

        product_data = prod_res.json()
        if product_data.get("is_blocked"):
            raise HTTPException(
                status_code=400,
                detail=f"Product '{product_data.get('name')}' is blocked and cannot be purchased."
            )

        # Step 3: Assert sufficient stock availability
        if product_data["stock"] < order.quantity:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient stock for product '{product_data['name']}'. Available: {product_data['stock']}, Requested: {order.quantity}"
            )

        # Step 4: Request atomic stock deduction from Product Service
        try:
            deduct_res = await client.put(
                f"{PRODUCT_SERVICE_URL}/products/{order.product_id}/reduce-stock",
                json={"quantity": order.quantity}
            )
            if deduct_res.status_code != 200:
                raise HTTPException(status_code=500, detail="Failed to update inventory in Product Service.")
        except httpx.RequestError:
            raise HTTPException(status_code=503, detail="Product Service is unavailable during stock deduction.")

        # Step 5: Save order locally in MySQL orders_db
        total_price = product_data["price"] * order.quantity
        db_order = models.Order(
            user_id=order.user_id,
            product_id=order.product_id,
            quantity=order.quantity,
            total_price=total_price,
            status="COMPLETED",
            payment_method=order.payment_method or "COD",
            payment_id=order.payment_id,
            order_group_id=order.order_group_id
        )
        db.add(db_order)
        db.commit()
        db.refresh(db_order)
        if not db_order.order_group_id:
            db_order.order_group_id = f"ORD-{db_order.id}"
            db.commit()
            db.refresh(db_order)
        return db_order


# ==============================================================================
# [DATA TRAVEL FLOW - PAYMENT & BATCH CHECKOUT ROUTES]:
#   - GET /orders/payment/config -> returns Razorpay public key and configuration
#   - POST /orders/payment/razorpay/create-order -> creates official Razorpay Order
#   - POST /orders/payment/razorpay/verify -> verifies signature & confirms orders
#   - POST /orders/checkout -> multi-item batch order placement (COD or prepaid)
# ==============================================================================

@app.get("/orders/payment/config")
def get_payment_config():
    """Returns Razorpay public key and configuration state from .env."""
    key_id, key_secret = get_razorpay_keys()
    return {
        "razorpay_key_id": key_id,
        "is_configured": bool(key_id and key_secret),
        "currency": "INR"
    }


@app.post("/orders/payment/razorpay/create-order")
def create_razorpay_order(payload: schemas.RazorpayCreateOrderRequest):
    """Creates an official Razorpay Order for frontend checkout."""
    key_id, key_secret = get_razorpay_keys()
    if not key_id or not key_secret:
        raise HTTPException(
            status_code=400,
            detail="Razorpay is not configured in .env. Please add RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET."
        )

    try:
        import razorpay
        client = razorpay.Client(auth=(key_id, key_secret))
        amount_in_paise = int(round(payload.amount * 100))
        receipt_id = f"rcpt_{int(time.time() * 1000)}"
        rzp_order = client.order.create({
            "amount": amount_in_paise,
            "currency": payload.currency or "INR",
            "receipt": receipt_id,
            "payment_capture": 1
        })
        return {
            "razorpay_order_id": rzp_order["id"],
            "amount": rzp_order["amount"],
            "currency": rzp_order["currency"],
            "key_id": key_id
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to create Razorpay order: {str(e)}")


@app.post("/orders/payment/razorpay/verify", response_model=List[schemas.Order])
async def verify_razorpay_and_place_orders(payload: schemas.RazorpayVerifyRequest, db: Session = Depends(database.get_db)):
    """Verifies Razorpay HMAC signature and places all cart orders atomically."""
    key_id, key_secret = get_razorpay_keys()
    if not key_id or not key_secret:
        raise HTTPException(
            status_code=400,
            detail="Razorpay is not configured in .env. Please add RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET."
        )

    try:
        import razorpay
        client = razorpay.Client(auth=(key_id, key_secret))
        client.utility.verify_payment_signature({
            "razorpay_order_id": payload.razorpay_order_id,
            "razorpay_payment_id": payload.razorpay_payment_id,
            "razorpay_signature": payload.razorpay_signature
        })
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid Razorpay payment signature: {str(e)}")

    if not payload.items:
        raise HTTPException(status_code=400, detail="No items specified for checkout.")

    group_id = payload.razorpay_payment_id or f"RZP-{int(time.time()*1000)}"
    created_orders = []
    async with httpx.AsyncClient(timeout=10.0) as client_http:
        for item in payload.items:
            prod_res = await client_http.get(f"{PRODUCT_SERVICE_URL}/products/{item.product_id}")
            if prod_res.status_code != 200:
                continue
            prod_data = prod_res.json()

            deduct_res = await client_http.put(
                f"{PRODUCT_SERVICE_URL}/products/{item.product_id}/reduce-stock",
                json={"quantity": item.quantity}
            )
            if deduct_res.status_code != 200:
                continue

            total_price = prod_data["price"] * item.quantity
            db_order = models.Order(
                user_id=payload.user_id,
                product_id=item.product_id,
                quantity=item.quantity,
                total_price=total_price,
                status="COMPLETED",
                payment_method="RAZORPAY",
                payment_id=payload.razorpay_payment_id,
                order_group_id=group_id
            )
            db.add(db_order)
            db.commit()
            db.refresh(db_order)
            created_orders.append(db_order)

    return created_orders


@app.post("/orders/checkout", response_model=List[schemas.Order], status_code=status.HTTP_201_CREATED)
async def checkout_cart_orders(payload: schemas.CheckoutRequest, db: Session = Depends(database.get_db)):
    """Batch order placement for cart checkout (Cash on Delivery or prepaid)."""
    if not payload.items:
        raise HTTPException(status_code=400, detail="Cart has no items for checkout.")

    group_id = payload.payment_id or f"COD-{int(time.time()*1000)}-{payload.user_id}"

    async with httpx.AsyncClient(timeout=10.0) as client:
        # Step 1: Verify user
        try:
            user_res = await client.get(f"{USER_SERVICE_URL}/users/{payload.user_id}")
            if user_res.status_code == 404:
                raise HTTPException(status_code=400, detail=f"User with ID {payload.user_id} not found.")
            elif user_res.status_code != 200:
                raise HTTPException(status_code=500, detail="Failed to verify user from User Service.")
            if user_res.json().get("is_blocked"):
                raise HTTPException(status_code=403, detail="Your user account is blocked and cannot place orders.")
        except httpx.RequestError:
            raise HTTPException(status_code=503, detail="User Service is unavailable.")

        # Step 2: Validate all products & verify stocks
        product_cache = {}
        for item in payload.items:
            try:
                prod_res = await client.get(f"{PRODUCT_SERVICE_URL}/products/{item.product_id}")
                if prod_res.status_code == 404:
                    raise HTTPException(status_code=400, detail=f"Product with ID {item.product_id} not found.")
                elif prod_res.status_code != 200:
                    raise HTTPException(status_code=500, detail="Failed to verify product.")
                pdata = prod_res.json()
                if pdata.get("is_blocked"):
                    raise HTTPException(
                        status_code=400,
                        detail=f"Product '{pdata['name']}' is currently blocked and cannot be purchased."
                    )
                if pdata["stock"] < item.quantity:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Insufficient stock for '{pdata['name']}'. Available: {pdata['stock']}, Requested: {item.quantity}"
                    )
                product_cache[item.product_id] = pdata
            except httpx.RequestError:
                raise HTTPException(status_code=503, detail="Product Service is unavailable.")

        # Step 3: Deduct stock and commit orders
        created_orders = []
        for item in payload.items:
            pdata = product_cache[item.product_id]
            deduct_res = await client.put(
                f"{PRODUCT_SERVICE_URL}/products/{item.product_id}/reduce-stock",
                json={"quantity": item.quantity}
            )
            if deduct_res.status_code != 200:
                raise HTTPException(status_code=500, detail=f"Failed to deduct stock for {pdata['name']}")

            total_price = pdata["price"] * item.quantity
            db_order = models.Order(
                user_id=payload.user_id,
                product_id=item.product_id,
                quantity=item.quantity,
                total_price=total_price,
                status="COMPLETED",
                payment_method=payload.payment_method or "COD",
                payment_id=payload.payment_id,
                order_group_id=group_id
            )
            db.add(db_order)
            db.commit()
            db.refresh(db_order)
            created_orders.append(db_order)

        return created_orders


# ==============================================================================
# [DATA TRAVEL FLOW - LIST ORDERS]:
#   Origin:      API Gateway (GET /orders, scoped by user_id for customers) -> Order Service (GET /orders)
#   Params:      user_id: Optional[int], skip: int, limit: int
#   Database:    SELECT * FROM orders_db.orders [WHERE user_id = ?] LIMIT limit OFFSET skip
#   Destination: Returns list of Order objects back to API Gateway -> Frontend.
# ==============================================================================
@app.get("/orders", response_model=List[schemas.Order])
@app.get("/orders/", response_model=List[schemas.Order], include_in_schema=False)
def list_orders(
    user_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(database.get_db)
):
    """List orders, optionally filtered by user_id."""
    query = db.query(models.Order)
    if user_id is not None:
        query = query.filter(models.Order.user_id == user_id)
    return query.offset(skip).limit(limit).all()


# ==============================================================================
# [DATA TRAVEL FLOW - GET ORDER BY ID]:
#   Origin:      API Gateway (GET /orders/{id}) -> Order Service (GET /orders/{id})
#   Database:    SELECT * FROM orders_db.orders WHERE id = ? LIMIT 1
#   Destination: Returns Order object back to API Gateway -> Frontend.
# ==============================================================================
@app.get("/orders/{order_id}", response_model=schemas.Order)
def get_order(order_id: int, db: Session = Depends(database.get_db)):
    """Retrieve an order by ID."""
    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


# ==============================================================================
# [DATA TRAVEL FLOW - FEDERATED ORDER DETAILS]:
#   Origin:      API Gateway (GET /orders/{id}/details) -> Order Service
#   Local DB:    1. SELECT * FROM orders_db.orders WHERE id = ?
#
#   FEDERATION CALLS:
#     Step 1: Order Service -> User Service
#             GET http://127.0.0.1:8011/users/{order.user_id}
#             -> Returns user details { id, name, email }
#
#     Step 2: Order Service -> Product Service
#             GET http://127.0.0.1:8012/products/{order.product_id}
#             -> Returns product details { id, name, price }
#
#   Destination: Merges order + user_details + product_details and returns
#                aggregated OrderDetail schema back to API Gateway -> Frontend.
# ==============================================================================
@app.get("/orders/{order_id}/details", response_model=schemas.OrderDetail)
async def get_order_details(order_id: int, db: Session = Depends(database.get_db)):
    """Federated read: aggregates local order record with remote user and product details."""
    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    user_details = None
    product_details = None

    async with httpx.AsyncClient(timeout=5.0) as client:
        # Step 1: Query User Service
        try:
            u_res = await client.get(f"{USER_SERVICE_URL}/users/{order.user_id}")
            if u_res.status_code == 200:
                user_details = u_res.json()
        except httpx.RequestError:
            user_details = {"error": "User Service unavailable"}

        # Step 2: Query Product Service
        try:
            p_res = await client.get(f"{PRODUCT_SERVICE_URL}/products/{order.product_id}")
            if p_res.status_code == 200:
                product_details = p_res.json()
        except httpx.RequestError:
            product_details = {"error": "Product Service unavailable"}

    return {
        "id": order.id,
        "user_id": order.user_id,
        "product_id": order.product_id,
        "quantity": order.quantity,
        "total_price": order.total_price,
        "status": order.status,
        "payment_method": order.payment_method or "COD",
        "payment_id": order.payment_id,
        "order_group_id": order.order_group_id,
        "user_details": user_details,
        "product_details": product_details
    }


# ==============================================================================
# [DATA TRAVEL FLOW - UPDATE ORDER STATUS & COMPENSATING RESTORATION]:
#   Origin:      API Gateway (PUT /orders/{id}) -> Order Service (PUT /orders/{id})
#   Payload:     OrderUpdate { status: str }
#   Compensating Call:
#     If new_status == 'CANCELLED' from an active status:
#     Order Service -> Product Service
#     PUT http://127.0.0.1:8012/products/{product_id}/restore-stock
#     -> Restores inventory in products_db.products
#   Database:    UPDATE orders_db.orders SET status = ? WHERE id = ?
#   Destination: Returns updated Order object back to API Gateway -> Frontend.
# ==============================================================================
@app.put("/orders/{order_id}", response_model=schemas.Order)
async def update_order(order_id: int, payload: schemas.OrderUpdate, db: Session = Depends(database.get_db)):
    """Update order status; automatically restores product inventory on cancellation."""
    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if payload.status is not None:
        new_status = payload.status.upper()
        old_status = (order.status or "").upper()

        # If transitioning to CANCELLED, execute compensating stock restoration
        if new_status == "CANCELLED" and old_status != "CANCELLED":
            async with httpx.AsyncClient(timeout=5.0) as client:
                try:
                    res = await client.put(
                        f"{PRODUCT_SERVICE_URL}/products/{order.product_id}/restore-stock",
                        json={"quantity": order.quantity}
                    )
                    if res.status_code not in (200, 404):
                        raise HTTPException(status_code=500, detail="Failed to restore inventory in Product Service.")
                except httpx.RequestError:
                    raise HTTPException(status_code=503, detail="Product Service unavailable for stock restoration.")

        order.status = new_status

    db.commit()
    db.refresh(order)
    return order


# ==============================================================================
# [DATA TRAVEL FLOW - DELETE ORDER WITH INVENTORY RESTORATION]:
#   Origin:      API Gateway (DELETE /orders/{id}) -> Order Service (DELETE /orders/{id})
#   Compensating Call:
#     If order was active (not CANCELLED):
#     Order Service -> Product Service (PUT .../restore-stock)
#     -> Re-credits items back to inventory before deleting order
#   Database:    DELETE FROM orders_db.orders WHERE id = ?
#   Destination: Returns success message back to API Gateway -> Frontend.
# ==============================================================================
@app.delete("/orders/{order_id}", status_code=status.HTTP_200_OK)
async def delete_order(order_id: int, db: Session = Depends(database.get_db)):
    """Safely delete order and restore product inventory if order was active."""
    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # If the order was active, restore stock before deleting
    if (order.status or "").upper() != "CANCELLED":
        async with httpx.AsyncClient(timeout=5.0) as client:
            try:
                await client.put(
                    f"{PRODUCT_SERVICE_URL}/products/{order.product_id}/restore-stock",
                    json={"quantity": order.quantity}
                )
            except httpx.RequestError:
                pass

    db.delete(order)
    db.commit()
    return {"message": f"Order {order_id} deleted successfully"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8013)
