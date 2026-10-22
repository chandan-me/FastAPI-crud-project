from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from .. import schemas, database
from ..services import order_service

# =====================================================================
# API ROUTER MODULE (Order Service)
# This module defines the HTTP endpoints (routes) for the Order Service.
# Routers are responsible for mapping HTTP methods (GET, POST, etc.) and paths
# to controller functions, injecting DB dependencies, and raising HTTP exceptions.
# =====================================================================

# Initialize the router with a prefix so all endpoints start with '/orders'
router = APIRouter(prefix="/orders", tags=["orders"])

@router.post("", response_model=schemas.Order, status_code=status.HTTP_201_CREATED, include_in_schema=False)
@router.post("/", response_model=schemas.Order, status_code=status.HTTP_201_CREATED)
async def create_order(order: schemas.OrderCreate, db: Session = Depends(database.get_db)):
    """
    Endpoint to place a new order.
    Note: Marked as 'async def' because it performs async calls inside order_service.
    """
    return await order_service.create_order(db=db, order=order)

@router.get("", response_model=List[schemas.Order], include_in_schema=False)
@router.get("/", response_model=List[schemas.Order])
def read_orders(user_id: Optional[int] = None, skip: int = 0, limit: int = 100, db: Session = Depends(database.get_db)):
    """
    Endpoint to list base orders, optionally filtered by user_id.
    """
    return order_service.get_orders(db, user_id=user_id, skip=skip, limit=limit)

@router.get("/{order_id}", response_model=schemas.Order)
def read_order(order_id: int, db: Session = Depends(database.get_db)):
    """
    Endpoint to retrieve a base order record from database.
    """
    db_order = order_service.get_order_by_id(db, order_id=order_id)
    if db_order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    return db_order

@router.get("/{order_id}/details", response_model=schemas.OrderDetail)
async def read_order_details(order_id: int, db: Session = Depends(database.get_db)):
    """
    Endpoint to retrieve detailed aggregated order details.
    Demonstrates data federation across multiple services.
    """
    details = await order_service.get_order_details(db, order_id=order_id)
    if details is None:
        raise HTTPException(status_code=404, detail="Order not found")
    return details

@router.put("/{order_id}", response_model=schemas.Order)
async def update_order(order_id: int, payload: schemas.OrderUpdate, db: Session = Depends(database.get_db)):
    """
    Endpoint to update order status (e.g. CANCELLED, COMPLETED).
    """
    db_order = order_service.get_order_by_id(db, order_id=order_id)
    if db_order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    return await order_service.update_order(db=db, db_order=db_order, order_update=payload)

@router.delete("/{order_id}", status_code=status.HTTP_200_OK)
async def delete_order(order_id: int, db: Session = Depends(database.get_db)):
    """
    Endpoint to delete/cancel order and release reserved stock.
    """
    db_order = order_service.get_order_by_id(db, order_id=order_id)
    if db_order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    return await order_service.delete_order(db=db, db_order=db_order)
