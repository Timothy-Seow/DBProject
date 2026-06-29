"""
sqlQueries.py
-------------
All database access for the Folio app.
"""

import os
import sqlite3
import hashlib

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "food_review.db")


# ---------- connection ----------

def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _hash(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


# ================================================================
# USERS
# ================================================================

def create_user(username: str, email: str, password: str) -> int | None:
    try:
        with get_connection() as conn:
            cur = conn.execute(
                "INSERT INTO users (username, email, password_hash) VALUES (?,?,?)",
                (username, email, _hash(password))
            )
            return cur.lastrowid
    except sqlite3.IntegrityError:
        return None


def authenticate_user(username: str, password: str) -> dict | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT user_id, username, email FROM users WHERE username=? AND password_hash=?",
            (username, _hash(password))
        ).fetchone()
    return dict(row) if row else None


def get_user(user_id: int) -> dict | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT user_id, username, email FROM users WHERE user_id=?",
            (user_id,)
        ).fetchone()
    return dict(row) if row else None


def get_user_by_username(username: str) -> dict | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT user_id, username, email FROM users WHERE username=?",
            (username,)
        ).fetchone()
    return dict(row) if row else None


# ================================================================
# RESTAURANTS
# ================================================================

def get_top_rated_restaurants(limit: int = 5, min_reviews: int = 1) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT r.restaurant_id, r.name, r.avg_rating, r.total_reviews,
                   c.name AS category
            FROM restaurants r
            LEFT JOIN categories c ON c.category_id = r.category_id
            WHERE r.total_reviews >= ?
            ORDER BY r.avg_rating DESC, r.total_reviews DESC
            LIMIT ?
        """, (min_reviews, limit)).fetchall()
    return [dict(r) for r in rows]


def get_restaurant_by_id(rid: int) -> dict | None:
    with get_connection() as conn:
        row = conn.execute("""
            SELECT r.*, c.name AS category
            FROM restaurants r
            LEFT JOIN categories c ON c.category_id = r.category_id
            WHERE r.restaurant_id = ?
        """, (rid,)).fetchone()
    return dict(row) if row else None


def search_restaurants(
    keyword: str = None,
    category_id: int = None,
    price_range: str = None,
    min_rating: float = None,
    city: str = None,
) -> list[dict]:
    sql    = "SELECT r.*, c.name AS category FROM restaurants r LEFT JOIN categories c ON c.category_id = r.category_id WHERE 1=1"
    params = []
    if keyword:
        sql += " AND (r.name LIKE ? OR c.name LIKE ?)"
        params += [f"%{keyword}%", f"%{keyword}%"]
    if category_id:
        sql += " AND r.category_id = ?"
        params.append(category_id)
    if price_range:
        sql += " AND r.price_range = ?"
        params.append(price_range)
    if min_rating is not None:
        sql += " AND r.avg_rating >= ?"
        params.append(min_rating)
    if city:
        sql += " AND r.city LIKE ?"
        params.append(f"%{city}%")
    sql += " ORDER BY r.avg_rating DESC, r.name"
    with get_connection() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def get_restaurants_by_categories(category_ids: list[int], limit: int = 10) -> list[dict]:
    """Return restaurants matching any of the given category IDs (for personalised home page)."""
    if not category_ids:
        return []
    placeholders = ",".join("?" * len(category_ids))
    with get_connection() as conn:
        rows = conn.execute(f"""
            SELECT r.restaurant_id, r.name, r.avg_rating, r.total_reviews,
                   c.name AS category
            FROM restaurants r
            LEFT JOIN categories c ON c.category_id = r.category_id
            WHERE r.category_id IN ({placeholders})
            ORDER BY r.avg_rating DESC, r.total_reviews DESC
            LIMIT ?
        """, (*category_ids, limit)).fetchall()
    return [dict(r) for r in rows]


# ================================================================
# CATEGORIES
# ================================================================

def get_category_summary() -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT c.category_id, c.name AS category, COUNT(r.restaurant_id) AS restaurant_count
            FROM categories c
            LEFT JOIN restaurants r ON r.category_id = c.category_id
            GROUP BY c.category_id
            ORDER BY restaurant_count DESC
        """).fetchall()
    return [dict(r) for r in rows]


def get_all_categories() -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT category_id, name FROM categories GROUP BY name ORDER BY name"
        ).fetchall()
    return [dict(r) for r in rows]


# ================================================================
# MENU
# ================================================================

def get_menu_by_restaurant(rid: int) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT mi.item_id, mi.name, mi.description, mi.price,
                   mi.avg_rating, mi.total_reviews,
                   mc.name AS section
            FROM menu_items mi
            LEFT JOIN menu_categories mc ON mc.menu_category_id = mi.menu_category_id
            WHERE mi.restaurant_id = ?
            ORDER BY mc.name, mi.name
        """, (rid,)).fetchall()
    return [dict(r) for r in rows]


# ================================================================
# RESTAURANT REVIEWS
# ================================================================

def get_reviews_for_restaurant(rid: int) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT rr.review_id, rr.rating, rr.title, rr.content, rr.upvotes,
                   rr.user_id, u.username
            FROM restaurant_reviews rr
            JOIN users u ON u.user_id = rr.user_id
            WHERE rr.restaurant_id = ?
            ORDER BY rr.upvotes DESC, rr.review_id DESC
        """, (rid,)).fetchall()
    return [dict(r) for r in rows]


def create_restaurant_review(rid: int, uid: int, rating: int, title: str, content: str) -> bool:
    try:
        with get_connection() as conn:
            conn.execute(
                "INSERT INTO restaurant_reviews (restaurant_id, user_id, rating, title, content) VALUES (?,?,?,?,?)",
                (rid, uid, rating, title, content)
            )
        return True
    except sqlite3.IntegrityError:
        return False


def update_restaurant_review(rev_id: int, uid: int, rating: int, title: str, content: str) -> bool:
    try:
        with get_connection() as conn:
            conn.execute(
                "UPDATE restaurant_reviews SET rating=?, title=?, content=? WHERE review_id=? AND user_id=?",
                (rating, title, content, rev_id, uid)
            )
        return True
    except Exception:
        return False


def delete_restaurant_review(rev_id: int, uid: int) -> None:
    with get_connection() as conn:
        conn.execute(
            "DELETE FROM restaurant_reviews WHERE review_id=? AND user_id=?",
            (rev_id, uid)
        )


# ================================================================
# MENU ITEM REVIEWS
# ================================================================

def get_user_item_reviews_for_restaurant(uid: int, rid: int) -> dict:
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT mir.review_id, mir.item_id, mir.rating, mir.content, mir.upvotes
            FROM menu_item_reviews mir
            JOIN menu_items mi ON mi.item_id = mir.item_id
            WHERE mir.user_id = ? AND mi.restaurant_id = ?
        """, (uid, rid)).fetchall()
    return {r["item_id"]: dict(r) for r in rows}


def create_menu_item_review(iid: int, uid: int, rating: int, content: str) -> bool:
    try:
        with get_connection() as conn:
            conn.execute(
                "INSERT INTO menu_item_reviews (item_id, user_id, rating, content) VALUES (?,?,?,?)",
                (iid, uid, rating, content)
            )
        return True
    except sqlite3.IntegrityError:
        return False


def update_menu_item_review(rev_id: int, uid: int, rating: int, content: str) -> bool:
    try:
        with get_connection() as conn:
            conn.execute(
                "UPDATE menu_item_reviews SET rating=?, content=? WHERE review_id=? AND user_id=?",
                (rating, content, rev_id, uid)
            )
        return True
    except Exception:
        return False


def delete_menu_item_review(rev_id: int, uid: int) -> None:
    with get_connection() as conn:
        conn.execute(
            "DELETE FROM menu_item_reviews WHERE review_id=? AND user_id=?",
            (rev_id, uid)
        )


# ================================================================
# USER REVIEW HISTORY  (profile page)
# ================================================================

def get_user_review_history(uid: int) -> list[dict]:
    with get_connection() as conn:
        restaurant_reviews = conn.execute("""
            SELECT rr.review_id, 'restaurant' AS review_type,
                   r.name AS subject, rr.rating, rr.title, rr.content,
                   rr.restaurant_id
            FROM restaurant_reviews rr
            JOIN restaurants r ON r.restaurant_id = rr.restaurant_id
            WHERE rr.user_id = ?
        """, (uid,)).fetchall()

        item_reviews = conn.execute("""
            SELECT mir.review_id, 'menu_item' AS review_type,
                   mi.name AS subject, mir.rating, NULL AS title, mir.content,
                   mi.restaurant_id
            FROM menu_item_reviews mir
            JOIN menu_items mi ON mi.item_id = mir.item_id
            WHERE mir.user_id = ?
        """, (uid,)).fetchall()

    return [dict(r) for r in restaurant_reviews] + [dict(r) for r in item_reviews]


# ================================================================
# FAVORITES
# ================================================================

def get_user_favorites(uid: int) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT f.favorite_id, f.restaurant_id, r.name
            FROM favorites f
            JOIN restaurants r ON r.restaurant_id = f.restaurant_id
            WHERE f.user_id = ?
            ORDER BY r.name
        """, (uid,)).fetchall()
    return [dict(r) for r in rows]


def add_favorite(uid: int, rid: int) -> None:
    try:
        with get_connection() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO favorites (user_id, restaurant_id) VALUES (?,?)",
                (uid, rid)
            )
    except sqlite3.Error:
        pass


def remove_favorite(uid: int, rid: int) -> None:
    with get_connection() as conn:
        conn.execute(
            "DELETE FROM favorites WHERE user_id=? AND restaurant_id=?",
            (uid, rid)
        )


# ================================================================
# UPVOTES
# ================================================================

def vote_on_review(uid: int, rev_id: int, review_type: str) -> None:
    col   = "upvotes" if review_type == "restaurant" else "upvotes"
    table = "restaurant_reviews" if review_type == "restaurant" else "menu_item_reviews"
    id_col = "review_id"

    with get_connection() as conn:
        existing = conn.execute(
            "SELECT upvotes FROM upvotes WHERE user_id=? AND review_id=? AND review_type=?",
            (uid, rev_id, review_type)
        ).fetchone()

        if existing:
            new_val = 1 - existing["upvotes"]
            conn.execute(
                "UPDATE upvotes SET upvotes=? WHERE user_id=? AND review_id=? AND review_type=?",
                (new_val, uid, rev_id, review_type)
            )
            delta = 1 if new_val == 1 else -1
        else:
            conn.execute(
                "INSERT INTO upvotes (user_id, review_id, review_type, upvotes) VALUES (?,?,?,1)",
                (uid, rev_id, review_type)
            )
            delta = 1

        conn.execute(
            f"UPDATE {table} SET upvotes = upvotes + ? WHERE {id_col} = ?",
            (delta, rev_id)
        )


# ================================================================
# FOLLOWS  (new)
# ================================================================

def follow_user(follower_id: int, followee_id: int) -> bool:
    """follower_id starts following followee_id. Returns True on success."""
    if follower_id == followee_id:
        return False
    try:
        with get_connection() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO follows (follower_id, followee_id) VALUES (?,?)",
                (follower_id, followee_id)
            )
        return True
    except sqlite3.Error:
        return False


def unfollow_user(follower_id: int, followee_id: int) -> None:
    with get_connection() as conn:
        conn.execute(
            "DELETE FROM follows WHERE follower_id=? AND followee_id=?",
            (follower_id, followee_id)
        )


def is_following(follower_id: int, followee_id: int) -> bool:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT 1 FROM follows WHERE follower_id=? AND followee_id=?",
            (follower_id, followee_id)
        ).fetchone()
    return row is not None


def get_followers(user_id: int) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT u.user_id, u.username
            FROM follows f
            JOIN users u ON u.user_id = f.follower_id
            WHERE f.followee_id = ?
            ORDER BY u.username
        """, (user_id,)).fetchall()
    return [dict(r) for r in rows]


def get_following(user_id: int) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT u.user_id, u.username
            FROM follows f
            JOIN users u ON u.user_id = f.followee_id
            WHERE f.follower_id = ?
            ORDER BY u.username
        """, (user_id,)).fetchall()
    return [dict(r) for r in rows]


def get_follow_counts(user_id: int) -> dict:
    with get_connection() as conn:
        followers = conn.execute(
            "SELECT COUNT(*) FROM follows WHERE followee_id=?", (user_id,)
        ).fetchone()[0]
        following = conn.execute(
            "SELECT COUNT(*) FROM follows WHERE follower_id=?", (user_id,)
        ).fetchone()[0]
    return {"followers": followers, "following": following}


# ================================================================
# PUBLIC PROFILE
# ================================================================

def get_public_profile(username: str) -> dict | None:
    """All public-facing data for a user profile page."""
    with get_connection() as conn:
        user = conn.execute(
            "SELECT user_id, username FROM users WHERE username=?", (username,)
        ).fetchone()
        if not user:
            return None
        uid = user["user_id"]

        restaurant_reviews = conn.execute("""
            SELECT rr.review_id, 'restaurant' AS review_type,
                   r.name AS subject, r.restaurant_id,
                   rr.rating, rr.title, rr.content, rr.upvotes
            FROM restaurant_reviews rr
            JOIN restaurants r ON r.restaurant_id = rr.restaurant_id
            WHERE rr.user_id = ?
            ORDER BY rr.review_id DESC
        """, (uid,)).fetchall()

        item_reviews = conn.execute("""
            SELECT mir.review_id, 'menu_item' AS review_type,
                   mi.name AS subject, mi.restaurant_id,
                   mir.rating, NULL AS title, mir.content, mir.upvotes
            FROM menu_item_reviews mir
            JOIN menu_items mi ON mi.item_id = mir.item_id
            WHERE mir.user_id = ?
            ORDER BY mir.review_id DESC
        """, (uid,)).fetchall()

    reviews = [dict(r) for r in restaurant_reviews] + [dict(r) for r in item_reviews]
    avg = round(sum(r["rating"] for r in reviews) / len(reviews), 1) if reviews else None

    return {
        "user_id":  uid,
        "username": user["username"],
        "reviews":  reviews,
        "avg_rating": avg,
    }
