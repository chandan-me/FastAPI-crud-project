# 🏛️ System Architecture & Data Travel Documentation

This document provides a complete visual and technical breakdown of the distributed microservices platform, its communication channels, and exact data travel flows.

---

## 1. High-Level Architecture Diagram

```mermaid
flowchart TD
    Client["💻 React Frontend\n(Port 5173)"]
    
    Gateway["🛡️ API Gateway\n(Port 8010)\n[JWT Auth & Reverse Proxy]"]
    
    subgraph Microservices ["Microservices Layer (Direct HTTP REST)"]
        UserService["👤 User Service\n(Port 8011)"]
        ProductService["📦 Product Service\n(Port 8012)"]
        OrderService["🛒 Order Service\n(Port 8013)"]
    end
    
    subgraph Databases ["Isolated MySQL Databases"]
        UserDB[("🗄️ users_db\n(users table)")]
        ProductDB[("🗄️ products_db\n(products table)")]
        OrderDB[("🗄️ orders_db\n(orders table)")]
    end

    %% Client to Gateway
    Client -->|"HTTP Requests\n(/auth, /products, /orders)"| Gateway

    %% Gateway to Microservices
    Gateway -->|"Proxy /users"| UserService
    Gateway -->|"Proxy /products"| ProductService
    Gateway -->|"Proxy /orders (JWT Verified)"| OrderService

    %% Inter-Service Distributed Saga Calls
    OrderService -.->|"1. Verify User Exists"| UserService
    OrderService -.->|"2. Check Stock & Price"| ProductService
    OrderService -.->|"3. Atomic Stock Deduction"| ProductService

    %% Referential Integrity Checks on Deletion
    UserService -.->|"Check Active Orders before Delete"| OrderService
    ProductService -.->|"Check Active Orders before Delete"| OrderService

    %% Database Connections
    UserService <--> UserDB
    ProductService <--> ProductDB
    OrderService <--> OrderDB
```

---

## 2. Service Directory & Network Ports

| Component | Port | Base URL | Swagger Docs | Database Schema | Primary Role |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **API Gateway** | `8010` | `http://127.0.0.1:8010` | `/docs` | Stateless / JWT | Single Entry Point, JWT Gatekeeper, RBAC, Reverse Proxy |
| **User Service** | `8011` | `http://127.0.0.1:8011` | `/docs` | MySQL: `users_db` | User Identity, Profiles, Role Management |
| **Product Service** | `8012` | `http://127.0.0.1:8012` | `/docs` | MySQL: `products_db` | Product Catalog, Pricing, Inventory Stock Tracking |
| **Order Service** | `8013` | `http://127.0.0.1:8013` | `/docs` | MySQL: `orders_db` | Saga Orchestration, Order Lifecycle, Data Federation |
| **React Frontend** | `5173` | `http://localhost:5173` | N/A (Web UI) | LocalStorage | Responsive User Dashboard, Catalog, Order UI |

---

## 3. Detailed Data Travel Flows

### Flow A: User Registration & Login (Authentication)

```mermaid
sequenceDiagram
    autonumber
    actor User as 👤 User
    participant FE as 💻 React Frontend (5173)
    participant GW as 🛡️ API Gateway (8010)
    participant US as 👤 User Service (8011)
    participant DB as 🗄️ MySQL (users_db)

    User->>FE: Fills Name, Email & Role
    FE->>GW: POST /auth/register
    GW->>US: POST http://127.0.0.1:8011/users/
    US->>DB: SELECT * FROM users WHERE email = ? (Duplicate Check)
    alt Email is already registered
        US-->>GW: 400 Bad Request ("Email already registered")
        GW-->>FE: 400 Bad Request
    else Email is unique
        US->>DB: INSERT INTO users (name, email, role) VALUES (...)
        DB-->>US: Return generated primary key ID
        US-->>GW: 201 Created { id: 1, name: "Alice", email: "...", role: "customer" }
        GW->>GW: Signs JWT Access Token containing { user_id, email, role }
        GW-->>FE: 200 OK { access_token: "eyJ...", token_type: "bearer", user: {...} }
        FE->>FE: Saves token & user object to localStorage
        FE-->>User: Logs in user & opens dashboard
    end
```

---

### Flow B: Public Product Catalog Browsing

```mermaid
sequenceDiagram
    autonumber
    actor User as 👤 User
    participant FE as 💻 React Frontend (5173)
    participant GW as 🛡️ API Gateway (8010)
    participant PS as 📦 Product Service (8012)
    participant DB as 🗄️ MySQL (products_db)

    User->>FE: Opens Catalog / Types in Search Box
    FE->>GW: GET /products?q=mouse (Unauthenticated / Public Whitelist)
    GW->>PS: Forward GET http://127.0.0.1:8012/products?q=mouse
    PS->>DB: SELECT * FROM products WHERE name LIKE '%mouse%'
    DB-->>PS: Rows matching query
    PS-->>GW: 200 OK [ { id: 1, name: "Wireless Mouse", price: 25.99, stock: 48 }, ... ]
    GW-->>FE: Relays Products Array
    FE-->>User: Renders Products Grid
```

---

### Flow C: Order Placement (Distributed Saga Transaction)

When an order is created, `order_service` acts as the orchestrator to verify the customer, check inventory, atomically deduct stock, and store the order.

```mermaid
sequenceDiagram
    autonumber
    actor User as 👤 Customer
    participant FE as 💻 React Frontend (5173)
    participant GW as 🛡️ API Gateway (8010)
    participant OS as 🛒 Order Service (8013)
    participant US as 👤 User Service (8011)
    participant PS as 📦 Product Service (8012)
    participant DB as 🗄️ MySQL (orders_db)

    User->>FE: Selects Quantity & Clicks "Place Order"
    FE->>GW: POST /orders (Headers: Authorization: Bearer <token>)
    GW->>GW: 1. Validate JWT Signature & Expiration<br/>2. Extract user_id & inject into payload
    GW->>OS: POST http://127.0.0.1:8013/orders { user_id, product_id, quantity }
    
    rect rgb(240, 248, 255)
    note right of OS: Distributed Saga Steps
    OS->>US: Step 1: GET http://127.0.0.1:8011/users/{user_id}
    US-->>OS: 200 OK (User exists & is valid)
    
    OS->>PS: Step 2: GET http://127.0.0.1:8012/products/{product_id}
    PS-->>OS: 200 OK (Product data & stock: 48)
    
    OS->>OS: Assert available stock (48 >= quantity)
    
    OS->>PS: Step 3: PUT http://127.0.0.1:8012/products/{product_id}/reduce-stock { quantity }
    PS-->>OS: 200 OK (Stock deducted to 46 in products_db)
    end

    OS->>DB: Step 4: INSERT INTO orders (user_id, product_id, quantity, total_price, status='COMPLETED')
    DB-->>OS: Return created order record with ID
    OS-->>GW: 201 Created { id: 5, user_id: 1, product_id: 2, total_price: 51.98, status: "COMPLETED" }
    GW-->>FE: 201 Created
    FE-->>User: Displays Order Confirmation & Refreshes Stock
```

---

### Flow D: Federated Order Details (Data Aggregation)

```mermaid
sequenceDiagram
    autonumber
    actor User as 👤 User / Admin
    participant FE as 💻 React Frontend (5173)
    participant GW as 🛡️ API Gateway (8010)
    participant OS as 🛒 Order Service (8013)
    participant US as 👤 User Service (8011)
    participant PS as 📦 Product Service (8012)
    participant DB as 🗄️ MySQL (orders_db)

    User->>FE: Clicks "View Details" on Order #5
    FE->>GW: GET /orders/5/details (Bearer JWT)
    GW->>OS: GET http://127.0.0.1:8013/orders/5/details
    OS->>DB: SELECT * FROM orders WHERE id = 5
    
    par Query User Service
        OS->>US: GET http://127.0.0.1:8011/users/{order.user_id}
        US-->>OS: { name: "Alice", email: "alice@example.com" }
    and Query Product Service
        OS->>PS: GET http://127.0.0.1:8012/products/{order.product_id}
        PS-->>OS: { name: "Wireless Mouse", price: 25.99 }
    end

    OS->>OS: Merge order + user_details + product_details
    OS-->>GW: Consolidated OrderDetail JSON
    GW-->>FE: 200 OK
    FE-->>User: Renders Order Modal with Customer Name & Product Title
```

---

### Flow E: Order Cancellation & Compensating Stock Restoration

```mermaid
sequenceDiagram
    autonumber
    actor Admin as 🛡️ Admin / User
    participant FE as 💻 React Frontend (5173)
    participant GW as 🛡️ API Gateway (8010)
    participant OS as 🛒 Order Service (8013)
    participant PS as 📦 Product Service (8012)
    participant DB as 🗄️ MySQL (orders_db)

    Admin->>FE: Clicks "Cancel Order"
    FE->>GW: PUT /orders/5 { status: "CANCELLED" }
    GW->>OS: PUT http://127.0.0.1:8013/orders/5 { status: "CANCELLED" }
    
    rect rgb(255, 245, 245)
    note right of OS: Compensating Action
    OS->>PS: PUT http://127.0.0.1:8012/products/{product_id}/restore-stock { quantity }
    PS-->>OS: 200 OK (Stock restored in products_db)
    end

    OS->>DB: UPDATE orders SET status = 'CANCELLED' WHERE id = 5
    OS-->>GW: 200 OK { id: 5, status: "CANCELLED" }
    GW-->>FE: 200 OK
    FE-->>Admin: Updates order badge to CANCELLED
```

---

### Flow F: Distributed Referential Integrity (Safe Deletion)

```mermaid
sequenceDiagram
    autonumber
    actor Admin as 🛡️ Admin
    participant GW as 🛡️ API Gateway (8010)
    participant US as 👤 User Service (8011)
    participant OS as 🛒 Order Service (8013)
    participant DB as 🗄️ MySQL (users_db)

    Admin->>GW: DELETE /users/3
    GW->>US: DELETE http://127.0.0.1:8011/users/3
    US->>OS: GET http://127.0.0.1:8013/orders?user_id=3
    
    alt User has associated orders
        OS-->>US: [ { id: 10, ... }, { id: 11, ... } ]
        US-->>GW: 400 Bad Request ("Cannot delete user with associated orders")
        GW-->>Admin: Deletion Blocked
    else User has 0 orders
        OS-->>US: [ ] (Empty array)
        US->>DB: DELETE FROM users WHERE id = 3
        US-->>GW: 200 OK { "message": "User #3 deleted successfully" }
        GW-->>Admin: Deletion Confirmed
    end
```

---

## 4. Code File Architecture Map

```
microservices/
├── .env                         # Central DB passwords, JWT secrets, and port configs
├── README.md                    # Project overview and quick start manual
├── ARCHITECTURE.md              # THIS DOCUMENT (Visual flow and technical reference)
├── run_all.py                   # Master process runner for all 5 components
├── test_crud.py                 # Automated 17/17 RBAC & CRUD integration test suite
├── verify.py                    # Gateway & distributed flow verification script
│
├── gateway_service/             # API GATEWAY (Port 8010)
│   ├── auth.py                  # JWT encoding, decoding, expiration validation
│   └── main.py                  # Catch-all reverse proxy, ACL whitelist, RBAC logic
│
├── user_service/                # USER MICROSERVICE (Port 8011)
│   ├── database.py              # PyMySQL engine (users_db) with connection pooling
│   ├── models.py                # SQLAlchemy ORM User entity
│   ├── schemas.py               # Pydantic schemas (UserCreate, UserUpdate, User)
│   └── main.py                  # FastAPI route controllers & DB CRUD operations
│
├── product_service/             # PRODUCT MICROSERVICE (Port 8012)
│   ├── database.py              # PyMySQL engine (products_db) with connection pooling
│   ├── models.py                # SQLAlchemy ORM Product entity
│   ├── schemas.py               # Pydantic schemas (ProductCreate, ProductUpdate, etc.)
│   └── main.py                  # Catalog endpoints, search/filter, atomic stock reduction
│
├── order_service/               # ORDER MICROSERVICE (Port 8013)
│   ├── database.py              # PyMySQL engine (orders_db) with connection pooling
│   ├── models.py                # SQLAlchemy ORM Order entity
│   ├── schemas.py               # Pydantic schemas (OrderCreate, OrderDetail, etc.)
│   └── main.py                  # Saga coordinator, inter-service HTTPX calls, federation
│
└── frontend/                    # REACT 18 + VITE (Port 5173)
    ├── package.json             # NPM dependencies
    ├── vite.config.js           # Vite dev server configuration
    └── src/
        ├── App.jsx              # Unified user dashboard, catalog, auth, order manager
        └── index.css            # Responsive layout styling
```

