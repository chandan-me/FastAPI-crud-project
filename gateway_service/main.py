import os
import json
import httpx
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
#   2. Local Auth Routes (/auth/*) validate credentials and issue JWT tokens.
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
    ("GET", "/products"),
]

class LoginRequest(BaseModel):
    email: str

class RegisterRequest(BaseModel):
    name: str
    email: str
    role: str = "customer"


# ==============================================================================
# [DATA TRAVEL FLOW - USER LOGIN]:
#   Step 1: Frontend sends { email } -> POST http://127.0.0.1:8010/auth/login
#   Step 2: Gateway forwards request -> GET http://127.0.0.1:8011/users/by-email?email=...
#   Step 3: User Service checks MySQL (users_db.users) and returns user record
#   Step 4: Gateway generates signed JWT { user_id, email, role, exp }
#   Step 5: Gateway returns { access_token, token_type, user } back to Frontend
# ==============================================================================
@app.post("/auth/login")
async def login(payload: LoginRequest):
    """Authenticates credentials against User Service and issues JWT."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            # Step 2: Forward lookup to User Service
            user_host = SERVICE_URL_MAP["users"]
            res = await client.get(f"{user_host}/users/by-email", params={"email": payload.email.strip()})
            if res.status_code == 404:
                raise HTTPException(status_code=401, detail="Email address not registered")
            elif res.status_code != 200:
                raise HTTPException(status_code=500, detail="User Service database connection failed")

            # Step 4: Issue signed JWT access token
            user = res.json()
            user_role = user.get("role", "customer")
            token = auth.create_access_token(data={"user_id": user["id"], "email": user["email"], "role": user_role})

            # Step 5: Return token and user profile to Frontend
            return {"access_token": token, "token_type": "bearer", "user": user}
        except httpx.RequestError:
            raise HTTPException(status_code=503, detail="User Service is offline")


# ==============================================================================
# [DATA TRAVEL FLOW - USER REGISTRATION]:
#   Step 1: Frontend sends { name, email, role } -> POST http://127.0.0.1:8010/auth/register
#   Step 2: Gateway forwards JSON -> POST http://127.0.0.1:8011/users/
#   Step 3: User Service inserts record into MySQL (users_db.users) and returns created user with ID
#   Step 4: Gateway signs new JWT containing { user_id, email, role, exp }
#   Step 5: Gateway returns { access_token, token_type, user } back to Frontend
# ==============================================================================
@app.post("/auth/register")
async def register(payload: RegisterRequest):
    """Registers user in User Service and issues JWT access token."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            # Step 2: Forward registration payload to User Service
            user_host = SERVICE_URL_MAP["users"]
            res = await client.post(f"{user_host}/users/", json=payload.dict())
            if res.status_code == 400:
                raise HTTPException(status_code=400, detail="Email already registered")
            elif res.status_code != 201:
                raise HTTPException(status_code=500, detail="User registration failed")

            # Step 4: Issue signed JWT token for the newly created user
            user = res.json()
            user_role = user.get("role", "customer")
            token = auth.create_access_token(data={"user_id": user["id"], "email": user["email"], "role": user_role})

            # Step 5: Return token and user profile to Frontend
            return {"access_token": token, "token_type": "bearer", "user": user}
        except httpx.RequestError:
            raise HTTPException(status_code=503, detail="User Service is offline")


# ==============================================================================
# [DATA TRAVEL FLOW - DYNAMIC REVERSE PROXY]:
#   Step 1: Frontend sends request -> http://127.0.0.1:8010/{service_prefix}/{path}
#   Step 2: Gateway verifies route against PUBLIC_ROUTES whitelist.
#           - If protected: validates Authorization: Bearer <token> & decodes JWT.
#   Step 3: Gateway enforces RBAC rules:
#           - Products: Only Admin can POST, PUT, DELETE.
#           - Orders POST: Injects authenticated user_id from token into body.
#           - Orders GET: Scopes customer view to their own user_id.
#           - Users/Orders PUT/DELETE: Prevents users from modifying other accounts.
#   Step 4: Gateway forwards request downstream using HTTPX:
#           - /users/*    -> http://127.0.0.1:8011/users/*
#           - /products/* -> http://127.0.0.1:8012/products/*
#           - /orders/*   -> http://127.0.0.1:8013/orders/*
#   Step 5: Target microservice responds; Gateway relays exact status & body to Frontend.
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
        method == m and request_path.startswith(p)
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

    # Step 4 & 5: Forward request downstream and relay response back to client
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
