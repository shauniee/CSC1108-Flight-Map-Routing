from pathlib import Path

from flask import Flask, render_template, request

from route_service import RouteService

app = Flask(__name__)

BASE_DIR = Path(__file__).parent

ROUTES_FILE = BASE_DIR/"AirlineData"/"airline_routes.json"
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

    result = route_service.computeAlgorithmResults(src, dst, mode)
    return render_template("results.html", src=src, dst=dst, mode=mode, result=result)


if __name__ == "__main__":
    app.run(debug=True)
