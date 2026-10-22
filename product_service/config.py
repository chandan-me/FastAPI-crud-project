import os
from urllib.parse import quote_plus
from dotenv import load_dotenv

# =====================================================================
# CONFIGURATION MODULE (Product Service)
# This module loads environment variables from a root-level .env file.
# By reading environment variables, we keep database credentials secure
# and outside of the source code.
# =====================================================================

# Load environment variables from the central '.env' file located in the parent directory
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

# Database Configuration Details (defaulting to local development settings)
MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_PORT = os.getenv("MYSQL_PORT", "3306")
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "products_db") # Each microservice targets its own schema

# URL-encode the password to prevent connection string parsing issues (e.g. if the password contains '@')
MYSQL_PASSWORD_ENCODED = quote_plus(MYSQL_PASSWORD)

# Build the complete SQLAlchemy connection URL for the PyMySQL driver
# Structure: mysql+pymysql://username:password@host:port/database_name
DATABASE_URL = f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD_ENCODED}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}"
