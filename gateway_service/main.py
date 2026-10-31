from fastapi import FastAPI, Request, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
import httpx
from pydantic import BaseModel
from . import auth
import json
import os

# =====================================================================
# API GATEWAY (Direct Microservice Routing with ACL Whitelist)
# 
# Routes requests directly to microservice instances.
# 
# Key Features:
#   1. Whitelist Access Control: Protects all routes by default except login/catalog.
#   2. Direct Service Resolution: Maps service routes to downstream service ports.
#   3. RBAC Enforcement: Admin vs Customer roles.
# =====================================================================

app = FastAPI(
    title="API Gateway", 
    description="API Gateway with Direct Routing & ACL Whitelist"
)

# Enable CORS for React Frontend (Port 5173)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Direct Static Service Mappings
SERVICE_URL_MAP = {
    "users": os.getenv("USER_SERVICE_URL", "http://127.0.0.1:8011"),
    "products": os.getenv("PRODUCT_SERVICE_URL", "http://127.0.0.1:8012"),
    "orders": os.getenv("ORDER_SERVICE_URL", "http://127.0.0.1:8013"),
}

async def resolve_service_url(service_prefix: str) -> str:
    """
    Resolves the direct host URL for a service.
    """
    target_url = SERVICE_URL_MAP.get(service_prefix)
    if not target_url:
        raise HTTPException(status_code=404, detail="Service mapping prefix not found")
    return target_url

# ACCESS CONTROL LIST (ACL) Whitelist
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

# ---------------------------------------------------------------------
# 1. GATEWAY AUTHENTICATION ENDPOINTS (Local Gateway Auth Handling)
# ---------------------------------------------------------------------

@app.post("/auth/login")
async def login(payload: LoginRequest):
    """Authenticates credentials against User Service database and issues JWT."""
    async with httpx.AsyncClient() as client:
        try:
            # Query User Service
            user_host = await resolve_service_url("users")
            res = await client.get(f"{user_host}/users/by-email", params={"email": payload.email.strip()})
            if res.status_code == 404:
                raise HTTPException(status_code=401, detail="Email address not registered")
            elif res.status_code != 200:
                raise HTTPException(status_code=500, detail="User Service database connection failed")
            
            user = res.json()
            user_role = user.get("role", "customer")
            token = auth.create_access_token(data={"user_id": user["id"], "email": user["email"], "role": user_role})
            return {"access_token": token, "token_type": "bearer", "user": user}
        except httpx.RequestError:
            raise HTTPException(status_code=503, detail="User Service is offline")

@app.post("/auth/register")
async def register(payload: RegisterRequest):
    """Registers user in User Service and issues JWT access token."""
    async with httpx.AsyncClient() as client:
        try:
            # Resolve downstream User Service
            user_host = await resolve_service_url("users")
            res = await client.post(f"{user_host}/users/", json=payload.dict())
            if res.status_code == 400:
                raise HTTPException(status_code=400, detail="Email already registered")
            elif res.status_code != 201:
                raise HTTPException(status_code=500, detail="User registration failed")
            
            user = res.json()
            user_role = user.get("role", "customer")
            token = auth.create_access_token(data={"user_id": user["id"], "email": user["email"], "role": user_role})
            return {"access_token": token, "token_type": "bearer", "user": user}
        except httpx.RequestError:
            raise HTTPException(status_code=503, detail="User Service is offline")

# ---------------------------------------------------------------------
# 2. DYNAMIC CATCH-ALL REVERSE PROXY ROUTE (With Whitelist Enforcement)
# ---------------------------------------------------------------------

@app.api_route("/{service_prefix}", methods=["GET", "POST", "PUT", "DELETE"])
@app.api_route("/{service_prefix}/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def dynamic_reverse_proxy(service_prefix: str, request: Request, path: str = ""):
    """
    Catch-all route. Intercepts incoming requests dynamically.
    - Resolves downstream service URL directly.
    - Inspects prefix and path against PUBLIC_ROUTES whitelist.
    - Enforces JWT validation if the route is protected.
    - Applies Role-Based Access Control (RBAC): Admin vs Customer.
    - Forwards request content downstream, returning response back to client.
    """
    # 1. Resolve microservice address directly
    target_host = await resolve_service_url(service_prefix)
    target_url = f"{target_host}{request.url.path}"
    
    # 2. Clone headers and prepare request parameters
    headers = dict(request.headers)
    headers.pop("host", None) # Prevent destination host mismatches
    headers.pop("content-length", None) # Allow HTTPX to recalculate size dynamically
    query_params = request.query_params
    method = request.method
    body = await request.body()
    
    # 3. Whitelist Check (Access Control List Validation)
    request_path = request.url.path
    is_public_route = False
    
    for allowed_method, allowed_prefix in PUBLIC_ROUTES:
        if method == allowed_method and request_path.startswith(allowed_prefix):
            is_public_route = True
            break

    # 4. Enforce Token Security on Protected Routes
    user_payload = {}
    if not is_public_route:
        auth_header = headers.get("authorization", "")
        if not auth_header.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, 
                detail="Access token is missing"
            )
        
        token = auth_header.split(" ")[1]
        user_payload = auth.decode_access_token(token)
        if not user_payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, 
                detail="Access token is invalid or expired"
            )

        user_role = (user_payload.get("role") or "customer").lower()

        # 4.1 RBAC Enforcement for Product Management:
        # ONLY Admin can Create, Update, or Delete products (Customers can only view and purchase)
        if service_prefix == "products" and method in ("POST", "PUT", "DELETE"):
            if user_role != "admin":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: Admin role required to create, modify, or delete products"
                )

        # 4.2 Secure Ingestion: If creating order, inject user_id from token to prevent spoofing
        if service_prefix == "orders" and method == "POST" and body:
            try:
                body_json = json.loads(body)
                body_json["user_id"] = user_payload["user_id"]
                body = json.dumps(body_json).encode("utf-8")
                headers.pop("content-length", None)
            except Exception:
                raise HTTPException(status_code=400, detail="Invalid JSON request body")

        # 4.3 Secure Isolation: Customers can only view their own orders; Admins can view all orders
        if service_prefix == "orders" and method == "GET" and (path == "" or path == "/"):
            if user_role != "admin":
                query_params = dict(query_params)
                query_params["user_id"] = str(user_payload["user_id"])

        # 4.4 Secure Authorization: Users can only modify or delete their own profile (unless admin)
        if service_prefix == "users" and method in ("PUT", "DELETE"):
            clean_path = path.strip("/")
            if clean_path.isdigit():
                if user_role != "admin" and int(clean_path) != user_payload["user_id"]:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="You are not authorized to modify or delete another user's profile"
                    )

    # 5. Proxy/Forward the request to the correct microservice using HTTPX Client
    async with httpx.AsyncClient() as client:
        # Check order ownership for PUT / DELETE on orders (Admins can manage any; Customers only their own)
        if not is_public_route and service_prefix == "orders" and method in ("PUT", "DELETE"):
            user_role = (user_payload.get("role") or "customer").lower()
            if user_role != "admin":
                clean_path = path.strip("/")
                if clean_path.isdigit():
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

        try:
            response = await client.request(
                method=method,
                url=target_url,
                headers=headers,
                params=query_params,
                content=body,
                follow_redirects=True, # Follow redirects (like trailing slash adjustments)
                timeout=15.0
            )
            
            # Return the exact response from the microservice (content, status, headers)
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
