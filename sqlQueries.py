import os
import sqlite3
import bcrypt
from datetime import date
from typing import Any, Dict, List, Optional
from dataLoader import DB_PATH, init_db

def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = lambda cur, row: {
        col[0]: row[idx] for idx, col in enumerate(cur.description)
    } if cur.description else row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def get_restaurants() -> List[Dict]:
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM restaurants")
        return cur.fetchall()
    except sqlite3.Error as e:
        print(f"Error fetching restaurants: {e}")
        return []
    finally:
        if conn:
            conn.close()

def get_restaurant_by_id(rid: int) -> Optional[Dict]:
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM restaurants WHERE restaurant_id = ?", (rid,))
        return cur.fetchone()
    except sqlite3.Error as e:
        print(f"Error fetching restaurant by ID: {e}")
        return None
    finally:
        if conn:
            conn.close()

def get_menu_by_restaurant(rid: int) -> List[Dict]:
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT mi.item_id, mi.name, mi.description, mi.price, mi.avg_rating, mi.total_reviews, mc.name AS section 
            FROM menu_items mi 
            INNER JOIN menu_categories mc ON mi.menu_category_id = mc.menu_category_id
            WHERE mi.restaurant_id = ?
        """, 
        (rid,))
        return cur.fetchall()
    except sqlite3.Error as e:
        print(f"Error fetching menu items: {e}")
        return []
    finally:
        if conn:
            conn.close()