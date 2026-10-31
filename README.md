# Layered FastAPI MySQL Microservices & React Dashboard

A production-grade, distributed microservices platform built with **Python (FastAPI)**, **MySQL**, and **React (Vite)**. The platform implements an API gateway with direct routing and JWT gatekeeper security, dynamic reverse proxying, per-service isolated databases, and distributed saga transactions for order processing with automated inventory deduction.

---

## 🏛️ System Architecture

```mermaid
flowchart TD
    Client["💻 React Web Dashboard\n(Port 5173)"]
    Gateway["🛡️ API Gateway\n(Port 8010)"]
    
    subgraph Microservices ["Isolated Domain Microservices"]
        UserService["👤 User Service\n(Port 8011)"]
        ProductService["📦 Product Service\n(Port 8012)"]
        OrderService["🛒 Order Service\n(Port 8013)"]
    end
    
    subgraph Databases ["MySQL Isolated Databases"]
        UserDB[("🗄️ users_db")]
        ProductDB[("🗄️ products_db")]
        OrderDB[("🗄️ orders_db")]
    end

    Client -->|HTTP / REST| Gateway
    Gateway -->|Proxy /auth, /users| UserService
    Gateway -->|Proxy /products| ProductService
    Gateway -->|Proxy /orders (JWT Verified)| OrderService

    OrderService -.->|1. Verify User Exists| UserService
    OrderService -.->|2. Verify Stock Availability| ProductService
    OrderService -.->|3. Atomic Stock Deduction| ProductService

    UserService --- UserDB
    ProductService --- ProductDB
    OrderService --- OrderDB
```

---

## 🧭 Service Port Directory

| Component | Port | Base URL | Interactive Docs (Swagger) | Database |
| :--- | :--- | :--- | :--- | :--- |
| **API Gateway** | `8010` | `http://127.0.0.1:8010` | `http://127.0.0.1:8010/docs` | Stateless / JWT |
| **User Service** | `8011` | `http://127.0.0.1:8011` | `http://127.0.0.1:8011/docs` | MySQL: `users_db` |
| **Product Service** | `8012` | `http://127.0.0.1:8012` | `http://127.0.0.1:8012/docs` | MySQL: `products_db` |
| **Order Service** | `8013` | `http://127.0.0.1:8013` | `http://127.0.0.1:8013/docs` | MySQL: `orders_db` |
| **React Frontend** | `5173` | `http://localhost:5173` | N/A (Web UI) | Browser LocalStorage |

---

## 📂 Clean Architecture Directory Structure

Every service strictly follows the **Separation of Concerns (SoC)** layered architecture:

```
microservices/
├── .env                         # Central configuration & database credentials
├── .env.example                 # Environment configuration template
├── .gitignore                   # Ignored files (logs, caches, node_modules)
├── README.md                    # System documentation & manual
├── requirements.txt             # Python packages & dependencies
├── run_all.py                   # Master process orchestrator
├── verify.py                    # End-to-end integration test suite
│
├── gateway_service/             # Central API Gateway
│   ├── auth.py                  # JWT encoding, decoding & token gatekeeper
│   └── main.py                  # Direct reverse proxy & routing
│
├── user_service/                # User Domain Service (Port 8011)
│   ├── config.py                # Environment & SQLAlchemy URL generator
│   ├── database.py              # Engine setup & SessionLocal dependency
│   ├── models.py                # SQLAlchemy ORM model ('users' table)
│   ├── schemas.py               # Pydantic schemas (UserCreate, UserResponse)
│   ├── routers/user_router.py   # FastAPI route controller
│   ├── services/user_service.py # Database queries & CRUD operations
│   └── main.py                  # Application entry point
│
├── product_service/             # Product Domain Service (Port 8012)
│   ├── config.py, database.py, main.py
│   ├── models.py                # SQLAlchemy ORM model ('products' table)
│   ├── schemas.py               # Pydantic schemas (ProductCreate, ProductUpdate)
│   ├── routers/product_router.py
│   └── services/product_service.py # Inventory management & stock reduction
│
├── order_service/               # Order Domain Service (Port 8013)
│   ├── config.py, database.py, main.py
│   ├── models.py                # SQLAlchemy ORM model ('orders' table)
│   ├── schemas.py               # Pydantic schemas (OrderCreate, OrderDetail)
│   ├── routers/order_router.py  # User-scoped order endpoints
│   └── services/order_service.py # Distributed saga coordinator & HTTPX clients
│
└── frontend/                    # Single-Page Application (React 18 + Vite)
    ├── package.json
    ├── vite.config.js
    └── src/
        ├── App.jsx              # Marketplace dashboard, auth modal, order UI
        ├── index.css            # Custom responsive modern stylesheet
        └── main.jsx             # React DOM root entry
```

---

## 🚀 Getting Started

### 1. Prerequisites
- **Python**: Version 3.10 or higher.
- **Node.js**: Version 18.0 or higher (with `npm`).
- **MySQL Community Server**: Running on `localhost:3306`.

---

### 2. Configure Environment (`.env`)
Create or edit your [.env](file:///c:/Users/user/Downloads/microservices/.env) file at the workspace root:

```env
# MySQL Connection Configuration
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_mysql_password_here

# JWT Security
JWT_SECRET=demo_secret_key_Demo_gatekeeper_auth_2026
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440
```

---

### 3. Install Dependencies

#### Python Packages
```powershell
pip install -r requirements.txt
```

#### Frontend Packages
```powershell
cd frontend
npm install
cd ..
```

---

### 4. Start the Entire Workspace
Launch all 3 Microservices, the API Gateway, and the React Frontend concurrently:

```powershell
python run_all.py
```

When all services are ready, open your browser:
- **🛍️ React Marketplace UI**: [http://localhost:5173](http://localhost:5173)
- **🛡️ API Gateway Swagger Docs**: [http://127.0.0.1:8010/docs](http://127.0.0.1:8010/docs)

*(Press `Ctrl+C` in the terminal to gracefully terminate all processes).*

---

## 🧪 Automated Verification & Test Suites

### 1. Comprehensive CRUD Test Suite
Run the automated end-to-end CRUD suite verifying all 23 lifecycle checks:

```powershell
python test_crud.py
```

### 2. Integration & Security Suite
Run the gateway proxying and token verification suite:

```powershell
python verify.py
```

This automated test script verifies:
1. **JWT Security Gatekeeper**: Asserts that requests to protected routes without a valid Bearer token are blocked with `401 Unauthorized`.
2. **Authentication Flow**: Authenticates a user and generates a signed 24-hour JWT token.
3. **Public Route Routing**: Verifies that public routes (e.g. `GET /products`) pass through the Gateway without requiring credentials.
4. **Distributed Order Saga Transaction**: Submits an order through the Gateway; verifies that the Order Service verifies user existence, asserts product stock, and decrements inventory in the Product Service database atomically.
5. **Inventory Assertion**: Confirms that stock levels in the Product Service database decremented accurately.
6. **Data Federation / Aggregated Read**: Calls `GET /orders/{id}/details` and confirms federated synthesis across all three services.

---

## 🔑 Core Features & Architectural Patterns

### 1. Direct API Gateway Routing
- Direct reverse proxy routing on port `8010` to downstream microservices without discovery client overhead.
- Configurable service target URLs via environment variables (`USER_SERVICE_URL`, `PRODUCT_SERVICE_URL`, `ORDER_SERVICE_URL`).
- Fast and resilient request forwarding without client heartbeats or registration background threads.

### 2. API Gateway & Token Security
- Centralized reverse proxy running on port `8010`.
- Issues signed JSON Web Tokens (JWT) using the `HS256` algorithm with configurable expiration (`ACCESS_TOKEN_EXPIRE_MINUTES=1440`).
- Validates the `Authorization: Bearer <token>` header on all non-public endpoints.
- Auto-injects verified user context (`user_id`) into downstream requests, preventing identity spoofing.

### 3. Distributed Order Saga Transaction
When placing an order (`POST /orders`):
1. **User Existence Check**: Order Service calls User Service (`GET http://localhost:8011/users/{user_id}`).
2. **Catalog & Stock Check**: Order Service calls Product Service (`GET http://localhost:8012/products/{product_id}`).
3. **Inventory Deduction**: Order Service triggers stock reduction in Product Service (`PUT http://localhost:8012/products/{product_id}/reduce-stock`).
4. **Order Commitment**: Upon downstream confirmation, the order is committed into `orders_db` with `status: "COMPLETED"`.
5. If any validation fails (e.g., user not found or insufficient inventory), the transaction halts and an HTTP `400` error is returned.

### 4. Role-Based Access Control (RBAC): Admin vs Customer
The system defines two primary roles:
- **`admin`**:
  - Full product catalog CRUD: Can **Add** (`POST /products`), **Edit** (`PUT /products/{id}`), **Delete** (`DELETE /products/{id}`), and **Restock/Reduce** inventory.
  - Full order oversight: Can view all customer orders across the platform and cancel/delete orders.
  - Can manage and view user profiles.
  - Interactive UI displays admin badge, "Add Product" button, and inline "Edit" & "Delete" controls.
- **`customer`**:
  - Read-only catalog browsing with search and price filtering.
  - **Can only purchase items** via `POST /orders`.
  - Strictly blocked from adding, editing, or deleting products (`403 Forbidden`).
  - Can only view their own order history (`GET /orders?user_id={id}`).
  - Product management buttons are hidden in the UI.

### 5. Indian Rupee (`₹`) Localization
- All currency values across the Product Catalog, Purchase Order form, Transaction History, and Aggregated Order views are standardized to **`₹`**.

---

## 📚 API Endpoints Summary

### Authentication (`gateway_service`)
- `POST /auth/register` — Register a new account and receive a JWT access token.
- `POST /auth/login` — Log in with email and receive a JWT access token.

### User Service (`/users`)
- `GET /users/` — List users with pagination (`?skip=0&limit=100`).
- `GET /users/{id}` — Get user profile by ID.
- `POST /users/` — Create a new user.
- `PUT /users/{id}` — Update user profile (`name`, `email`).
- `DELETE /users/{id}` — Safely delete user (blocked if active orders exist).

### Product Service (`/products`)
- `GET /products/` — Retrieve products with pagination, search (`?q=...`), price range (`?min_price=...&max_price=...`), and stock filter (`?in_stock=true`).
- `GET /products/{id}` — Retrieve single product details.
- `POST /products/` — Add a new product to inventory with price & stock validation.
- `PUT /products/{id}` — Update product name, price, or stock levels.
- `PUT /products/{id}/reduce-stock` — Deduct inventory quantity (called by Order Service).
- `PUT /products/{id}/restore-stock` — Restore inventory quantity (called on order cancellation).
- `DELETE /products/{id}` — Safely delete product (blocked if active orders reference it).

### Order Service (`/orders`)
- `GET /orders?user_id={id}` — Retrieve orders (scoped to authenticated user, paginated).
- `GET /orders/{id}` — Get single order record.
- `POST /orders/` — Place purchase order (orchestrates distributed stock check & deduction).
- `GET /orders/{id}/details` — Aggregated order details with customer and product information.
- `PUT /orders/{id}` — Update order status (transition to `CANCELLED` automatically restores product inventory).
- `DELETE /orders/{id}` — Delete/cancel order record (releases reserved inventory back to Product Service).

---

## 🛠️ Troubleshooting

### Port Collision (`[Errno 10048]`)
If a previous session did not close cleanly:
```powershell
# Check for processes on microservice ports:
Get-NetTCPConnection -LocalPort 8010, 8011, 8012, 8013, 5173 -ErrorAction SilentlyContinue

# Terminate orphaned Python or Node processes:
Stop-Process -Name python, node -Force
```
