CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL,
    email TEXT NOT NULL,
    password_hash TEXT NOT NULL
);

-- 1 to many relation with categories
CREATE TABLE IF NOT EXISTS restaurants (
    restaurant_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    category_id INTEGER,
    price_range TEXT,
    full_address TEXT,
    city TEXT,
    state TEXT,
    latitude REAL,
    longitude REAL,
    avg_rating REAL DEFAULT 0.00,
    total_reviews INTEGER DEFAULT 0,
    FOREIGN KEY (category_id) REFERENCES categories(category_id)
);

-- many to 1 relation with restaurants
CREATE TABLE IF NOT EXISTS categories (
    category_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT
);

-- 1 to many with restaurants
CREATE TABLE IF NOT EXISTS menu_items (
    item_id INTEGER PRIMARY KEY AUTOINCREMENT,
    restaurant_id INTEGER NOT NULL,
    menu_category_id INTEGER,
    name TEXT NOT NULL,
    description TEXT,
    price REAL,
    avg_rating REAL DEFAULT 0.00,
    total_reviews INTEGER DEFAULT 0,
    FOREIGN KEY (restaurant_id) REFERENCES restaurants(restaurant_id),
    FOREIGN KEY (menu_category_id) REFERENCES menu_categories(menu_category_id)
);

-- many to 1 relation with restaurants
CREATE TABLE IF NOT EXISTS menu_categories (
    menu_category_id INTEGER PRIMARY KEY AUTOINCREMENT,
    restaurant_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    FOREIGN KEY (restaurant_id) REFERENCES restaurants(restaurant_id)
);

 -- many to 1 relation with users and restaurants | made it so that a user can only review a restaurant once
CREATE TABLE IF NOT EXISTS restaurant_reviews (
    review_id INTEGER PRIMARY KEY AUTOINCREMENT,
    restaurant_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    rating INTEGER NOT NULL CHECK(rating BETWEEN 1 AND 5),
    title TEXT,
    content TEXT,
    upvotes INTEGER DEFAULT 0,
    UNIQUE (user_id, restaurant_id),
    FOREIGN KEY (restaurant_id) REFERENCES restaurants(restaurant_id),
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- many to 1 relation with users and menu_items | made it so that a user can only review a menu item once
CREATE TABLE IF NOT EXISTS menu_item_reviews (
    review_id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    rating INTEGER NOT NULL CHECK(rating BETWEEN 1 AND 5),
    content TEXT,
    helpful_count INTEGER DEFAULT 0,
    UNIQUE (user_id, item_id),
    FOREIGN KEY (item_id)  REFERENCES menu_items(item_id),
    FOREIGN KEY (user_id)  REFERENCES users(user_id) ON DELETE CASCADE
);

INSERT OR IGNORE INTO categories (name, description) VALUES
('American',       'Classic American comfort food'),
('Pizza',          'Pizza and Italian-American cuisine'),
('Chinese',        'Traditional and modern Chinese dishes'),
('Mexican',        'Mexican and Tex-Mex cuisine'),
('Japanese',       'Japanese cuisine including sushi and ramen'),
('Indian',         'Indian cuisine with rich spices'),
('Mediterranean',  'Mediterranean and Middle Eastern cuisine'),
('Thai',           'Thai cuisine'),
('Burgers',        'Gourmet and classic burgers'),
('Seafood',        'Fresh seafood dishes'),
('Vegan',          'Plant-based options'),
('Desserts',       'Sweet treats and desserts'),
('Breakfast',      'Breakfast and brunch'),
('Sandwiches',     'Sandwiches and subs'),
('Korean',         'Korean cuisine');