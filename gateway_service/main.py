import os
import json
from datetime import datetime
import httpx
from typing import Optional
from fastapi import FastAPI, Request, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel

try:
    from . import auth
except ImportError:
    import auth

# ==============================================================================
# API GATEWAY (Port 8010)
#
# High-Level Data Travel Architecture:
#   1. React Frontend (Browser Port 5173) connects exclusively to this Gateway.
#   2. Local Auth Routes (/auth/login, /auth/register, /users/login, /users/register)
#      validate credentials with bcrypt and issue secure signed JWT tokens.
#   3. Catch-All Proxy (/{service_prefix}/*) validates JWT & RBAC, then forwards
#      requests directly to downstream microservices (Ports 8011, 8012, 8013).
#   4. Downstream responses are streamed back to the client.
# ==============================================================================

app = FastAPI(title="API Gateway", description="Unified API Gateway with Direct Routing & RBAC")

# Enable CORS for React Frontend (Port 5173)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Service Port Mapping Directory
SERVICE_URL_MAP = {
    "users": os.getenv("USER_SERVICE_URL", "http://127.0.0.1:8011"),
    "products": os.getenv("PRODUCT_SERVICE_URL", "http://127.0.0.1:8012"),
    "orders": os.getenv("ORDER_SERVICE_URL", "http://127.0.0.1:8013"),
}

# Publicly accessible routes that bypass JWT token authentication
PUBLIC_ROUTES = [
    ("POST", "/auth/login"),
    ("POST", "/auth/register"),
    ("POST", "/users/login"),
    ("POST", "/users/register"),
    ("GET", "/products"),
    ("GET", "/orders/payment/config"),
]

class LoginRequest(BaseModel):
    email: str
    password: str

class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str
    role: str = "customer"
    profile_image: Optional[str] = None


# ==============================================================================
# [DATA TRAVEL FLOW - USER LOGIN]:
#   Step 1: Frontend sends { email, password } -> POST /auth/login or /users/login
#   Step 2: Gateway forwards request -> POST http://127.0.0.1:8011/users/verify-credentials
#   Step 3: User Service checks MySQL (users_db.users) and verifies bcrypt password hash
#   Step 4: Gateway generates signed JWT { user_id, email, role, exp }
#   Step 5: Gateway returns { access_token, token_type, user } back to Frontend
# ==============================================================================
@app.post("/auth/login")
@app.post("/users/login")
async def login(payload: LoginRequest):
    """Authenticates credentials against User Service (bcrypt) and issues JWT."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            user_host = SERVICE_URL_MAP["users"]
            res = await client.post(
                f"{user_host}/users/verify-credentials",
                json={"email": payload.email.strip(), "password": payload.password}
            )
            if res.status_code == 401:
                raise HTTPException(status_code=401, detail="Invalid email or password")
            elif res.status_code == 403:
                raise HTTPException(status_code=403, detail=res.json().get("detail", "Your account has been blocked."))
            elif res.status_code != 200:
                raise HTTPException(status_code=500, detail="User Service authentication failed")

            user = res.json()
            user_role = user.get("role", "customer")
            token, expire = auth.create_access_token(
                data={"user_id": user["id"], "email": user["email"], "role": user_role}
            )

            # Persist JWT token, expiration datetime, and last_login into MySQL users_db.users
            now = datetime.now()
            try:
                await client.put(
                    f"{user_host}/users/{user['id']}/token",
                    json={
                        "access_token": token,
                        "token_expires_at": expire.strftime("%Y-%m-%d %H:%M:%S"),
                        "last_login": now.strftime("%Y-%m-%d %H:%M:%S")
                    }
                )
            except Exception as e:
                print(f"Token persistence note: {e}")

            return {
                "access_token": token,
                "token_type": "bearer",
                "user": user,
                "expires_in_minutes": auth.ACCESS_TOKEN_EXPIRE_MINUTES
            }
        except httpx.RequestError:
            raise HTTPException(status_code=503, detail="User Service is offline")


# ==============================================================================
# [DATA TRAVEL FLOW - USER REGISTRATION]:
#   Step 1: Frontend sends { name, email, password, role } -> POST /auth/register or /users/register
#   Step 2: Gateway forwards JSON -> POST http://127.0.0.1:8011/users/
#   Step 3: User Service bcrypt-hashes password, inserts record into MySQL (users_db.users)
#   Step 4: Gateway signs new JWT containing { user_id, email, role, exp }
#   Step 5: Gateway returns { access_token, token_type, user } back to Frontend
# ==============================================================================
@app.post("/auth/register")
@app.post("/users/register")
async def register(payload: RegisterRequest):
    """Registers new user in User Service, hashes password, and issues JWT."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            user_host = SERVICE_URL_MAP["users"]
            res = await client.post(
                f"{user_host}/users",
                json={
                    "name": payload.name.strip(),
                    "email": payload.email.strip(),
                    "password": payload.password.strip(),
                    "role": payload.role,
                    "profile_image": payload.profile_image.strip() if payload.profile_image else None,
                }
            )
            if res.status_code == 400:
                raise HTTPException(status_code=400, detail=res.json().get("detail", "Email already registered"))
            elif res.status_code != 201:
                raise HTTPException(status_code=500, detail="User Service registration failed")

            user = res.json()
            user_role = user.get("role", "customer")
            token, expire = auth.create_access_token(
                data={"user_id": user["id"], "email": user["email"], "role": user_role}
            )

            # Persist JWT token, expiration datetime, and last_login into MySQL users_db.users
            now = datetime.now()
            try:
                await client.put(
                    f"{user_host}/users/{user['id']}/token",
                    json={
                        "access_token": token,
                        "token_expires_at": expire.strftime("%Y-%m-%d %H:%M:%S"),
                        "last_login": now.strftime("%Y-%m-%d %H:%M:%S")
                    }
                )
            except Exception as e:
                print(f"Token persistence note: {e}")

            return {
                "access_token": token,
                "token_type": "bearer",
                "user": user,
                "expires_in_minutes": auth.ACCESS_TOKEN_EXPIRE_MINUTES
            }
        except httpx.RequestError:
            raise HTTPException(status_code=503, detail="User Service is offline")


# ==============================================================================
# DYNAMIC REVERSE PROXY WITH JWT & RBAC VERIFICATION
# ==============================================================================
@app.api_route("/{service_prefix}", methods=["GET", "POST", "PUT", "DELETE"])
@app.api_route("/{service_prefix}/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def dynamic_reverse_proxy(service_prefix: str, request: Request, path: str = ""):
    """Catch-all reverse proxy route with ACL Whitelist and RBAC enforcement."""
    # Resolve downstream microservice URL
    target_host = SERVICE_URL_MAP.get(service_prefix)
    if not target_host:
        raise HTTPException(status_code=404, detail="Service mapping prefix not found")

    target_url = f"{target_host}{request.url.path}"
    method = request.method
    request_path = request.url.path
    query_params = request.query_params
    body = await request.body()

    # Headers cleanup (prevent host & content-length mismatches)
    headers = dict(request.headers)
    headers.pop("host", None)
    headers.pop("content-length", None)

    # Check if request is on the public whitelist
    is_public_route = any(
        method == m and (request_path == p or request_path.startswith(f"{p}/"))
        for m, p in PUBLIC_ROUTES
    )

    # Token & RBAC enforcement on protected routes
    user_payload = {}
    if not is_public_route:
        auth_header = headers.get("authorization", "")
        if not auth_header.startswith("Bearer "):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Access token is missing")

        token = auth_header.split(" ")[1]
        user_payload = auth.decode_access_token(token)
        if not user_payload:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Access token is invalid or expired")

        user_role = (user_payload.get("role") or "customer").lower()

        # RBAC: Only Admin can create, update, or delete products
        if service_prefix == "products" and method in ("POST", "PUT", "DELETE"):
            if user_role != "admin":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: Admin role required to create, modify, or delete products"
                )

        # RBAC: Only Admin can block or unblock users
        if service_prefix == "users" and any(act in path for act in ("block", "unblock", "toggle-block")):
            if user_role != "admin":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: Admin role required to block or unblock users"
                )

        # RBAC: Only Admin can block or unblock products
        if service_prefix == "products" and any(act in path for act in ("block", "unblock", "toggle-block")):
            if user_role != "admin":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: Admin role required to block or unblock products"
                )

        # Ingestion Security: Inject authenticated user_id into order body to prevent spoofing
        if service_prefix == "orders" and method == "POST" and body:
            try:
                body_json = json.loads(body)
                body_json["user_id"] = user_payload["user_id"]
                body = json.dumps(body_json).encode("utf-8")
            except Exception:
                raise HTTPException(status_code=400, detail="Invalid JSON request body")

        # Isolation: Customers can only view their own orders; Admins can view all orders
        if service_prefix == "orders" and method == "GET" and (path == "" or path == "/"):
            if user_role != "admin":
                query_params = dict(query_params)
                query_params["user_id"] = str(user_payload["user_id"])

        # Authorization: Standard users can only modify/delete their own profile
        if service_prefix == "users" and method in ("PUT", "DELETE"):
            clean_path = path.strip("/")
            if clean_path.isdigit():
                if user_role != "admin" and int(clean_path) != user_payload["user_id"]:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="You are not authorized to modify or delete another user's profile"
                    )

        # Authorization: Standard users can only modify/delete their own orders
        if service_prefix == "orders" and method in ("PUT", "DELETE"):
            if user_role != "admin":
                clean_path = path.strip("/")
                if clean_path.isdigit():
                    async with httpx.AsyncClient(timeout=5.0) as client:
                        try:
                            chk = await client.get(f"{target_host}/orders/{clean_path}")
                            if chk.status_code == 200:
                                order_info = chk.json()
                                if order_info.get("user_id") != user_payload["user_id"]:
                                    raise HTTPException(
                                        status_code=status.HTTP_403_FORBIDDEN,
                                        detail="You are not authorized to modify or delete another user's order"
                                    )
                        except httpx.RequestError:
                            pass

    # Forward request downstream and relay response back to client
    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            response = await client.request(
                method=method,
                url=target_url,
                headers=headers,
                params=query_params,
                content=body,
                follow_redirects=True
            )
            return Response(
                content=response.content,
                status_code=response.status_code,
                headers=dict(response.headers)
            )
        except httpx.RequestError:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"{service_prefix.capitalize()} service is offline"
            )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8010)
