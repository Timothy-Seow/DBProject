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

# USER STUFF
def create_user(username: str, email: str, password: str) -> Optional[int]:
    try:
        pw_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        with get_connection() as conn:
            cur = conn.execute("""
                    INSERT INTO users (username, email, password_hash) 
                    VALUES (?, ?, ?)
                    """, 
                    (username, email, pw_hash),
            )
        return cur.lastrowid
    except sqlite3.IntegrityError:
        print("Error creating user: username or email already exists.")
        return None
    except sqlite3.Error as e:
        print(f"Error creating user: {e}")
        return None

def get_user(user_id: int) -> Optional[Dict]:
    try:
        with get_connection() as conn:
            cur = conn.execute("""
                SELECT user_id, username, email
                FROM users WHERE user_id = ?
                """,
                (user_id,),
            )
            return cur.fetchone()
    except sqlite3.Error as e:
        print(f"Error getting user by id: {e}")
        return None
    
def authenticate_user(name: str, password: str) -> Optional[Dict]:
    try:
        with get_connection() as conn:
            cur = conn.execute("""
                    SELECT user_id, username, email, password_hash
                    FROM users WHERE username = ?
                    """,
                    (name,),
                )
        user = cur.fetchone()
        if user and bcrypt.checkpw(password.encode(), user["password_hash"].encode()):
            user.pop("password_hash")
            return user
        return None
    except sqlite3.Error as e:
        print(f"Error authenticating user: {e}")
        return None

# RESTAURANT STUFF
def get_restaurants() -> List[Dict]:
    try:
        with get_connection() as conn:
            cur = conn.execute("SELECT * FROM restaurants")
        return cur.fetchall()
    except sqlite3.Error as e:
        print(f"Error fetching restaurants: {e}")
        return []
    finally:
        if conn:
            conn.close()

def get_restaurant_by_id(rid: int) -> Optional[Dict]:
    try:
        with get_connection() as conn:
            cur = conn.execute("SELECT * FROM restaurants WHERE restaurant_id = ?", (rid,))
        return cur.fetchone()
    except sqlite3.Error as e:
        print(f"Error fetching restaurant by ID: {e}")
        return None
    finally:
        if conn:
            conn.close()

def get_menu_by_restaurant(rid: int) -> List[Dict]:
    try:
        with get_connection() as conn:
            cur = conn.execute("""
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

def create_restaurant_review(restaurant_id: int, user_id: int, rating: int, title: str = None, content: str = None) -> Optional[int]:
    if not 1 <= rating <= 5:
        print("Error rating not selected")
        return None
    try:
        print(f"Restaurant ID: {restaurant_id}, User ID: {user_id}, Rating: {rating}, Title: {title}, Content: {content}")
        with get_connection() as conn:
            cur = conn.execute("""
                INSERT INTO restaurant_reviews (restaurant_id, user_id, rating, title, content)
                VALUES (?, ?, ?, ?, ?)
                """,
                (restaurant_id, user_id, rating, title, content),
            )
            return cur.lastrowid
    except sqlite3.IntegrityError:
        print("Error creating restaurant review: user already has a review in this restaurant")
        return None
    except sqlite3.Error as e:
        print(f"Error creating restaurant review: {e}")
        return None
    
def get_reviews_for_restaurant(restaurant_id: int) -> List[Dict]:
    try:
        with get_connection() as conn:
            cur = conn.execute("""
                SELECT r.review_id, r.rating, r.title, r.content, u.username, u.user_id
                FROM restaurant_reviews r
                JOIN users u ON r.user_id = u.user_id
                WHERE r.restaurant_id = ?
            """,
            (restaurant_id,),
        )
        return cur.fetchall()
    except sqlite3.Error as e:
        print(f"Error geting reviews for restaurant: {e}")
        return []
    
def create_menu_item_review(item_id: int, user_id: int, rating: int, content: str = None) -> Optional[int]:
    if not 1 <= rating <= 5:
        print("Error rating not selected")
        return None
    try:
        with get_connection() as conn:
            cur = conn.execute(
                "INSERT INTO menu_item_reviews (item_id, user_id, rating, content) "
                "VALUES (?, ?, ?, ?)",
                (item_id, user_id, rating, content),
            )
            return cur.lastrowid
    except sqlite3.IntegrityError:
        print("Error creating menu tem review: user already reviewed this item.")
        return None
    except sqlite3.Error as e:
        print(f"Error creating menu tem review {e}")
        return None

def get_reviews_for_menu_item(item_id: int) -> List[Dict]:
    try:
        with get_connection() as conn:
            cur = conn.execute("""
                SELECT r.review_id, r.rating, r.content, r.helpful_count, r.created_at, u.username, u.avatar_url
                FROM menu_item_reviews r
                JOIN users u ON r.user_id = u.user_id
                WHERE r.item_id = ?
                """,
                (item_id,),
            )
            return cur.fetchall()
    except sqlite3.Error as e:
        print(f"Error getting reviews for menu item: {e}")
        return []

# same as the above func, but for checking if the current user is the one who reviewed
def get_user_item_reviews_for_restaurant(user_id: int, restaurant_id: int) -> Dict[int, Dict]:
    try:
        with get_connection() as conn:
            cur = conn.execute("""
                SELECT mir.review_id, mir.item_id, mir.rating, mir.content
                FROM menu_item_reviews mir
                JOIN menu_items mi ON mir.item_id = mi.item_id
                WHERE mir.user_id = ? AND mi.restaurant_id = ?
                """,
                (user_id, restaurant_id),
            )
            return {row["item_id"]: row for row in cur.fetchall()}
    except sqlite3.Error as e:
        print(f"Error geting user item reviews for restaurant: {e}")
        return {}

# Advanced query lol. To get all reviews by a user across both restaurant and menu-item types. Uses UNION ALL to merge both tables.
def get_user_review_history(user_id: int) -> List[Dict]:
    try:
        with get_connection() as conn:
            cur = conn.execute("""
                SELECT 'restaurant' AS review_type, rr.review_id, r.name AS subject, rr.rating, rr.title, rr.content
                FROM restaurant_reviews rr
                JOIN restaurants r ON rr.restaurant_id = r.restaurant_id
                WHERE rr.user_id = ?
                UNION ALL
                SELECT 'menu_item' AS review_type, mir.review_id, mi.name AS subject, mir.rating, NULL AS title, mir.content
                FROM menu_item_reviews mir JOIN menu_items mi ON mir.item_id = mi.item_id
                WHERE mir.user_id = ? 
                """,
                (user_id, user_id),
            )
            return cur.fetchall()
    except sqlite3.Error as e:
        print(f"Error getting user review history: {e}")
        return []

def delete_restaurant_review(review_id: int, user_id: int) -> bool:
    try:
        with get_connection() as conn:
            cur = conn.execute("""
                DELETE FROM restaurant_reviews 
                WHERE review_id = ? AND user_id = ?
                """,
                (review_id, user_id),
            )
            return cur.rowcount > 0
    except sqlite3.Error as e:
        print(f"Error deleting restaurant review: {e}")
        return False
    
def update_restaurant_review(review_id: int, user_id: int, rating: int = None, title: str = None, content: str = None) -> bool:

    if rating is not None and not 1 <= rating <= 5:
        print("Error: Rating must be between 1 and 5.")
        return False
    try:
        with get_connection() as conn:
            cur = conn.execute("""
                UPDATE restaurant_reviews
                SET rating = COALESCE(?, rating), title = COALESCE(?, title), content = COALESCE(?, content)
                WHERE review_id = ? AND user_id = ?
                """,
                (rating, title, content, review_id, user_id),
            )
            return cur.rowcount > 0
    except sqlite3.Error as exc:
        print(f"[ERROR] update_restaurant_review: {exc}")
        return False
    
def delete_menu_item_review(review_id: int, user_id: int) -> bool:
    try:
        with get_connection() as conn:
            cur = conn.execute("""
                DELETE FROM menu_item_reviews
                WHERE review_id = ? AND user_id = ?
                """,
                (review_id, user_id),
             )  
            return cur.rowcount > 0
    except sqlite3.Error as e:
        print(f"Error deleting menu item review: {e}")
        return False

def update_menu_item_review(review_id: int, user_id: int, rating: int = None, content: str = None) -> bool:
    if rating is not None and not 1 <= rating <= 5:
        print("[ERROR] Rating must be between 1 and 5.")
        return False
    try:
        with get_connection() as conn:
            cur = conn.execute("""
                UPDATE menu_item_reviews
                SET rating = COALESCE(?, rating), content = COALESCE(?, content)
                WHERE review_id = ? AND user_id = ?
                """,
                (rating, content, review_id, user_id),
            )
            return cur.rowcount > 0
    except sqlite3.Error as e:
        print(f"Error updating menu item review: {e}")
        return False