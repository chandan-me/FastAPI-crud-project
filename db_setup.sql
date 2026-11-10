-- =============================================================================
-- Dhee Stores - Database Setup & Initial Seed Data
-- Run in MySQL: mysql -u root -p < db_setup.sql
-- =============================================================================

-- 1. USERS DATABASE & SEED DATA
CREATE DATABASE IF NOT EXISTS users_db;
USE users_db;

CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    role VARCHAR(50) NOT NULL DEFAULT 'customer',
    password VARCHAR(255) NULL,
    is_blocked TINYINT(1) NOT NULL DEFAULT 0,
    profile_image TEXT NULL,
    access_token TEXT NULL,
    token_expires_at DATETIME NULL,
    last_login DATETIME NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Default Users: password123 (bcrypt hash: $2b$12$Gr/.Ubn052MvytWfU8ByNu9swtSuOvhnCVDf6T2jtfd4ykYMg5u8O)
INSERT INTO users (id, name, email, role, password, is_blocked) VALUES
(1, 'Admin', 'admin@gmail.com', 'admin', '$2b$12$Gr/.Ubn052MvytWfU8ByNu9swtSuOvhnCVDf6T2jtfd4ykYMg5u8O', 0),
(2, 'Customer', 'customer@gmail.com', 'customer', '$2b$12$Gr/.Ubn052MvytWfU8ByNu9swtSuOvhnCVDf6T2jtfd4ykYMg5u8O', 0)
ON DUPLICATE KEY UPDATE name=VALUES(name), role=VALUES(role), password=VALUES(password), is_blocked=VALUES(is_blocked);

-- 2. PRODUCTS DATABASE & SEED DATA
CREATE DATABASE IF NOT EXISTS products_db;
USE products_db;

CREATE TABLE IF NOT EXISTS products (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    price DECIMAL(10, 2) NOT NULL,
    stock INT NOT NULL DEFAULT 0,
    image_url TEXT NULL,
    is_blocked TINYINT(1) NOT NULL DEFAULT 0
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

INSERT INTO products (id, name, price, stock, image_url) VALUES
(1, 'Smart Watch Series 5', 89.99, 25, 'https://images.unsplash.com/photo-1523275335684-37898b6baf30?auto=format&fit=crop&w=600&h=600&q=80'),
(2, 'Wireless Headphones', 59.99, 40, 'https://images.unsplash.com/photo-1505740420928-5e560c06d30e?auto=format&fit=crop&w=600&h=600&q=80'),
(3, 'Travel Backpack', 39.99, 30, 'https://images.unsplash.com/photo-1553062407-98eeb64c6a62?auto=format&fit=crop&w=600&h=600&q=80'),
(4, 'Running Shoes', 49.99, 20, 'https://images.unsplash.com/photo-1542291026-7eec264c27ff?auto=format&fit=crop&w=600&h=600&q=80'),
(5, 'Luxury Perfume', 29.99, 15, 'https://images.unsplash.com/photo-1523293182086-7651a899d37f?auto=format&fit=crop&w=600&h=600&q=80'),
(6, 'Mechanical Gaming Keyboard', 79.99, 18, 'https://images.unsplash.com/photo-1618384887929-16ec33fab9ef?auto=format&fit=crop&w=600&h=600&q=80'),
(7, 'Ergonomic Wireless Mouse', 24.99, 35, 'https://images.unsplash.com/photo-1527864550417-7fd91fc51a46?auto=format&fit=crop&w=600&h=600&q=80'),
(8, 'Pro Gaming Laptop', 1099.99, 10, 'https://images.unsplash.com/photo-1496181133206-80ce9b88a853?auto=format&fit=crop&w=600&h=600&q=80'),
(9, 'Studio Desk Microphone', 64.99, 18, 'https://images.unsplash.com/photo-1590658268037-6bf12165a8df?auto=format&fit=crop&w=600&h=600&q=80'),
(10, '4K Ultra HD Webcam', 49.99, 30, 'https://images.unsplash.com/photo-1588872657578-7efd1f1555ed?auto=format&fit=crop&w=600&h=600&q=80')
ON DUPLICATE KEY UPDATE name=VALUES(name), price=VALUES(price), stock=VALUES(stock), image_url=VALUES(image_url);

-- 3. ORDERS DATABASE
CREATE DATABASE IF NOT EXISTS orders_db;
USE orders_db;

CREATE TABLE IF NOT EXISTS orders (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    product_id INT NOT NULL,
    quantity INT NOT NULL,
    total_price DECIMAL(10, 2) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'COMPLETED',
    payment_method VARCHAR(50) NOT NULL DEFAULT 'COD',
    payment_id VARCHAR(100) NULL,
    order_group_id VARCHAR(100) NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
