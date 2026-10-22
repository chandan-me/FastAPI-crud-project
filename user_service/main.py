from fastapi import FastAPI
from . import models, database
from .routers import user_router

# =====================================================================
# MAIN ENTRYPOINT (User Service)
# This module initializes the FastAPI application instance, mounts
# the APIRouter schemas, and triggers database table definitions setup.
# =====================================================================

# Instantiate the FastAPI app
app = FastAPI(
    title="User Service", 
    description="Demo User Microservice for clean architecture demonstration"
)

# Trigger automatic creation of database tables if they do not already exist.
# Note: In production projects, migrations (e.g. Alembic) are used instead.
models.Base.metadata.create_all(bind=database.engine)

# Register endpoints from user_router
app.include_router(user_router.router)

# --- Service Discovery Registration ---
from .discovery_client import DiscoveryClient

discovery_client = DiscoveryClient(app_name="user-service", port=8011)

@app.on_event("startup")
def startup_event():
    discovery_client.start()

@app.on_event("shutdown")
def shutdown_event():
    discovery_client.stop()

