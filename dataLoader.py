import math
import os
import re
import pandas as pd
import sqlite3

RESTAURANT_LIMIT = 70
MENU_ITEM_LIMIT = 4900

# the actual cats from the dataset, buts mapped to ids
CATEGORY_MAP = {
    "american":      1,
    "pizza":         2,
    "chinese":       3,
    "mexican":       4,
    "japanese":      5,
    "indian":        6,
    "mediterranean": 7,
    "thai":          8,
    "burger":        9,
    "seafood":       10,
    "vegan":         11,
    "dessert":       12,
    "breakfast":     13,
    "sandwich":      14,
    "korean":        15,
    "others":        16,
}

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "food_review.db")

# --- helper funcs ---
def init_db():
    sql_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "createDB.sql")
    with open(sql_path, "r") as f:
        sql = f.read()
    conn = sqlite3.connect(DB_PATH) 
    conn.executescript(sql)
    conn.close()

def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode = WAL")   # allows concurrency
    return conn

def clean_string(s, max: int = None):
    if s is None:
        return None
    s = str(s).strip()
    return s[:max] if max else s

def clean_float(val):
    try:
        f = float(val)
        return None if math.isnan(f) else f
    except (TypeError, ValueError):
        return None

def get_cityState(address):
    if not address:
        return None, None
    parts = [part.strip() for part in address.split(",")]
    city  = parts[-3][:100] if len(parts) >= 2 else None
    state = None
    if len(parts) >= 1:
        num = parts[-2].strip().split()
        if num and re.match(r"^[A-Z]{2}$", num[0]): #check if the first part is a 2-letter state code
            state = num[0]
    return city, state

def map_category(raw: str):
    if not raw:
        return None
    lower = raw.lower()
    for keyword, cid in CATEGORY_MAP.items():
        if keyword in lower:
            return cid
    return 16

# ---------- Loading of restaurant data ----------
def load_restaurants(filePath) -> dict:
    if not os.path.exists(filePath):
        print(f"Cannot find {filePath}")
        return {}

    df = pd.read_csv(filePath, nrows=RESTAURANT_LIMIT, dtype=str)
    df.drop_duplicates(subset=["id"], keep="first", inplace=True)

    conn = get_connection()
    cur = conn.cursor()

    total = errors = 0
    resIDs= {}

    for _, row in df.iterrows():
        name = clean_string(row.get("name"), 255)
        if not name:
            continue

        catID = map_category(row.get("category"))
        price = clean_string(row.get("price_range"), 4)
        address = clean_string(row.get("full_address"))
        lat = clean_float(row.get("latitude"))
        lng = clean_float(row.get("longitude"))
        city, state  = get_cityState(address)
        print(f"category ID: {catID}")
        try:
            cur.execute("""
                INSERT OR IGNORE INTO restaurants (name, category_id, price_range, full_address, city, state, latitude, longitude)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (name, catID, price, address, city, state, lat, lng))

            #print(f"Inserted restaurant: {name} with ID: {cur.lastrowid}")
            if cur.lastrowid:
                resIDs[name.lower()] = cur.lastrowid
                total += 1
        except sqlite3.Error as e:
            errors += 1
            print(f"[DEBUG] DB Error: {e}")
            continue

    conn.commit()
    conn.close()
    print(f"Total inserted: {total:,}")
    print(f"Total errors: {errors:,}")
    return resIDs

# ---------- Loading of menu data ----------
def load_menu_items(menuFilePath, resFilePath, nameToId):
    if not os.path.exists(menuFilePath):
        print(f"File:{menuFilePath} not found")
        return

    menus_df = pd.read_csv(menuFilePath, nrows=MENU_ITEM_LIMIT, dtype=str)

    idToName = {}
    rest_df = pd.read_csv(resFilePath, dtype=str)
    for _, row in rest_df.iterrows():
        id  = clean_string(row.get("id"))
        name = clean_string(row.get("name"))
        if id and name:
            idToName[id] = name.lower()

    conn = get_connection()
    cur  = conn.cursor()

    categoryID = {}
    def get_category_id(rid, catName) -> int:
        key = (rid, catName)
        if key in categoryID:
            return categoryID[key]
        id = cur.execute("SELECT menu_category_id FROM menu_categories WHERE restaurant_id = ? AND name = ?", (rid, catName)).fetchone()
        if id:
            categoryID[key] = id[0]
        else:
            cur.execute("INSERT INTO menu_categories (restaurant_id, name) VALUES (?,?)",(rid, catName))
            id = cur.lastrowid
        categoryID[key] = id
        return id

    total = errors = 0
    for _, row in menus_df.iterrows():
        resID = clean_string(row.get("restaurant_id"))
        resName = idToName.get(resID)
        currentResID = nameToId.get(resName)

        itemName = clean_string(row.get("name"), 255)
        category = clean_string(row.get("category"), 100) or 'General'
        desc = clean_string(row.get("description"))
        price = clean_float(row.get("price"))

        try:
            catID = get_category_id(currentResID, category)
            cur.execute("""
                INSERT INTO menu_items (restaurant_id, menu_category_id, name, description, price)
                VALUES (?, ?, ?, ?, ?)
            """, (currentResID, catID, itemName, desc, price))
            total += 1
            #print(f"Inserted menu item: {itemName}, menu ID: {cur.lastrowid} for restaurant ID: {currentResID}")
        except sqlite3.Error as e:
            print(f"[DEBUG] DB Error: {e}")
            errors += 1
            continue
    
    conn.commit()
    conn.close()
    print(f"Total menu items inserted: {total:,}")
    print(f"Total menu item errors: {errors:,}")

if __name__ == "__main__":
    print("Loading data")

    init_db()

    # load restaurants
    resIDs = load_restaurants("dataset/restaurants.csv")

    # load menu items
    load_menu_items("dataset/restaurant-menus.csv", "dataset/restaurants.csv", resIDs)

    print("\nDONE")
   
