from fastapi import FastAPI
from . import models, database
from .routers import product_router

# =====================================================================
# MAIN ENTRYPOINT (Product Service)
# This module initializes the FastAPI application instance, mounts
# the APIRouter schemas, and triggers database table definitions setup.
# =====================================================================

# Instantiate the FastAPI app
app = FastAPI(
    title="Product Service", 
    description="Demo Product Microservice for clean architecture demonstration"
)

# Trigger automatic creation of database tables if they do not already exist.
models.Base.metadata.create_all(bind=database.engine)

# Register endpoints from product_router
app.include_router(product_router.router)

# --- Service Discovery Registration ---
from .discovery_client import DiscoveryClient

discovery_client = DiscoveryClient(app_name="product-service", port=8012)

@app.on_event("startup")
def startup_event():
    discovery_client.start()

@app.on_event("shutdown")
def shutdown_event():
    discovery_client.stop()

