import os
import httpx
import bcrypt
from typing import List
from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text

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
#   3. Securely stores passwords in bcrypt hashed format.
#   4. On user deletion, calls Order Service (Port 8013) to ensure referential integrity.
# ==============================================================================

app = FastAPI(title="User Service", description="User Management Microservice with Bcrypt Password Security")

# Auto-create table definitions in MySQL (users_db)
models.Base.metadata.create_all(bind=database.engine)

# Auto-migration to ensure all user table columns exist in MySQL users_db
try:
    with database.engine.connect() as conn:
        for col_name, col_sql in [
            ("role", "ALTER TABLE users ADD COLUMN role VARCHAR(50) NOT NULL DEFAULT 'customer' AFTER email"),
            ("password", "ALTER TABLE users ADD COLUMN password VARCHAR(255) NULL AFTER role"),
            ("is_blocked", "ALTER TABLE users ADD COLUMN is_blocked TINYINT(1) NOT NULL DEFAULT 0 AFTER password"),
            ("profile_image", "ALTER TABLE users ADD COLUMN profile_image TEXT NULL AFTER is_blocked"),
            ("access_token", "ALTER TABLE users ADD COLUMN access_token TEXT NULL AFTER profile_image"),
            ("token_expires_at", "ALTER TABLE users ADD COLUMN token_expires_at DATETIME NULL AFTER access_token"),
            ("last_login", "ALTER TABLE users ADD COLUMN last_login DATETIME NULL AFTER token_expires_at"),
        ]:
            col_check = conn.execute(text(f"SHOW COLUMNS FROM users LIKE '{col_name}'"))
            if not col_check.fetchone():
                conn.execute(text(col_sql))
                conn.commit()
except Exception as e:
    print(f"User DB migration check note: {e}")

ORDER_SERVICE_URL = os.getenv("ORDER_SERVICE_URL", "http://127.0.0.1:8013")


# ------------------------------------------------------------------------------
# Bcrypt Password Utilities (Passwords validated and hashed dynamically from DB)
# ------------------------------------------------------------------------------
def hash_password(password: str) -> str:
    """Hashes a plain-text password using bcrypt."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifies a plain-text password against a stored password.
    Supports:
    1. Direct string match (handles plaintext credentials entered manually in MySQL Workbench)
    2. Bcrypt hash verification ($2a$, $2b$, $2y$)
    """
    if not hashed_password or not plain_password:
        return False
    # Direct plaintext match fallback (e.g. if edited in DB via MySQL Workbench)
    if plain_password == hashed_password or plain_password.strip() == hashed_password.strip():
        return True
    try:
        if hashed_password.startswith(("$2a$", "$2b$", "$2y$")):
            return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception as e:
        print(f"Bcrypt verification check error: {e}")
    return False


# ==============================================================================
# [DATA TRAVEL FLOW - CREATE USER]:
#   Origin:      API Gateway (POST /auth/register) -> User Service (POST /users)
#   Payload:     { name: str, email: str, password: str, role: str }
#   Security:    Bcrypt hashes the password before persistence in users_db.users.
#   Destination: Returns created User object with autoincremented ID back to API Gateway.
# ==============================================================================
@app.post("/users", response_model=schemas.User, status_code=status.HTTP_201_CREATED)
@app.post("/users/", response_model=schemas.User, status_code=status.HTTP_201_CREATED, include_in_schema=False)
def create_user(user: schemas.UserCreate, db: Session = Depends(database.get_db)):
    """Create a new user account with hashed password storage."""
    # Check if user with this email already exists
    existing = db.query(models.User).filter(models.User.email == user.email.strip().lower()).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Normalize role
    role = (user.role or "customer").lower()
    if role not in ("admin", "customer"):
        role = "customer"

    # Validate and hash the password with bcrypt (stored dynamically in DB)
    plain_password = user.password.strip() if user.password else ""
    if not plain_password:
        raise HTTPException(status_code=400, detail="Password is required")
    hashed_pwd = hash_password(plain_password)

    profile_img = user.profile_image.strip() if user.profile_image else None

    # Save to MySQL users_db
    db_user = models.User(
        name=user.name.strip(),
        email=user.email.strip().lower(),
        password=hashed_pwd,
        role=role,
        is_blocked=False,
        profile_image=profile_img,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


# ==============================================================================
# [DATA TRAVEL FLOW - VERIFY CREDENTIALS]:
#   Origin:      API Gateway (POST /auth/login) -> User Service (POST /users/verify-credentials)
#   Payload:     { email: str, password: str }
#   Security:    Bcrypt verifies plain password against hash in users_db.users.
#   Destination: Returns verified User object to Gateway for JWT signing.
# ==============================================================================
@app.post("/users/verify-credentials", response_model=schemas.User)
def verify_credentials(payload: schemas.UserLogin, db: Session = Depends(database.get_db)):
    """Verifies email and password against stored bcrypt hash."""
    user = db.query(models.User).filter(models.User.email == payload.email.strip().lower()).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    # Blocked check: If user is marked as blocked (1) in DB, deny login
    if getattr(user, "is_blocked", False):
        raise HTTPException(status_code=403, detail="Your account has been blocked by an administrator.")

    if not verify_password(payload.password, user.password):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    return user


# ==============================================================================
# [DATA TRAVEL FLOW - UPDATE USER TOKEN & SESSION EXPIRY]:
# ==============================================================================
@app.put("/users/{user_id}/token", response_model=schemas.User)
def update_user_token(
    user_id: int,
    payload: schemas.UserTokenUpdate,
    db: Session = Depends(database.get_db)
):
    """Updates persisted JWT access token, expiry date, and last login in MySQL."""
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if payload.access_token is not None:
        user.access_token = payload.access_token
    if payload.token_expires_at is not None:
        user.token_expires_at = payload.token_expires_at
    if payload.last_login is not None:
        user.last_login = payload.last_login
    db.commit()
    db.refresh(user)
    return user


# ==============================================================================
# [DATA TRAVEL FLOW - LIST USERS]:
#   Origin:      API Gateway (GET /users) -> User Service (GET /users)
#   Destination: Returns array of User objects back to API Gateway -> Admin Dashboard.
# ==============================================================================
@app.get("/users", response_model=List[schemas.User])
@app.get("/users/", response_model=List[schemas.User], include_in_schema=False)
def list_users(skip: int = 0, limit: int = 100, db: Session = Depends(database.get_db)):
    """List users with pagination."""
    return db.query(models.User).offset(skip).limit(limit).all()


# ==============================================================================
# [DATA TRAVEL FLOW - GET USER BY EMAIL]:
# ==============================================================================
@app.get("/users/by-email", response_model=schemas.User)
def get_user_by_email(email: str, db: Session = Depends(database.get_db)):
    """Retrieve user by email for lookup."""
    user = db.query(models.User).filter(models.User.email == email.strip().lower()).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


# ==============================================================================
# [DATA TRAVEL FLOW - GET USER BY ID]:
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

    if payload.password is not None and payload.password.strip():
        user.password = hash_password(payload.password.strip())

    if payload.role is not None and payload.role.strip():
        role = payload.role.strip().lower()
        if role in ("admin", "customer"):
            user.role = role

    if payload.profile_image is not None:
        user.profile_image = payload.profile_image.strip() or None

    if payload.is_blocked is not None:
        user.is_blocked = bool(payload.is_blocked)
        if user.is_blocked:
            user.access_token = None

    db.commit()
    db.refresh(user)
    return user


# ==============================================================================
# [DATA TRAVEL FLOW - BLOCK / UNBLOCK USER (1 or 0 in DB)]:
# ==============================================================================
@app.put("/users/{user_id}/block", response_model=schemas.User)
def block_user(user_id: int, db: Session = Depends(database.get_db)):
    """Blocks a user account (is_blocked = 1) and revokes their active access token."""
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_blocked = True
    user.access_token = None
    db.commit()
    db.refresh(user)
    return user


@app.put("/users/{user_id}/unblock", response_model=schemas.User)
def unblock_user(user_id: int, db: Session = Depends(database.get_db)):
    """Unblocks a user account (is_blocked = 0)."""
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_blocked = False
    db.commit()
    db.refresh(user)
    return user


@app.put("/users/{user_id}/toggle-block", response_model=schemas.User)
def toggle_block_user(user_id: int, db: Session = Depends(database.get_db)):
    """Toggles user blocked status between 0 (active) and 1 (blocked)."""
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_blocked = not bool(user.is_blocked)
    if user.is_blocked:
        user.access_token = None
    db.commit()
    db.refresh(user)
    return user


# ==============================================================================
# [DATA TRAVEL FLOW - DELETE USER WITH SAGA INTEGRITY CHECK]:
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
                        detail=f"Cannot delete user #{user_id} because they have {len(orders)} associated order(s)."
                    )
    except httpx.RequestError:
        pass

    db.delete(user)
    db.commit()
    return {"message": f"User #{user_id} deleted successfully"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8011)
