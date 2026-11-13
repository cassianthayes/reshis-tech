import csv
import math
import secrets
import sqlite3
from pathlib import Path

from flask import Flask, g, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
folder = Path(__file__).resolve().parent / "data"
key_file = folder.parent / ".secret_key"
if not key_file.exists():
    key_file.touch(mode=0o600)
    key_file.write_text(secrets.token_hex(32))
app.secret_key = key_file.read_text().strip()
app.config["DATABASE"] = folder.parent / "users.sqlite3"
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

with (folder / "routes.csv").open(encoding="utf-8") as f:
    routes = {row["route"]: row for row in csv.DictReader(f)}
with (folder / "my_forecast.csv").open(encoding="utf-8") as f:
    forecast = {(row["route"], row["date"]): row for row in csv.DictReader(f)}

dates = sorted({date for route, date in forecast})


def database():
    if "db" not in g:
        g.db = sqlite3.connect(app.config["DATABASE"])
        g.db.execute("CREATE TABLE IF NOT EXISTS users ("
                     "id INTEGER PRIMARY KEY, username TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL)")
    return g.db


@app.teardown_appcontext
def close_database(error):
    db = g.pop("db", None)
    if db is not None:
        db.close()


@app.route("/register", methods=["GET", "POST"])
@app.route("/login", methods=["GET", "POST"])
def login():
    registering = request.path == "/register"
    error = None
    username = request.form.get("username", "").strip()
    if request.method == "POST":
        password = request.form.get("password", "")
        db = database()
        if registering:
            if not username or not password:
                error = "Введите имя и пароль."
            else:
                try:
                    with db:
                        cursor = db.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)",
                                            (username, generate_password_hash(password)))
                    session.clear()
                    session["user_id"] = cursor.lastrowid
                    return redirect(url_for("index"))
                except sqlite3.IntegrityError:
                    error = "Это имя уже занято."
        else:
            user = db.execute("SELECT id, password_hash FROM users WHERE username = ?", (username,)).fetchone()
            if user and check_password_hash(user[1], password):
                session.clear()
                session["user_id"] = user[0]
                return redirect(url_for("index"))
            error = "Неверное имя или пароль."
    return render_template("login.html", registering=registering, username=username, error=error)


@app.post("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/", methods=["GET", "POST"])
def index():
    user = database().execute("SELECT username FROM users WHERE id = ?", (session.get("user_id"),)).fetchone()
    if not user:
        return redirect(url_for("login"))
    route = request.form.get("route", next(iter(routes)))
    date = request.form.get("date", dates[0])
    price = request.form.get("price", routes.get(route, {}).get("base_price", ""))
    result = None
    error = None

    if request.method == "POST":
        try:
            amount = float(price)
            if not math.isfinite(amount) or amount < 0:
                raise ValueError
            flight = forecast[route, date]
            params = routes[route]
            adjustment = float(params["price_sensitivity"]) * (amount - float(params["base_price"]))
            quantiles = [float(flight[f"{i / 10:.1f}_base_demand"]) - adjustment for i in range(1, 10)]
            demand = quantiles[4]
            seats = int(flight["seats"])
            result = {"demand": demand, "sales": min(seats, max(0, demand)),
                      "seats": seats, "quantiles": quantiles}
        except (ValueError, KeyError):
            error = "Проверьте маршрут, дату и цену. Цена должна быть числом не меньше нуля."

    return render_template("index.html", routes=routes, dates=dates, route=route,
                           date=date, price=price, result=result, error=error, username=user[0])


if __name__ == "__main__":
    app.run(port=8000)
