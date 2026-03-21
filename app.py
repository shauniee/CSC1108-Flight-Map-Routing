from pathlib import Path

from flask import Flask, render_template, request
from BFS import BFS

from route_service import RouteService
import threading

app = Flask(__name__)

BASE_DIR = Path(__file__).parent

ROUTES_FILE = BASE_DIR/"AirlineData"/"airline_routes.json"
AIRLINE_CLASSIFICATIONS_FILE = BASE_DIR/"AirlineData"/"airline_classifications.json"
route_service = RouteService(ROUTES_FILE, AIRLINE_CLASSIFICATIONS_FILE)

def precompute_hubs():
    route_service.get_hubs(top_n=20)
threading.Thread(target=precompute_hubs, daemon=True).start()

@app.get("/")
def index():
    return render_template("index.html", airports=route_service.airports)


@app.post("/search")
def search():
    searchType = request.form.get("search_type", "route").strip()
    src = request.form.get("src", "").strip()
    dst = request.form.get("dst", "").strip()
    mode = request.form.get("mode", "distance").strip()
    radiusRaw = request.form.get("radius_km", "500").strip()

    try:
        radiusKm = max(1.0, float(radiusRaw))
    except ValueError:
        radiusKm = 500.0

    if searchType == "proximity":
        if not src:
            return render_template(
                "nearby_results.html",
                src=src or "N/A",
                result={"type": "proximity", "origin": None, "airports": [], "map_points": [], "radius_km": radiusKm, "count": 0},
            )

        result = route_service.findAirportsWithinRadius(src, radiusKm)
        return render_template("nearby_results.html", src=src, result=result)

    if not src or not dst or src == dst:
        return render_template(
            "results.html",
            src=src or "N/A",
            dst=dst or "N/A",
            mode=mode,
            search_type=searchType,
            result={"best": None, "routes": []},
        )

    result = route_service.computeAlgorithmResults(src, dst, mode)
    dfsResult = route_service.computeDfsResults(src, dst, mode, sort_by="distance")
    result["dfs_routes"] = dfsResult.get("routes", [])
    result["dfs_timed_out"] = dfsResult.get("timed_out", False)
    result["dfs_sort_by"] = "distance"
    return render_template("results.html", src=src, dst=dst, mode=mode, search_type=searchType, result=result)

@app.post("/route-option")
def route_option():
    src = request.form.get("src", "").strip()
    dst = request.form.get("dst", "").strip()
    mode = request.form.get("mode", "distance").strip()
    routeRaw = request.form.get("route", "").strip()
    routeCodes = [code.strip() for code in routeRaw.split(",") if code.strip()]

    if not src or not dst or len(routeCodes) < 2:
        return render_template(
            "results.html",
            src=src or "N/A",
            dst=dst or "N/A",
            mode=mode,
            search_type="route",
            result={"best": None, "routes": []},
        )

    baseResult = route_service.computeAlgorithmResults(src, dst, mode)
    selectedKey = tuple(routeCodes)
    selectedRoute = None
    remainingRoutes = []

    best = baseResult.get("best")
    if best:
        if tuple(best.get("route", [])) == selectedKey:
            selectedRoute = best
        else:
            remainingRoutes.append(best)

    for item in baseResult.get("routes", []):
        itemKey = tuple(item.get("route", []))
        if itemKey == selectedKey:
            selectedRoute = item
        else:
            remainingRoutes.append(item)

    if not selectedRoute:
        selectedRoute = route_service.buildRouteResult(routeCodes, mode)

    result = {
        "best": selectedRoute,
        "routes": remainingRoutes,
    }
    return render_template("results.html", src=src, dst=dst, mode=mode, search_type="route", result=result)


@app.post("/dfs-routes")
def dfs_routes():
    src = request.form.get("src", "").strip()
    dst = request.form.get("dst", "").strip()
    mode = request.form.get("mode", "distance").strip()
    sort_by = request.form.get("sort_by", "duration").strip()

    if not src or not dst or src == dst:
        return render_template(
            "results.html",
            src=src or "N/A",
            dst=dst or "N/A",
            mode=mode,
            search_type="route",
            result={"best": None, "routes": []},
        )

    result = route_service.computeAlgorithmResults(src, dst, mode)
    dfsResult = route_service.computeDfsResults(src, dst, mode, sort_by=sort_by)
    result["dfs_routes"] = dfsResult.get("routes", [])
    result["dfs_timed_out"] = dfsResult.get("timed_out", False)
    result["dfs_sort_by"] = sort_by
    return render_template("results.html", src=src, dst=dst, mode=mode, search_type="route", result=result)


@app.get("/schedule")
def schedule():
    src = request.args.get("src", "").strip().upper()
    dst = request.args.get("dst", "").strip().upper()
    result = {}
    if src and dst and src != dst:
        result = route_service.get_flight_schedule(src, dst)
    return render_template(
        "schedule.html",
        airports=route_service.airports,
        src=src,
        dst=dst,
        result=result,
    )
 
 
@app.get("/hubs")
def hubs():
    hubs_list = route_service.get_hubs(top_n=20)
    return render_template("hubs.html", hubs=hubs_list)


if __name__ == "__main__":
    app.run(debug=True)
