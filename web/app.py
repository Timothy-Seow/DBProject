import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from flask import(Flask, render_template, request, redirect, url_for, session, flash)
from functools import wraps
import sqlQueries as db

app = Flask(__name__)

@app.route('/')
def home():
    restaurants = db.get_restaurants()
    return render_template('home.html', restaurants=restaurants)

@app.route("/restaurant/<int:rid>")
def restaurant(rid):
    restaurant = db.get_restaurant_by_id(rid)
    menu = db.get_menu_by_restaurant(rid)

    menu_sections = {}
    for i in menu:
        sec = i.get("section") or "General"
        menu_sections.setdefault(sec, []).append(i)

    if not restaurant:
        flash("Restaurant not found.", "error")
        return redirect(url_for('home'))
    return render_template('restaurant.html', restaurant=restaurant, menu_sections=menu_sections)

if __name__ == '__main__':
    print("Running")
    app.run(debug=True, port=5000)