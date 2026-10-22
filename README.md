# Layered FastAPI MySQL Microservices Demo

This repository contains a professional, layered demonstration of a microservices architecture. It showcases 3 independent services with separate MySQL databases communicating with each other over HTTP.

## Professional Clean Architecture Folder Structure

Each service follows a standard layered structure (Separation of Concerns):

```
microservices/
├── .env                     # Central database credentials configuration
├── requirements.txt         # Added pymysql, cryptography, python-dotenv
├── run_all.py               # Starts services
├── verify.py                # Validation tests
└── user_service/            # Same layout is applied to product_service & order_service
    ├── config.py            # Environment configuration
    ├── database.py          # SQLAlchemy Session and Engine setup
    ├── models.py            # Declarative database models (MySQL compatible)
    ├── schemas.py           # Pydantic schemas for request/response validation
    ├── services/
    │   └── user_service.py  # Business logic layer (CRUD operations, querying)
    ├── routers/
    │   └── user_router.py   # FastAPI APIRouter endpoints
    └── main.py              # Application main entry point
```

---

## Getting Started

### 1. Configure MySQL Credentials (`.env`)
Open the [.env](file:///c:/Projects/microservices/.env) file in the root directory and configure your MySQL server details:

```env
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=your_username
MYSQL_PASSWORD=your_password
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Initialize/Seed Databases (Optional)
Since you already ran the script in **MySQL Workbench**, your databases (`users_db`, `products_db`, `orders_db`) are set up and seeded. 

If you ever need to reset or seed them programmatically, run:
```bash
python seed_databases.py
```

### 4. Run the Microservices
Start all three services concurrently:
```bash
python run_all.py
```
You will see output indicating that all 3 services are running:
* **User Service**: http://127.0.0.1:8001/docs
* **Product Service**: http://127.0.0.1:8002/docs
* **Order Service**: http://127.0.0.1:8003/docs

*(Open these links in your browser to interact with the endpoints directly using FastAPI's interactive Swagger UI).*

---

## Verifying Inter-Service Communication

While the services are running in one terminal (from `python run_all.py`), open another terminal window and run:
```bash
python verify.py
```
This script will test:
1. **User Service** retrieval.
2. **Product Service** retrieval.
3. Placing a valid order via **Order Service** (which triggers background calls to verify user, check stock, and reduce stock).
4. Verifying that the product stock was correctly updated in **Product Service** DB.
5. Graceful handling of invalid user IDs and out-of-stock items.
6. Retrieval of aggregated order details (fetching info from all 3 services to present a unified model).
