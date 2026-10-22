from sqlalchemy.orm import Session
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
    # Instantiate the SQLAlchemy DB model using Pydantic incoming schema data
    db_user = models.User(name=user.name, email=user.email)
    
    db.add(db_user)      # Add the model to the database transaction session
    db.commit()          # Execute INSERT statement and commit database transaction
    db.refresh(db_user)  # Refresh object fields from DB (such as the auto-generated id)
    
    return db_user
