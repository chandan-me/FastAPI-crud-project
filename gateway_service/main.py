from fastapi import FastAPI, Request, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
import httpx
from pydantic import BaseModel
from . import auth
import json
import time

# =====================================================================
# CLOUD-NATIVE DYNAMIC API GATEWAY WITH SERVICE DISCOVERY RESOLUTION
# 
# Instead of hardcoding microservice ports (static discovery), this Gateway
# acts as a client to the Demo Discovery Registry (netflix-eureka-like, Port 8761).
# 
# Key Features:
#   1. Whitelist Access Control: Protects all routes by default except login/catalog.
#   2. Dynamic Service Resolution: Queries Port 8761 to resolve service destinations.
#   3. Local Cache Resilience: Replicates Eureka's local cache strategy to survive
#      transient discovery server outages.
# =====================================================================

app = FastAPI(
    title="API Gateway", 
    description="Cloud-Native Catch-All Gateway with Service Discovery & ACL Whitelist"
)

# Enable CORS for React Frontend (Port 5173)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dynamic Discovery Mappings
DISCOVERY_SERVER_URL = "http://localhost:8762/eureka/apps"

# Maps incoming URL prefixes to the application names registered in Eureka
SERVICE_APP_MAP = {
    "users": "USER-SERVICE",
    "products": "PRODUCT-SERVICE",
    "orders": "ORDER-SERVICE"
}

# In-memory local cache mimicking Spring Cloud Eureka Client caching
DISCOVERY_CACHE = {}
CACHE_EXPIRY_SECONDS = 10
last_cache_refresh = 0

async def resolve_service_url(service_prefix: str) -> str:
    """
    Queries the Discovery Registry (Port 8761) to find the host URL of a service.
    Implements local caching (Eureka Client behavior) for performance and resilience.
    """
    global last_cache_refresh
    now = time.time()
    
    # If the cached mapping is still fresh (< 10 seconds), return it immediately
    if service_prefix in DISCOVERY_CACHE and (now - last_cache_refresh) < CACHE_EXPIRY_SECONDS:
        return DISCOVERY_CACHE[service_prefix]

    # Map prefix (e.g. 'users') to registration name (e.g. 'USER-SERVICE')
    app_name = SERVICE_APP_MAP.get(service_prefix)
    if not app_name:
        raise HTTPException(status_code=404, detail="Service mapping prefix not found")

    async with httpx.AsyncClient() as client:
        try:
            # Query the central Eureka-compatible service registry
            res = await client.get(DISCOVERY_SERVER_URL, timeout=3.0)
            if res.status_code == 200:
                apps = res.json()
                instances = apps.get(app_name, [])
                if not instances:
                    # Fallback to local cache if registry is clean but temporarily empty
                    if service_prefix in DISCOVERY_CACHE:
                        print(f"[Gateway] Service registry empty for {app_name}. Using fallback cache.")
                        return DISCOVERY_CACHE[service_prefix]
                    raise HTTPException(
                        status_code=503, 
                        detail=f"No healthy instances of {app_name} found in discovery registry"
                    )
                
                # Dynamic IP resolution: Extract the first registered instance URL (Load Balancing)
                target_url = instances[0]["url"]
                DISCOVERY_CACHE[service_prefix] = target_url
                last_cache_refresh = now
                return target_url
            else:
                # Return cached version if registry returns server error
                if service_prefix in DISCOVERY_CACHE:
                    return DISCOVERY_CACHE[service_prefix]
                raise HTTPException(status_code=500, detail="Discovery Registry Server returned an error")
        except httpx.RequestError:
            # Registry Outage Resiliency: Fallback to local cache if Discovery Server is offline
            if service_prefix in DISCOVERY_CACHE:
                print(f"[Gateway] Discovery Server offline. Returning cached address: {DISCOVERY_CACHE[service_prefix]}")
                return DISCOVERY_CACHE[service_prefix]
            raise HTTPException(status_code=503, detail="Discovery Server (Port 8761) is offline and no fallback cache exists")

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

# ---------------------------------------------------------------------
# 1. GATEWAY AUTHENTICATION ENDPOINTS (Local Gateway Auth Handling)
# ---------------------------------------------------------------------

@app.post("/auth/login")
async def login(payload: LoginRequest):
    """Authenticates credentials against User Service database and issues JWT."""
    async with httpx.AsyncClient() as client:
        try:
            # Query User Service dynamically using Service Discovery
            user_host = await resolve_service_url("users")
            res = await client.get(f"{user_host}/users/")
            if res.status_code != 200:
                raise HTTPException(status_code=500, detail="User Service database connection failed")
            
            users = res.json()
            user = next((u for u in users if u["email"].lower() == payload.email.lower()), None)
            
            if not user:
                raise HTTPException(status_code=401, detail="Email address not registered")
            
            token = auth.create_access_token(data={"user_id": user["id"], "email": user["email"]})
            return {"access_token": token, "token_type": "bearer", "user": user}
        except httpx.RequestError:
            raise HTTPException(status_code=503, detail="User Service is offline")

@app.post("/auth/register")
async def register(payload: RegisterRequest):
    """Registers user in User Service and issues JWT access token."""
    async with httpx.AsyncClient() as client:
        try:
            # Resolve downstream User Service dynamically
            user_host = await resolve_service_url("users")
            res = await client.post(f"{user_host}/users/", json=payload.dict())
            if res.status_code == 400:
                raise HTTPException(status_code=400, detail="Email already registered")
            elif res.status_code != 201:
                raise HTTPException(status_code=500, detail="User registration failed")
            
            user = res.json()
            token = auth.create_access_token(data={"user_id": user["id"], "email": user["email"]})
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
    - Resolves downstream service URL dynamically using Discovery Server.
    - Inspects prefix and path against PUBLIC_ROUTES whitelist.
    - Enforces JWT validation if the route is protected.
    - Forwards request content downstream, returning response back to client.
    """
    # 1. Resolve microservice address dynamically from Discovery Registry
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
            
        # Secure Ingestion: If creating order, inject user_id from token to prevent spoofing
        if service_prefix == "orders" and method == "POST" and body:
            try:
                body_json = json.loads(body)
                body_json["user_id"] = user_payload["user_id"]
                body = json.dumps(body_json).encode("utf-8")
            except Exception:
                raise HTTPException(status_code=400, detail="Invalid JSON request body")

    # 5. Proxy/Forward the request to the correct microservice using HTTPX Client
    async with httpx.AsyncClient() as client:
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
