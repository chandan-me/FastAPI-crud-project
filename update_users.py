import os
import pymysql
from dotenv import load_dotenv

load_dotenv()

conn = pymysql.connect(
    host=os.getenv("MYSQL_HOST", "localhost"),
    port=int(os.getenv("MYSQL_PORT", 3306)),
    user=os.getenv("MYSQL_USER", "root"),
    password=os.getenv("MYSQL_PASSWORD", ""),
    database="users_db",
    autocommit=True
)

with conn.cursor() as cur:
    # Update Alice's email and role
    cur.execute("UPDATE users SET email = 'alice@gmail.com', role = 'admin' WHERE id = 1 OR email = 'alice@example.com';")
    cur.execute("UPDATE users SET email = 'bob@gmail.com', role = 'customer' WHERE id = 2 OR email = 'bob@example.com';")
    cur.execute("SELECT id, name, email, role FROM users;")
    rows = cur.fetchall()
    print("CURRENT USERS TABLE IN MYSQL:")
    for r in rows:
        print(f"  ID: {r[0]} | Name: {r[1]} | Email: {r[2]} | Role: {r[3]}")

conn.close()
