from pathlib import Path

from flask import Flask, render_template, request

from route_service import RouteService

app = Flask(__name__)

ROUTES_FILE = Path(__file__).with_name("airline_routes.json")
route_service = RouteService(ROUTES_FILE)


@app.get("/")
def index():
    return render_template("index.html", airports=route_service.airports)


@app.post("/search")
def search():
    src = request.form.get("src", "").strip()
    dst = request.form.get("dst", "").strip()
    mode = request.form.get("mode", "distance").strip()

    if not src or not dst or src == dst:
        return render_template(
            "results.html",
            src=src or "N/A",
            dst=dst or "N/A",
            mode=mode,
            result={"best": None, "routes": []},
        )

    result = route_service.compute_algorithm_results(src, dst, mode)
    return render_template("results.html", src=src, dst=dst, mode=mode, result=result)


if __name__ == "__main__":
    app.run()
