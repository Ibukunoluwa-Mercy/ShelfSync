import sqlite3
from pathlib import Path

from flask import current_app, g


DATABASE_PATH = Path(__file__).with_name("inventory.db")


def get_db():
    """Return the request's SQLite connection, creating it when needed."""
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(error=None):
    """Close the request's database connection, if one was opened."""
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    """Create the application tables, safe column migrations, and seed data."""
    db = get_db()
    user_columns = {
        row["name"] for row in db.execute("PRAGMA table_info(users)").fetchall()
    }
    if "username" in user_columns:
        user_count = db.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        if user_count:
            raise RuntimeError(
                "The existing users table still uses username columns and contains "
                "data. Back it up and migrate it before starting ShelfSync."
            )
        db.execute("DROP TABLE users")
        db.commit()

    # Safely migrate users table columns without modifying existing rows
    if "last_login_at" not in user_columns:
        db.execute("ALTER TABLE users ADD COLUMN last_login_at TEXT")
    if "session_version" not in user_columns:
        db.execute("ALTER TABLE users ADD COLUMN session_version INTEGER NOT NULL DEFAULT 0")

    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name       TEXT NOT NULL,
            email           TEXT NOT NULL UNIQUE COLLATE NOCASE,
            password_hash   TEXT NOT NULL,
            role            TEXT NOT NULL DEFAULT 'staff' CHECK (role IN ('admin', 'staff')),
            created_at      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            last_login_at   TEXT,
            session_version INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS login_attempts (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            email        TEXT NOT NULL,
            ip_address   TEXT NOT NULL,
            success      INTEGER NOT NULL DEFAULT 0,
            attempted_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_login_attempts_lookup
            ON login_attempts (email, ip_address, attempted_at);

        CREATE TABLE IF NOT EXISTS password_resets (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id      INTEGER NOT NULL,
            token_hash   TEXT NOT NULL UNIQUE,
            created_at   TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            expires_at   TEXT NOT NULL,
            used_at      TEXT,
            requested_ip TEXT,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_password_resets_user
            ON password_resets (user_id);

        CREATE TABLE IF NOT EXISTS password_reset_requests (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            email        TEXT NOT NULL,
            ip_address   TEXT NOT NULL,
            requested_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_reset_requests_lookup
            ON password_reset_requests (email, ip_address, requested_at);

        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        );

        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_name TEXT NOT NULL,
            product_code TEXT NOT NULL UNIQUE,
            category_id INTEGER NOT NULL,
            buying_price REAL NOT NULL,
            selling_price REAL NOT NULL,
            quantity INTEGER NOT NULL DEFAULT 0,
            minimum_stock INTEGER NOT NULL DEFAULT 0,
            date_added TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (category_id) REFERENCES categories (id)
        );

        CREATE TABLE IF NOT EXISTS stock_movements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            movement_type TEXT NOT NULL CHECK (movement_type IN ('in', 'out')),
            quantity INTEGER NOT NULL,
            reason TEXT NOT NULL,
            user_id INTEGER NOT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (product_id) REFERENCES products (id),
            FOREIGN KEY (user_id) REFERENCES users (id)
        );

        CREATE TABLE IF NOT EXISTS sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            total_amount REAL NOT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        );

        CREATE TABLE IF NOT EXISTS sale_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sale_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            price_at_sale REAL NOT NULL,
            FOREIGN KEY (sale_id) REFERENCES sales (id),
            FOREIGN KEY (product_id) REFERENCES products (id)
        );
        """
    )
    if db.execute("SELECT COUNT(*) FROM categories").fetchone()[0] == 0:
        db.executemany(
            "INSERT INTO categories (name) VALUES (?)",
            [("Food",), ("Drinks",), ("Toiletries",)],
        )
    db.commit()
