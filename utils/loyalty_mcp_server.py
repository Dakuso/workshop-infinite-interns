import sqlite3
import os
from datetime import datetime
from mcp.server.fastmcp import FastMCP

# Initialize the MCP server
mcp = FastMCP("LoyaltyDB")

@mcp.tool()
def add_customer(name: str, address: str, loyalty_points: int = 0) -> str:
    """Add a customer to the loyalty database."""
    conn = sqlite3.connect("utils/loyalty.db")
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO customers (name, address, loyalty_points) VALUES (?, ?, ?)",
            (name, address, loyalty_points)
        )
        conn.commit()
        return f"Customer {name} added successfully."
    except sqlite3.IntegrityError:
        return f"Customer with name {name} already exists."
    finally:
        conn.close()

@mcp.tool()
def list_customers() -> str:
    """List all customers in the loyalty database."""
    conn = sqlite3.connect("utils/loyalty.db")
    cur = conn.cursor()
    cur.execute("SELECT name, address, loyalty_points FROM customers")
    rows = cur.fetchall()
    conn.close()

    if not rows:
        return "No customers found."

    result = ["Customers:"]
    for row in rows:
        name, address, loyalty_points = row
        result.append(f"{name}, Address: {address}, Loyalty Points: {loyalty_points}")
    
    return "\n".join(result)

@mcp.tool()
def increase_loyalty_points(name: str, points: int) -> str:
    """Increase loyalty points for a customer."""
    conn = sqlite3.connect("utils/loyalty.db")
    cur = conn.cursor()
    cur.execute("UPDATE customers SET loyalty_points = loyalty_points + ? WHERE name = ?", (points, name))
    if cur.rowcount == 0:
        return f"No customer found with name {name}."
    conn.commit()
    conn.close()
    return f"Loyalty points increased by {points} for customer {name}."

@mcp.tool()
def decrease_loyalty_points(name: str, points: int) -> str:
    """Decrease loyalty points for a customer."""
    conn = sqlite3.connect("utils/loyalty.db")
    cur = conn.cursor()
    cur.execute("UPDATE customers SET loyalty_points = loyalty_points - ? WHERE name = ?", (points, name))
    if cur.rowcount == 0:
        return f"No customer found with name {name}."
    conn.commit()
    conn.close()
    return f"Loyalty points decreased by {points} for customer {name}."

@mcp.tool()
def set_loyalty_points(name: str, points: int) -> str:
    """Set loyalty points for a customer."""
    conn = sqlite3.connect("utils/loyalty.db")
    cur = conn.cursor()
    cur.execute("UPDATE customers SET loyalty_points = ? WHERE name = ?", (points, name))
    if cur.rowcount == 0:
        return f"No customer found with name {name}."
    conn.commit()
    conn.close()
    return f"Loyalty points set to {points} for customer {name}."

@mcp.tool()
def get_loyalty_points(name: str) -> str:
    """Get the loyalty points for a customer."""
    conn = sqlite3.connect("utils/loyalty.db")
    cur = conn.cursor()
    cur.execute("SELECT loyalty_points FROM customers WHERE name = ?", (name,))
    row = cur.fetchone()
    conn.close()

    if row is None:
        return f"No customer found with name {name}."
    
    loyalty_points = row[0]
    return f"Customer {name} has {loyalty_points} loyalty points."

@mcp.tool()
def top_customers(limit: int = 5) -> str:
    """List the top customers by loyalty points."""
    conn = sqlite3.connect("utils/loyalty.db")
    cur = conn.cursor()
    cur.execute("SELECT name, address, loyalty_points FROM customers ORDER BY loyalty_points DESC LIMIT ?", (limit,))
    rows = cur.fetchall()
    conn.close()

    if not rows:
        return "No customers found."

    result = ["Top Customers:"]
    for row in rows:
        name, address, loyalty_points = row
        result.append(f"{name}, Address: {address}, Loyalty Points: {loyalty_points}")
    
    return "\n".join(result)

@mcp.tool()
def zero_loyalty_customers() -> str:
    """List of addresses of customers with zero loyalty points."""
    conn = sqlite3.connect("utils/loyalty.db")
    cur = conn.cursor()
    cur.execute("SELECT name FROM customers WHERE loyalty_points = 0")
    rows = cur.fetchall()
    conn.close()

    if not rows:
        return "No customers with zero loyalty points found."

    result = []
    for (name,) in rows:
        result.append(name)
    
    return "\n".join(result)

@mcp.tool()
def delete_customer(name: str) -> str:
    """Delete a customer from the loyalty database."""
    conn = sqlite3.connect("utils/loyalty.db")
    cur = conn.cursor()
    cur.execute("DELETE FROM customers WHERE name = ?", (name,))
    if cur.rowcount == 0:
        return f"No customer found with name {name}."
    conn.commit()
    conn.close()
    return f"Customer {name} deleted successfully."

if __name__ == "__main__":
    mcp.run(transport="stdio")