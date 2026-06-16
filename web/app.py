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

# home page currently will display all restaurants
@app.route('/')
def home():
    restaurants = db.get_restaurants()
    return render_template('home.html', restaurants=restaurants)

# for when user clicks on a specific restaurant
@app.route("/restaurant/<int:rid>")
def restaurant(rid):
    restaurant = db.get_restaurant_by_id(rid)
    menu = db.get_menu_by_restaurant(rid)
    reviews = db.get_reviews_for_restaurant(rid)

    menu_sections = {}
    for i in menu:
        sec = i.get("section") or "General"
        menu_sections.setdefault(sec, []).append(i)

    if not restaurant:
        flash("Restaurant not found.", "error")
        return redirect(url_for('home'))
    
    return render_template('restaurant.html', restaurant=restaurant, menu_sections=menu_sections, reviews=reviews)

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

@app.route("/logout")
def logout():
    session.pop("user", None)
    flash("Logged out.", "info")
    return redirect(url_for("home"))

if __name__ == '__main__':
    print("Running")
    app.run(debug=True, port=5000)