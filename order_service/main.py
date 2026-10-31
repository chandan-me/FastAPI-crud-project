from fastapi import FastAPI
from . import models, database
from .routers import order_router

# =====================================================================
# MAIN ENTRYPOINT (Order Service)
# This module initializes the FastAPI application instance, mounts
# the APIRouter schemas, and triggers database table definitions setup.
# =====================================================================

# Instantiate the FastAPI app
app = FastAPI(
    title="Order Service", 
    description="Demo Order Microservice for clean architecture demonstration"
)

# Trigger automatic creation of database tables if they do not already exist.
models.Base.metadata.create_all(bind=database.engine)

# Register endpoints from order_router
app.include_router(order_router.router)


