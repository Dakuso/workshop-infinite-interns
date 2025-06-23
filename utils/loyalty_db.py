import os
import sqlite3

# --- One-time DB setup ---
if not os.path.exists("utils/loyalty.db"):
    conn = sqlite3.connect("utils/loyalty.db")
    cur = conn.cursor()

    # Create a simple customers table: name, address, loyalty_points
    cur.execute("""
    CREATE TABLE IF NOT EXISTS customers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        address TEXT,
        loyalty_points INTEGER DEFAULT 0
    )
    """)

    # Sample customer entries
    cur.executemany(
        "INSERT INTO customers (name, address, loyalty_points) VALUES (?, ?, ?)",
        [
            ("Max Mustermann", "Musterstrasse 1, Musterstadt", 100),
            ("John Doe", "Doe Street 2, Example City", 150),
        ]
    )

    # Commit changes and close the connection
    conn.commit()
    conn.close()

# -------------------------