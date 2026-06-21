import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from flask import(Flask, render_template, request, redirect, url_for, session, flash)
from functools import wraps
import sqlQueries as db

app = Flask(__name__)
app.secret_key = "randomkey"

# get user from session
def current_user():
    return session.get("user")

# for injecting user into every template so program knows if someone is logged in. runs by itself
@app.context_processor
def inject_user():
    return {"user": current_user()}


@app.route("/")
def home():
    top_restaurants = db.get_top_rated_restaurants(limit=5, min_reviews=1)
    categories = db.get_category_summary()
    return render_template("home.html", top_restaurants=top_restaurants, categories=categories)

# browse restaurants page - wil return list of restaurants based on search or filter
@app.route('/browse')
def browse():
    keyword = request.args.get("q", "").strip()
    category = request.args.get("category", None, type=int)
    price = request.args.get("price", "").strip()
    min_rating = request.args.get("min_rating", None, type=float)
    city = request.args.get("city", "").strip()

    results = db.search_restaurants(
        keyword = keyword or None,
        category_id = category,
        price_range = price or None,
        min_rating = min_rating,
        city = city or None,
    )
    categories = db.get_category_summary()

    query = dict(q=keyword, category=category, price=price, min_rating=min_rating, city=city)

    return render_template("browse.html", restaurants=results, categories=categories, query=query)

# for when user clicks on a specific restaurant
@app.route("/restaurant/<int:rid>")
def restaurant(rid):
    restaurant = db.get_restaurant_by_id(rid)
    if not restaurant:
        flash("Restaurant not found.", "error")
        return redirect(url_for('browse'))
    
    menu = db.get_menu_by_restaurant(rid)
    reviews = db.get_reviews_for_restaurant(rid)

    menu_sections = {}
    for i in menu:
        sec = i.get("section") or "General"
        menu_sections.setdefault(sec, []).append(i)

    user_item_reviews = {}
    is_fav = False
    if current_user():
        uid = current_user()["user_id"]
        user_item_reviews = db.get_user_item_reviews_for_restaurant(uid, rid)
        favs = db.get_user_favorites(uid)
        is_fav = any(f["restaurant_id"] == rid for f in favs)

    return render_template('restaurant.html', restaurant=restaurant, menu_sections=menu_sections, reviews=reviews, user_item_reviews=user_item_reviews, is_fav=is_fav)

# toggle save to favorite
@app.route("/restaurant/<int:rid>/favorite", methods=["POST"])
def toggle_favorite(rid):
    uid = current_user()["user_id"]
    action = request.form.get("action")
    if action == "add":
        db.add_favorite(uid, rid)
        flash("Added to favourites", "success")
    else:
        db.remove_favorite(uid, rid)
        flash("Removed from favourites.", "info")
    return redirect(url_for("restaurant", rid=rid))

# restaurant review route
@app.route("/restaurant/<int:rid>/review", methods=["POST"])
def submit_review(rid):
    rating  = request.form.get("rating",  type=int)
    title   = request.form.get("title",   "").strip()
    content = request.form.get("content", "").strip()

    if not rating or not 1 <= rating <= 5:
        flash("Please select a star rating.", "error")
        return redirect(url_for("restaurant", rid=rid))

    uid = current_user()["user_id"]
    ok  = db.create_restaurant_review(rid, uid, rating, title or None, content or None)
    if ok:
        flash("Review Submitted", "success")
    else:
        flash("Error Submitting", "error")
    return redirect(url_for("restaurant", rid=rid))

# editing a review
@app.route("/review/<int:rev_id>/edit", methods=["POST"])
def update_review(rev_id):
    rating = request.form.get("rating",  type=int)
    title = request.form.get("title",   "").strip()
    content = request.form.get("content", "").strip()
    rid = request.form.get("restaurant_id", type=int)
    uid = current_user()["user_id"]

    if not rating or not 1 <= rating <= 5:
        flash("Please select a star rating.", "error")
        return redirect(url_for("restaurant", rid=rid))

    ok = db.update_restaurant_review(rev_id, uid, rating=rating, title=title or None, content=content or None)
    if ok:
        flash("Review updated.", "success")
    else:
        flash("Could not update review.", "error")
    
    try:
        rid = request.form.get("restaurant_id", type=int)
        return redirect(url_for("restaurant", rid=rid))
    except:
        return redirect(url_for("profile"))

# menu item review route
@app.route("/menu-item/<int:iid>/review", methods=["POST"])
def submit_item_review(iid):
    rating = request.form.get("rating",  type=int)
    content = request.form.get("content", "").strip()
    rid  = request.form.get("restaurant_id", type=int)

    if not rating or not 1 <= rating <= 5:
        flash("Please select a rating.", "error")
        return redirect(url_for("restaurant", rid=rid))

    uid = current_user()["user_id"]
    ok  = db.create_menu_item_review(iid, uid, rating, content or None)
    if ok:
        flash("Review posted!", "success")
    else:
        flash("Could not submit review — you may already have reviewed this item.", "error")
    return redirect(url_for("restaurant", rid=rid))

# editing a review
@app.route("/item-review/<int:rev_id>/edit", methods=["POST"])
def update_item_review(rev_id):
    rating = request.form.get("rating",  type=int)
    content = request.form.get("content", "").strip()
    uid = current_user()["user_id"]

    if not rating or not 1 <= rating <= 5:
        flash("Please select a star rating.", "error")
        return redirect(url_for("restaurant", rid=rid))

    ok = db.update_menu_item_review(rev_id, uid, rating=rating, content=content or None)

    if ok:
        flash("Review updated.", "success")
    else:
        flash("Could not update review.", "error")
    
    try:
        rid = request.form.get("restaurant_id", type=int)
        return redirect(url_for("restaurant", rid=rid))
    except:
        return redirect(url_for("profile"))


# DELETE review
@app.route("/review/<int:rev_id>/<string:rev_type>/delete", methods=["POST"])
def delete_review(rev_id, rev_type):
    print(f"PLACEEEE: {rev_type}")
    uid = current_user()["user_id"]
    if rev_type == "res":
        db.delete_restaurant_review(rev_id, uid)
        flash("Review deleted.", "info")
        try:
            rid = request.form.get("restaurant_id", type=int)
            return redirect(url_for("restaurant", rid=rid))
        except:
            return redirect(url_for("profile"))
    elif rev_type == "men":
        db.delete_menu_item_review(rev_id, uid)
        flash("Review deleted.", "info")
        return redirect(url_for("profile"))
    else:
        rid = request.form.get("restaurant_id", type=int)
        db.delete_menu_item_review(rev_id, uid)
        flash("Review deleted.", "info")
        return redirect(url_for("restaurant", rid=rid))
    
# upvoting review
@app.route("/review/<int:rev_id>/vote", methods=["POST"])
def vote_review(rev_id):
    review_type = request.form.get("review_type", "restaurant")
    rid = request.form.get("restaurant_id", type=int)
    uid = current_user()["user_id"]
    db.vote_on_review(uid, rev_id, review_type)
    return redirect(url_for("restaurant", rid=rid))

# for the LOGIN / SIGNUP process
@app.route("/auth", methods=["GET", "POST"])
def auth():
    # redirect if logged in alr
    if current_user():
        return redirect(url_for("home"))
    
    tab = request.args.get("tab", "login")

    if request.method == "POST":
        action = request.form.get("action")

        if action == "login":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")
            user = db.authenticate_user(username, password)
            if user:
                session["user"] = user
                flash(f"Welcome back, {user['username']}", "success")
                return redirect(url_for("home"))
            flash("Invalid email or password.", "error")
            tab = "login"

        elif action == "register":
            username = request.form.get("username", "").strip()
            email = request.form.get("email", "").strip()
            password = request.form.get("password", "")

            if not username or not email or not password:
                flash("All fields are required.", "error")
                tab = "register"
            else:
                uid = db.create_user(username, email, password)
                if uid:
                    user = db.get_user(uid)
                    session["user"] = user
                    flash(f"Welcome, {username}. Your account has been created.", "success")
                    return redirect(url_for("home"))
                flash("Username or email is already taken.", "error")
                tab = "register"

    return render_template("auth.html", tab=tab)

@app.route("/profile")
def profile():
    uid = current_user()["user_id"]
    history = db.get_user_review_history(uid)
    favs = db.get_user_favorites(uid)
    return render_template("profile.html", history=history, favs=favs)

@app.route("/logout")
def logout():
    session.pop("user", None)
    flash("Logged out.", "info")
    return redirect(url_for("browse"))

if __name__ == '__main__':
    print("Running")
    app.run(debug=True, port=5000)