import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from flask import (Flask, render_template, request, redirect, url_for, session, flash, jsonify)
from functools import wraps
import sqlQueries as db
import preferences as prefs

app = Flask(__name__)
app.secret_key = "randomkey"


# ---------- helpers ----------

def current_user():
    return session.get("user")

@app.context_processor
def inject_user():
    return {"user": current_user()}

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user():
            flash("Please sign in first.", "error")
            return redirect(url_for("auth"))
        return f(*args, **kwargs)
    return decorated


# ================================================================
# HOME
# ================================================================

@app.route("/")
def home():
    top_restaurants  = db.get_top_rated_restaurants(limit=5, min_reviews=1)
    categories       = db.get_category_summary()

    personalised     = []
    user_prefs       = {}
    following_feed   = []
    if current_user():
        uid        = current_user()["user_id"]
        user_prefs = prefs.get_preferences(uid)
        if user_prefs.get("show_personalized") and user_prefs.get("cuisine_preferences"):
            personalised = db.get_restaurants_by_categories(
                user_prefs["cuisine_preferences"], limit=6
            )
        following_feed = db.get_following_feed(uid, limit=20)

    return render_template(
        "home.html",
        top_restaurants=top_restaurants,
        categories=categories,
        personalised=personalised,
        user_prefs=user_prefs,
        following_feed=following_feed,
    )


# ================================================================
# BROWSE
# ================================================================

@app.route('/browse')
def browse():
    keyword    = request.args.get("q", "").strip()
    category   = request.args.get("category", None, type=int)
    price      = request.args.get("price", "").strip()
    min_rating = request.args.get("min_rating", None, type=float)
    city       = request.args.get("city", "").strip()

    results    = db.search_restaurants(
        keyword=keyword or None,
        category_id=category,
        price_range=price or None,
        min_rating=min_rating,
        city=city or None,
    )
    categories = db.get_category_summary()
    query      = dict(q=keyword, category=category, price=price, min_rating=min_rating, city=city)

    return render_template("browse.html", restaurants=results, categories=categories, query=query)


# ================================================================
# RESTAURANT
# ================================================================

@app.route("/restaurant/<int:rid>")
def restaurant(rid):
    restaurant = db.get_restaurant_by_id(rid)
    if not restaurant:
        flash("Restaurant not found.", "error")
        return redirect(url_for('browse'))

    menu     = db.get_menu_by_restaurant(rid)
    reviews  = db.get_reviews_for_restaurant(rid)

    menu_sections = {}
    for i in menu:
        sec = i.get("section") or "General"
        menu_sections.setdefault(sec, []).append(i)

    user_item_reviews = {}
    is_fav = False
    if current_user():
        uid = current_user()["user_id"]
        user_item_reviews = db.get_user_item_reviews_for_restaurant(uid, rid)
        favs   = db.get_user_favorites(uid)
        is_fav = any(f["restaurant_id"] == rid for f in favs)

    return render_template(
        'restaurant.html',
        restaurant=restaurant,
        menu_sections=menu_sections,
        reviews=reviews,
        user_item_reviews=user_item_reviews,
        is_fav=is_fav,
    )


@app.route("/restaurant/<int:rid>/favorite", methods=["POST"])
@login_required
def toggle_favorite(rid):
    uid    = current_user()["user_id"]
    action = request.form.get("action")
    if action == "add":
        db.add_favorite(uid, rid)
        flash("Added to favourites", "success")
    else:
        db.remove_favorite(uid, rid)
        flash("Removed from favourites.", "info")
    return redirect(url_for("restaurant", rid=rid))


@app.route("/restaurant/<int:rid>/review", methods=["POST"])
@login_required
def submit_review(rid):
    rating  = request.form.get("rating", type=int)
    title   = request.form.get("title", "").strip()
    content = request.form.get("content", "").strip()

    if not rating or not 1 <= rating <= 5:
        flash("Please select a star rating.", "error")
        return redirect(url_for("restaurant", rid=rid))

    uid = current_user()["user_id"]
    ok  = db.create_restaurant_review(rid, uid, rating, title or None, content or None)
    flash("Review submitted!" if ok else "You've already reviewed this restaurant.", "success" if ok else "error")
    return redirect(url_for("restaurant", rid=rid))


@app.route("/review/<int:rev_id>/edit", methods=["POST"])
@login_required
def update_review(rev_id):
    rating  = request.form.get("rating", type=int)
    title   = request.form.get("title", "").strip()
    content = request.form.get("content", "").strip()
    rid     = request.form.get("restaurant_id", type=int)
    uid     = current_user()["user_id"]

    if not rating or not 1 <= rating <= 5:
        flash("Please select a star rating.", "error")
        return redirect(url_for("restaurant", rid=rid))

    ok = db.update_restaurant_review(rev_id, uid, rating=rating, title=title or None, content=content or None)
    flash("Review updated." if ok else "Could not update review.", "success" if ok else "error")
    return redirect(url_for("restaurant", rid=rid) if rid else url_for("profile"))


@app.route("/menu-item/<int:iid>/review", methods=["POST"])
@login_required
def submit_item_review(iid):
    rating  = request.form.get("rating", type=int)
    content = request.form.get("content", "").strip()
    rid     = request.form.get("restaurant_id", type=int)

    if not rating or not 1 <= rating <= 5:
        flash("Please select a rating.", "error")
        return redirect(url_for("restaurant", rid=rid))

    uid = current_user()["user_id"]
    ok  = db.create_menu_item_review(iid, uid, rating, content or None)
    flash("Review posted!" if ok else "You've already reviewed this item.", "success" if ok else "error")
    return redirect(url_for("restaurant", rid=rid))


@app.route("/item-review/<int:rev_id>/edit", methods=["POST"])
@login_required
def update_item_review(rev_id):
    rating  = request.form.get("rating", type=int)
    content = request.form.get("content", "").strip()
    rid     = request.form.get("restaurant_id", type=int)
    uid     = current_user()["user_id"]

    if not rating or not 1 <= rating <= 5:
        flash("Please select a star rating.", "error")
        return redirect(url_for("restaurant", rid=rid))

    ok = db.update_menu_item_review(rev_id, uid, rating=rating, content=content or None)
    flash("Review updated." if ok else "Could not update review.", "success" if ok else "error")
    return redirect(url_for("restaurant", rid=rid) if rid else url_for("profile"))


@app.route("/review/<int:rev_id>/<string:rev_type>/delete", methods=["POST"])
@login_required
def delete_review(rev_id, rev_type):
    uid = current_user()["user_id"]
    rid = request.form.get("restaurant_id", type=int)

    if rev_type == "res":
        db.delete_restaurant_review(rev_id, uid)
        flash("Review deleted.", "info")
        return redirect(url_for("restaurant", rid=rid) if rid else url_for("profile"))
    else:
        db.delete_menu_item_review(rev_id, uid)
        flash("Review deleted.", "info")
        return redirect(url_for("restaurant", rid=rid) if rid else url_for("profile"))


@app.route("/review/<int:rev_id>/vote", methods=["POST"])
@login_required
def vote_review(rev_id):
    review_type = request.form.get("review_type", "restaurant")
    rid         = request.form.get("restaurant_id", type=int)
    uid         = current_user()["user_id"]
    db.vote_on_review(uid, rev_id, review_type)
    return redirect(url_for("restaurant", rid=rid))


# ================================================================
# AUTH
# ================================================================

@app.route("/auth", methods=["GET", "POST"])
def auth():
    if current_user():
        return redirect(url_for("home"))

    tab = request.args.get("tab", "login")

    if request.method == "POST":
        action = request.form.get("action")

        if action == "login":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")
            user     = db.authenticate_user(username, password)
            if user:
                session["user"] = user
                flash(f"Welcome back, {user['username']}!", "success")
                return redirect(url_for("home"))
            flash("Invalid username or password.", "error")
            tab = "login"

        elif action == "register":
            username = request.form.get("username", "").strip()
            email    = request.form.get("email", "").strip()
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


# ================================================================
# PROFILE (own)
# ================================================================

@app.route("/profile")
@login_required
def profile():
    uid      = current_user()["user_id"]
    history  = db.get_user_review_history(uid)
    favs     = db.get_user_favorites(uid)
    follow_counts = db.get_follow_counts(uid)
    following = db.get_following(uid)
    followers = db.get_followers(uid)
    user_prefs = prefs.get_preferences(uid)
    all_cats   = db.get_all_categories()
    return render_template(
        "profile.html",
        history=history,
        favs=favs,
        counts=follow_counts,
        following=following,
        followers=followers,
        user_prefs=user_prefs,
        all_cats=all_cats,
    )


# ================================================================
# PUBLIC PROFILE
# ================================================================

@app.route("/user/<username>")
def public_profile(username):
    # redirect own profile to /profile
    if current_user() and current_user()["username"] == username:
        return redirect(url_for("profile"))

    profile_data = db.get_public_profile(username)
    if not profile_data:
        flash("User not found.", "error")
        return redirect(url_for("home"))

    is_following = False
    follow_counts = db.get_follow_counts(profile_data["user_id"])
    followers = db.get_followers(profile_data["user_id"])
    following = db.get_following(profile_data["user_id"])
    if current_user():
        is_following = db.is_following(current_user()["user_id"], profile_data["user_id"])

    return render_template(
        "public_profile.html",
        profile=profile_data,
        is_following=is_following,
        counts=follow_counts,
        followers=followers,
        following=following,
    )


# ================================================================
# FOLLOW / UNFOLLOW
# ================================================================

@app.route("/user/<username>/follow", methods=["POST"])
@login_required
def follow(username):
    target = db.get_user_by_username(username)
    if not target:
        flash("User not found.", "error")
        return redirect(url_for("home"))
    db.follow_user(current_user()["user_id"], target["user_id"])
    flash(f"You are now following {username}.", "success")
    return redirect(url_for("public_profile", username=username))


@app.route("/user/<username>/unfollow", methods=["POST"])
@login_required
def unfollow(username):
    target = db.get_user_by_username(username)
    if not target:
        flash("User not found.", "error")
        return redirect(url_for("home"))
    db.unfollow_user(current_user()["user_id"], target["user_id"])
    flash(f"You unfollowed {username}.", "info")
    return redirect(url_for("public_profile", username=username))


# ================================================================
# PREFERENCES (cuisine)
# ================================================================

@app.route("/preferences/cuisines", methods=["POST"])
@login_required
def save_cuisine_preferences():
    uid      = current_user()["user_id"]
    selected = request.form.getlist("cuisine_preferences", type=int)
    prefs.set_cuisine_preferences(uid, selected)
    flash("Cuisine preferences saved!", "success")
    return redirect(url_for("profile"))


@app.route("/preferences/toggle-personalised", methods=["POST"])
@login_required
def toggle_personalised():
    uid     = current_user()["user_id"]
    new_val = prefs.toggle_personalized(uid)
    flash("Personalised feed " + ("enabled." if new_val else "disabled."), "info")
    return redirect(url_for("home"))


# ================================================================
# LOGOUT
# ================================================================

@app.route("/logout")
def logout():
    session.pop("user", None)
    flash("Logged out.", "info")
    return redirect(url_for("browse"))


if __name__ == '__main__':
    print("Running on http://localhost:5000")
    app.run(debug=True, port=5000)
