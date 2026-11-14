"""
database.py - Database Connection and Query Utilities
Smart Chatbot for Restaurant Order Automation
"""

import sqlite3
import os
from contextlib import contextmanager

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'restaurant.db')

def get_db_connection(db_file=None):
    """
    Creates and returns a SQLite database connection with row factory enabled
    and foreign key constraints enforced.
    """
    target_db = db_file or DB_PATH
    conn = sqlite3.connect(target_db, timeout=10.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

@contextmanager
def db_session(db_file=None):
    """Context manager for safe database transactions with auto-commit/rollback."""
    conn = get_db_connection(db_file)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def query_db(query, args=(), one=False, db_file=None):
    """
    Executes a SELECT query safely with parameters and returns dictionary rows.
    """
    with db_session(db_file) as conn:
        cursor = conn.cursor()
        cursor.execute(query, args)
        rows = cursor.fetchall()
        cursor.close()
        if not rows:
            return None if one else []
        results = [dict(row) for row in rows]
        return results[0] if one else results

def execute_db(query, args=(), db_file=None):
    """
    Executes an INSERT, UPDATE, or DELETE query safely using parameterized SQL.
    Returns rowcount.
    """
    with db_session(db_file) as conn:
        cursor = conn.cursor()
        cursor.execute(query, args)
        rowcount = cursor.rowcount
        cursor.close()
        return rowcount

def execute_insert(query, args=(), db_file=None):
    """
    Executes an INSERT query safely and returns the last inserted row ID.
    """
    with db_session(db_file) as conn:
        cursor = conn.cursor()
        cursor.execute(query, args)
        last_id = cursor.lastrowid
        cursor.close()
        return last_id

SCHEMA_SQL = """
-- Categories Table
CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    slug TEXT NOT NULL UNIQUE,
    description TEXT,
    display_order INTEGER DEFAULT 0
);

-- Menu Items Table
CREATE TABLE IF NOT EXISTS menu_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category_id INTEGER NOT NULL,
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    price REAL NOT NULL CHECK(price >= 0),
    is_veg INTEGER NOT NULL DEFAULT 1 CHECK(is_veg IN (0, 1)),
    is_available INTEGER NOT NULL DEFAULT 1 CHECK(is_available IN (0, 1)),
    image_url TEXT,
    rating REAL DEFAULT 4.5 CHECK(rating >= 0 AND rating <= 5),
    popularity_score INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (category_id) REFERENCES categories (id) ON DELETE CASCADE
);

-- Admin Users Table
CREATE TABLE IF NOT EXISTS admin_users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT DEFAULT 'admin',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Customers/Users Table
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    phone TEXT NOT NULL,
    email TEXT,
    address TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Orders Table
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_code TEXT NOT NULL UNIQUE,
    user_name TEXT NOT NULL,
    user_phone TEXT NOT NULL,
    user_address TEXT NOT NULL,
    subtotal REAL NOT NULL CHECK(subtotal >= 0),
    tax_amount REAL NOT NULL CHECK(tax_amount >= 0),
    total_amount REAL NOT NULL CHECK(total_amount >= 0),
    status TEXT NOT NULL DEFAULT 'Pending' CHECK(status IN ('Pending', 'Confirmed', 'Preparing', 'Ready', 'Out for Delivery', 'Delivered', 'Cancelled')),
    payment_method TEXT NOT NULL DEFAULT 'Cash on Delivery',
    special_instructions TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Order Items Table (Historical Snapshot)
CREATE TABLE IF NOT EXISTS order_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL,
    menu_item_id INTEGER,
    item_name TEXT NOT NULL,
    item_price REAL NOT NULL CHECK(item_price >= 0),
    quantity INTEGER NOT NULL CHECK(quantity > 0),
    subtotal REAL NOT NULL CHECK(subtotal >= 0),
    FOREIGN KEY (order_id) REFERENCES orders (id) ON DELETE CASCADE,
    FOREIGN KEY (menu_item_id) REFERENCES menu_items (id) ON DELETE SET NULL
);

-- Bot Intent Training Data Table
CREATE TABLE IF NOT EXISTS bot_intent_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    intent TEXT NOT NULL,
    user_phrase TEXT NOT NULL
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_menu_category ON menu_items(category_id);
CREATE INDEX IF NOT EXISTS idx_menu_available ON menu_items(is_available);
CREATE INDEX IF NOT EXISTS idx_orders_code ON orders(order_code);
CREATE INDEX IF NOT EXISTS idx_orders_phone ON orders(user_phone);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
"""

def init_schema(db_file=None):
    """Initializes the database schema."""
    with db_session(db_file) as conn:
        conn.executescript(SCHEMA_SQL)
