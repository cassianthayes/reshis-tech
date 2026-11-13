import csv
import math
from pathlib import Path

from flask import Flask, render_template, request

app = Flask(__name__)
folder = Path(__file__).resolve().parent / "data"

with (folder / "routes.csv").open(encoding="utf-8") as f:
    routes = {row["route"]: row for row in csv.DictReader(f)}
with (folder / "my_forecast.csv").open(encoding="utf-8") as f:
    forecast = {(row["route"], row["date"]): row for row in csv.DictReader(f)}

dates = sorted({date for route, date in forecast})


@app.route("/", methods=["GET", "POST"])
def index():
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
            demand = float(flight["0.5_base_demand"]) - float(params["price_sensitivity"]) * (
                amount - float(params["base_price"])
            )
            seats = int(flight["seats"])
            result = {"demand": demand, "sales": min(seats, max(0, demand)), "seats": seats}
        except (ValueError, KeyError):
            error = "Проверьте маршрут, дату и цену. Цена должна быть числом не меньше нуля."

    return render_template("index.html", routes=routes, dates=dates, route=route,
                           date=date, price=price, result=result, error=error)


if __name__ == "__main__":
    app.run(port=8000)
