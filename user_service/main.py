import os
import httpx
from typing import List
from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session

try:
    from . import models, schemas, database
except ImportError:
    import models, schemas, database

# ==============================================================================
# USER SERVICE (Port 8011)
#
# High-Level Data Travel Architecture:
#   1. Receives requests from:
#      - API Gateway (Port 8010) for registration, login, and user profile CRUD.
#      - Order Service (Port 8013) to verify that a user exists during order placement.
#   2. Reads/Writes user records to its isolated MySQL database: `users_db.users`.
#   3. On user deletion, calls Order Service (Port 8013) to ensure referential integrity.
# ==============================================================================

app = FastAPI(title="User Service", description="User Management Microservice")

# Auto-create table definitions in MySQL (users_db)
models.Base.metadata.create_all(bind=database.engine)

ORDER_SERVICE_URL = os.getenv("ORDER_SERVICE_URL", "http://127.0.0.1:8013")


# ==============================================================================
# [DATA TRAVEL FLOW - CREATE USER]:
#   Origin:      API Gateway (POST /auth/register) -> User Service (POST /users)
#   Payload:     { name: str, email: str, role: str }
#   Database:    1. SELECT * FROM users_db.users WHERE email = ? (Check duplicate)
#                2. INSERT INTO users_db.users (name, email, role) VALUES (...)
#   Destination: Returns created User object with autoincremented ID back to API Gateway.
# ==============================================================================
@app.post("/users", response_model=schemas.User, status_code=status.HTTP_201_CREATED)
@app.post("/users/", response_model=schemas.User, status_code=status.HTTP_201_CREATED, include_in_schema=False)
def create_user(user: schemas.UserCreate, db: Session = Depends(database.get_db)):
    """Create a new user account."""
    # Check if user with this email already exists
    existing = db.query(models.User).filter(models.User.email == user.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Normalize role
    role = (user.role or "customer").lower()
    if role not in ("admin", "customer"):
        role = "customer"

    # Save to MySQL users_db
    db_user = models.User(name=user.name, email=user.email, role=role)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


# ==============================================================================
# [DATA TRAVEL FLOW - LIST USERS]:
#   Origin:      API Gateway (GET /users) -> User Service (GET /users)
#   Params:      skip: int, limit: int
#   Database:    SELECT * FROM users_db.users LIMIT limit OFFSET skip
#   Destination: Returns array of User objects back to API Gateway -> Admin Dashboard.
# ==============================================================================
@app.get("/users", response_model=List[schemas.User])
@app.get("/users/", response_model=List[schemas.User], include_in_schema=False)
def list_users(skip: int = 0, limit: int = 100, db: Session = Depends(database.get_db)):
    """List users with pagination."""
    return db.query(models.User).offset(skip).limit(limit).all()


# ==============================================================================
# [DATA TRAVEL FLOW - GET USER BY EMAIL]:
#   Origin:      API Gateway (POST /auth/login) -> User Service (GET /users/by-email?email=...)
#   Database:    SELECT * FROM users_db.users WHERE email = ? LIMIT 1
#   Destination: Returns User object to API Gateway to verify credentials & issue JWT token.
# ==============================================================================
@app.get("/users/by-email", response_model=schemas.User)
def get_user_by_email(email: str, db: Session = Depends(database.get_db)):
    """Retrieve user by email for Gateway authentication."""
    user = db.query(models.User).filter(models.User.email == email.strip()).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


# ==============================================================================
# [DATA TRAVEL FLOW - GET USER BY ID]:
#   Origin:      Called from:
#                1. API Gateway (GET /users/{id}) for profile viewing.
#                2. Order Service (GET http://127.0.0.1:8011/users/{id}) during
#                   Step 1 of the Order Saga and during Order Detail Federation.
#   Database:    SELECT * FROM users_db.users WHERE id = ? LIMIT 1
#   Destination: Returns User object to caller.
# ==============================================================================
@app.get("/users/{user_id}", response_model=schemas.User)
def get_user(user_id: int, db: Session = Depends(database.get_db)):
    """Retrieve user by ID."""
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


# ==============================================================================
# [DATA TRAVEL FLOW - UPDATE USER PROFILE]:
#   Origin:      API Gateway (PUT /users/{id}) -> User Service (PUT /users/{id})
#   Payload:     UserUpdate { name?, email?, role? }
#   Database:    UPDATE users_db.users SET ... WHERE id = ?
#   Destination: Returns updated User object back to API Gateway -> Frontend.
# ==============================================================================
@app.put("/users/{user_id}", response_model=schemas.User)
def update_user(user_id: int, payload: schemas.UserUpdate, db: Session = Depends(database.get_db)):
    """Update permitted user profile fields."""
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if payload.name is not None and payload.name.strip():
        user.name = payload.name.strip()

    if payload.email is not None and payload.email.strip():
        new_email = payload.email.strip().lower()
        if new_email != user.email.lower():
            existing = db.query(models.User).filter(models.User.email == new_email).first()
            if existing and existing.id != user.id:
                raise HTTPException(status_code=400, detail="Email address is already in use by another user")
            user.email = new_email

    if payload.role is not None and payload.role.strip():
        role = payload.role.strip().lower()
        if role in ("admin", "customer"):
            user.role = role

    db.commit()
    db.refresh(user)
    return user


# ==============================================================================
# [DATA TRAVEL FLOW - DELETE USER WITH SAGA INTEGRITY CHECK]:
#   Origin:      API Gateway (DELETE /users/{id}) -> User Service (DELETE /users/{id})
#   Outbound:    User Service -> Order Service (GET http://127.0.0.1:8013/orders?user_id={id})
#                - If active orders exist: Aborts and raises HTTP 400.
#                - If 0 orders exist: Proceeds to delete.
#   Database:    DELETE FROM users_db.users WHERE id = ?
#   Destination: Returns success message back to API Gateway -> Frontend.
# ==============================================================================
@app.delete("/users/{user_id}", status_code=status.HTTP_200_OK)
async def delete_user(user_id: int, db: Session = Depends(database.get_db)):
    """Safely delete user account after verifying no active orders exist."""
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Verify no associated orders exist in Order Service
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            res = await client.get(f"{ORDER_SERVICE_URL}/orders", params={"user_id": user_id})
            if res.status_code == 200:
                orders = res.json()
                if orders:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Cannot delete user #{user_id} because they have {len(orders)} associated order(s). Cancel or delete the orders first."
                    )
    except httpx.RequestError:
        pass

    db.delete(user)
    db.commit()
    return {"message": f"User #{user_id} deleted successfully"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8011)
