from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from .. import schemas, database
from ..services import user_service

# =====================================================================
# API ROUTER MODULE (User Service)
# This module defines the HTTP endpoints (routes) for the User Service.
# Routers are responsible for mapping HTTP methods (GET, POST, etc.) and paths
# to controller functions, injecting DB dependencies, and raising HTTP exceptions.
# =====================================================================

# Initialize the router with a prefix so all endpoints start with '/users'
router = APIRouter(prefix="/users", tags=["users"])

@router.post("", response_model=schemas.User, status_code=status.HTTP_201_CREATED, include_in_schema=False)
@router.post("/", response_model=schemas.User, status_code=status.HTTP_201_CREATED)
def create_user(user: schemas.UserCreate, db: Session = Depends(database.get_db)):
    """
    Endpoint to create a new user.
    Uses 'database.get_db' dependency injection to manage connections.
    """
    # Check if a user with the requested email already exists (duplicate check)
    db_user = user_service.get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Delegate insertion to the Service layer
    return user_service.create_user(db=db, user=user)

@router.get("", response_model=List[schemas.User], include_in_schema=False)
@router.get("/", response_model=List[schemas.User])
def read_users(skip: int = 0, limit: int = 100, db: Session = Depends(database.get_db)):
    """
    Endpoint to list users with pagination.
    """
    return user_service.get_users(db, skip=skip, limit=limit)

@router.get("/{user_id}", response_model=schemas.User)
def read_user(user_id: int, db: Session = Depends(database.get_db)):
    """
    Endpoint to retrieve details of a specific user.
    This is also called internally by the Order Service to validate user existance.
    """
    db_user = user_service.get_user_by_id(db, user_id=user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    
    return db_user

@router.put("/{user_id}", response_model=schemas.User)
def update_user(user_id: int, payload: schemas.UserUpdate, db: Session = Depends(database.get_db)):
    """
    Endpoint to update permitted user profile fields (name, email).
    """
    db_user = user_service.get_user_by_id(db, user_id=user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    
    return user_service.update_user(db=db, db_user=db_user, user_update=payload)

@router.delete("/{user_id}", status_code=status.HTTP_200_OK)
async def delete_user(user_id: int, db: Session = Depends(database.get_db)):
    """
    Endpoint to safely delete a user account if no dependent orders exist.
    """
    db_user = user_service.get_user_by_id(db, user_id=user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    
    return await user_service.delete_user(db=db, db_user=db_user)
