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
    cur.execute("SHOW COLUMNS FROM users LIKE 'role'")
    if not cur.fetchone():
        print("Adding 'role' column to users table...")
        cur.execute("ALTER TABLE users ADD COLUMN role VARCHAR(50) NOT NULL DEFAULT 'customer';")
        print("Added 'role' column.")
    else:
        print("'role' column already exists.")

    # Make alice an admin if exists
    cur.execute("UPDATE users SET role = 'admin' WHERE email = 'alice@example.com';")
    print(f"Updated alice@example.com to role 'admin'. Rows affected: {cur.rowcount}")

conn.close()
