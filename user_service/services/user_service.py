from sqlalchemy.orm import Session
import httpx
from fastapi import HTTPException
from .. import models, schemas

# =====================================================================
# SERVICE LAYER MODULE (User Service)
# This module encapsulates core database query logic and transactions.
# Separating query operations into a Service layer allows for reusability,
# easier testing, and keeps route handlers (routers) lightweight.
# =====================================================================

def get_user_by_id(db: Session, user_id: int):
    """
    Fetches a single user record by its primary key ID.
    Used by routers and other services for validity assertions.
    """
    return db.query(models.User).filter(models.User.id == user_id).first()

def get_user_by_email(db: Session, email: str):
    """
    Retrieves a user by their email address.
    Typically used to prevent duplicate user registrations.
    """
    return db.query(models.User).filter(models.User.email == email).first()

def get_users(db: Session, skip: int = 0, limit: int = 100):
    """
    Returns a list of users supporting pagination (offset/limit).
    """
    return db.query(models.User).offset(skip).limit(limit).all()

def create_user(db: Session, user: schemas.UserCreate):
    """
    Inserts a new user record into the database.
    Manages database transactions (commit and database state refresh).
    """
    user_role = (user.role or "customer").lower()
    if user_role not in ("admin", "customer"):
        user_role = "customer"

    # Instantiate the SQLAlchemy DB model using Pydantic incoming schema data
    db_user = models.User(name=user.name, email=user.email, role=user_role)
    
    db.add(db_user)      # Add the model to the database transaction session
    db.commit()          # Execute INSERT statement and commit database transaction
    db.refresh(db_user)  # Refresh object fields from DB (such as the auto-generated id)
    
    return db_user

def update_user(db: Session, db_user: models.User, user_update: schemas.UserUpdate):
    """
    Updates permitted fields on an existing user with uniqueness validation.
    """
    if user_update.name is not None and user_update.name.strip():
        db_user.name = user_update.name.strip()
    
    if user_update.email is not None and user_update.email.strip():
        new_email = user_update.email.strip().lower()
        if new_email != db_user.email.lower():
            existing = get_user_by_email(db, new_email)
            if existing and existing.id != db_user.id:
                raise HTTPException(status_code=400, detail="Email address is already in use by another user")
            db_user.email = new_email

    if user_update.role is not None and user_update.role.strip():
        r = user_update.role.strip().lower()
        if r in ("admin", "customer"):
            db_user.role = r
            
    db.commit()
    db.refresh(db_user)
    return db_user

async def delete_user(db: Session, db_user: models.User):
    """
    Safely deletes a user record after asserting no dependent orders exist.
    """
    ORDER_SERVICE_URL = "http://localhost:8013"
    # Check if user has associated orders in Order Service to maintain referential integrity
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            res = await client.get(f"{ORDER_SERVICE_URL}/orders?user_id={db_user.id}")
            if res.status_code == 200:
                orders = res.json()
                if orders and len(orders) > 0:
                    raise HTTPException(
                        status_code=400, 
                        detail=f"Cannot delete user #{db_user.id} because they have {len(orders)} associated order(s). Cancel or delete the orders first."
                    )
    except httpx.RequestError:
        pass

    db.delete(db_user)
    db.commit()
    return {"message": f"User #{db_user.id} deleted successfully"}
