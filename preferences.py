"""
preferences.py
--------------
NoSQL-style JSON store for user cuisine preferences.
All reads/writes go through this module; the backing file is
web/data/user_preferences.json.
"""

import json
import os
from typing import Optional

_PREF_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "user_preferences.json")


# ---------- low-level helpers ----------

def _load() -> dict:
    if not os.path.exists(_PREF_PATH):
        return {"_schema": {}, "users": {}}
    with open(_PREF_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _save(data: dict) -> None:
    os.makedirs(os.path.dirname(_PREF_PATH), exist_ok=True)
    with open(_PREF_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


# ---------- public API ----------

def get_preferences(user_id: int) -> dict:
    """Return the preference object for a user, or sensible defaults."""
    data = _load()
    key  = str(user_id)
    return data["users"].get(key, {
        "cuisine_preferences": [],
        "price_range":         None,
        "show_personalized":   True,
    })


def set_cuisine_preferences(user_id: int, category_ids: list[int]) -> None:
    """Overwrite the user's cuisine preference list."""
    data = _load()
    key  = str(user_id)
    prefs = data["users"].setdefault(key, {
        "cuisine_preferences": [],
        "price_range":         None,
        "show_personalized":   True,
    })
    prefs["cuisine_preferences"] = [int(c) for c in category_ids]
    _save(data)


def set_price_range(user_id: int, price_range: Optional[str]) -> None:
    """Overwrite the user's preferred price range (e.g. '$', '$$', '$$$', '$$$$')."""
    data = _load()
    key  = str(user_id)
    prefs = data["users"].setdefault(key, {
        "cuisine_preferences": [],
        "price_range":         None,
        "show_personalized":   True,
    })
    prefs["price_range"] = price_range or None
    _save(data)


def toggle_personalized(user_id: int) -> bool:
    """Toggle the show_personalized flag and return the new value."""
    data  = _load()
    key   = str(user_id)
    prefs = data["users"].setdefault(key, {
        "cuisine_preferences": [],
        "price_range":         None,
        "show_personalized":   True,
    })
    prefs["show_personalized"] = not prefs.get("show_personalized", True)
    _save(data)
    return prefs["show_personalized"]
