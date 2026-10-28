"""Starter skeleton for the MAP project.

Implements only the common contract: /health, /version, / and /reset.
Add the routes required by your assigned theme in this file or in separate modules.
"""

import os
import time

from flask import Flask, jsonify, request

APP_NAME = "map-project"
APP_VERSION = "0.1.0"

STARTED_AT = time.monotonic()

app = Flask(__name__)


VALID_CATEGORIES = {"family", "friends", "work", "other"}
MAX_NAME_LENGTH = 50


def validate_contact(data: dict) -> str | None:
    """Validates contact fields according to specification rules.

    Returns an error message string if invalid, or None if valid.
    """
    if not isinstance(data, dict):
        return "Invalid payload, must be a JSON object"

    for field in ("name", "email", "phone", "category"):
        if field not in data:
            return f"Missing required field: '{field}'"

    name = data["name"]
    if not isinstance(name, str) or not (1 <= len(name.strip()) and len(name) <= MAX_NAME_LENGTH):
        return f"'name' must be a non-empty string with at most {MAX_NAME_LENGTH} characters"

    email = data["email"]
    if not isinstance(email, str) or email.count("@") != 1:
        return "'email' must be a string containing exactly one '@'"
    before_at, after_at = email.split("@", 1)
    if not before_at.strip() or "." not in after_at:
        return "'email' must have text before '@' and at least one '.' after"

    phone = data["phone"]
    if not isinstance(phone, str):
        return "'phone' must be a string of exactly 10 digits (optionally prefixed by '+')"
    digits = phone[1:] if phone.startswith("+") else phone
    if len(digits) != 10 or not digits.isdigit():
        return "'phone' must contain exactly 10 digits (optionally preceded by '+')"

    category = data["category"]
    if not isinstance(category, str) or category not in VALID_CATEGORIES:
        return f"'category' must be one of: {', '.join(sorted(VALID_CATEGORIES))}"

    return None


class Store:
    """Holds the application data in memory.

    Everything is lost when the container restarts.
    Add your theme's structures here.
    """

    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.next_id = 1
        self.contacts: dict[int, dict] = {}


store = Store()


@app.post("/contacts")
def create_contact():
    data = request.get_json(silent=True)
    if data is None:
        return jsonify(error="validation", message="Request body must be valid JSON"), 400

    error = validate_contact(data)
    if error:
        return jsonify(error="validation", message=error), 400

    email_to_check = data["email"].strip().lower()
    for existing in store.contacts.values():
        if existing["email"].strip().lower() == email_to_check:
            return jsonify(error="conflict", message="A contact with this email already exists"), 409

    contact_id = store.next_id
    store.next_id += 1

    contact = {
        "id": contact_id,
        "name": data["name"],
        "email": data["email"],
        "phone": data["phone"],
        "category": data["category"],
    }
    store.contacts[contact_id] = contact

    return jsonify(contact), 201


@app.get("/contacts")
def list_contacts():
    category_filter = request.args.get("category")
    query_filter = request.args.get("q")

    results = list(store.contacts.values())

    if category_filter:
        results = [c for c in results if c["category"] == category_filter]

    if query_filter:
        q_lower = query_filter.lower()
        results = [c for c in results if q_lower in c["name"].lower()]

    results.sort(key=lambda c: (c["name"], c["id"]))
    return jsonify(results), 200


@app.get("/health")
def health():
    return jsonify(
        status="ok",
        uptime_seconds=int(time.monotonic() - STARTED_AT),
    )


@app.get("/version")
def version():
    return jsonify(
        app=APP_NAME,
        version=APP_VERSION,
        commit=os.getenv("APP_COMMIT", "dev"),
        built_at=os.getenv("APP_BUILT_AT", "unknown"),
    )


@app.post("/reset")
def reset():
    store.reset()
    return "", 204


@app.get("/")
def home():
    commit = os.getenv("APP_COMMIT", "dev")
    return f"""<!DOCTYPE html>
<html lang="ro"><head><meta charset="utf-8"><title>{APP_NAME}</title></head>
<body>
<h1>{APP_NAME}</h1>
<p>Autor: Marian Vitalie, grupa 1.2</p>
<p>Tema: 1 - Agenda de contacte</p>
<p>Versiune: {APP_VERSION}, commit {commit}</p>
</body></html>"""


@app.errorhandler(404)
def not_found(_):
    return jsonify(error="not_found", message="route does not exist"), 404


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
