import os
import pymysql
from dotenv import load_dotenv

# =====================================================================
# SEED DATABASES SCRIPT
# This script reads MySQL credentials from '.env', connects to the MySQL
# server, creates schemas if missing, and populates tables with initial mock values.
# =====================================================================

# Load environment configurations
load_dotenv()

MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")

def seed_db(db_name, sql_statements):
    """
    Connects to MySQL server, creates the specified database, selects it,
    and runs a sequence of SQL queries.
    """
    print(f"Creating and seeding database: {db_name}...")
    try:
        # Establish connection to MySQL server
        connection = pymysql.connect(
            host=MYSQL_HOST,
            port=MYSQL_PORT,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            autocommit=True
        )
        with connection.cursor() as cursor:
            # 1. Create schema if it does not exist
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {db_name};")
            
            # 2. Select database context
            cursor.execute(f"USE {db_name};")
            
            # 3. Execute SQL queries sequentially
            for statement in sql_statements:
                if statement.strip():
                    cursor.execute(statement)
        connection.close()
        print(f"Successfully seeded {db_name}!\n")
    except Exception as e:
        print(f"Error seeding {db_name}: {e}\n")

def main():
    # User Service seeding queries
    user_statements = [
        "DROP TABLE IF EXISTS users;",
        """CREATE TABLE users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            email VARCHAR(255) UNIQUE NOT NULL,
            role VARCHAR(50) NOT NULL DEFAULT 'customer'
        );""",
        "INSERT INTO users (name, email, role) VALUES ('Alice Johnson (Admin)', 'alice@gmail.com', 'admin');",
        "INSERT INTO users (name, email, role) VALUES ('Bob Smith (Customer)', 'bob@gmail.com', 'customer');",
        "INSERT INTO users (name, email, role) VALUES ('Charlie Brown (Customer)', 'charlie@example.com', 'customer');"
    ]

    # Product Service seeding queries
    product_statements = [
        "DROP TABLE IF EXISTS products;",
        """CREATE TABLE products (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            price DECIMAL(10,2) NOT NULL,
            stock INT NOT NULL
        );""",
        "INSERT INTO products (name, price, stock) VALUES ('Wireless Mouse', 25.99, 50);",
        "INSERT INTO products (name, price, stock) VALUES ('Mechanical Keyboard', 89.99, 15);",
        "INSERT INTO products (name, price, stock) VALUES ('USB-C Cable 1m', 9.99, 100);",
        "INSERT INTO products (name, price, stock) VALUES ('HD Webcam', 49.99, 0);"
    ]

    # Order Service seeding queries
    order_statements = [
        "DROP TABLE IF EXISTS orders;",
        """CREATE TABLE orders (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            product_id INT NOT NULL,
            quantity INT NOT NULL,
            total_price DECIMAL(10,2) NOT NULL,
            status VARCHAR(50) DEFAULT 'PENDING'
        );""",
        "INSERT INTO orders (user_id, product_id, quantity, total_price, status) VALUES (1, 1, 2, 51.98, 'COMPLETED');",
        "INSERT INTO orders (user_id, product_id, quantity, total_price, status) VALUES (2, 2, 1, 89.99, 'COMPLETED');"
    ]

    # Execute seeding sequence
    seed_db("users_db", user_statements)
    seed_db("products_db", product_statements)
    seed_db("orders_db", order_statements)
    print("All MySQL databases initialized & seeded successfully!")

if __name__ == "__main__":
    main()
