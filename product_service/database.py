from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from .config import DATABASE_URL

# =====================================================================
# DATABASE SESSION SETUP (Product Service)
# This module configures SQLAlchemy engine and session factories.
# It establishes database connections and exposes session instances.
# =====================================================================

# Create the SQLAlchemy Engine. This manages database connection pooling.
engine = create_engine(DATABASE_URL)

# Create a session factory. SessionLocal instances will represent transaction units.
# autocommit=False ensures transactions are manually committed (or rolled back).
# autoflush=False prevents automatic queries execution before manual commit.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for declarative models. DB models inherit from this to map to SQL tables.
Base = declarative_base()

# Dependency generator to inject database sessions into FastAPI routes.
# Yields a session instance and guarantees cleanup (closing session) after execution.
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
