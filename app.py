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
    tripType = request.form.get("trip_type", "oneway").strip()
    departDate = request.form.get("depart_date", "").strip()
    returnDate = request.form.get("return_date", "").strip()
    mode = request.form.get("mode", "distance").strip()
    radiusRaw = request.form.get("radius_km", "500").strip()
    budgetRaw = request.form.get("budget", "500").strip()
    targetCitiesRaw = request.form.get("target_cities", "3").strip()

    try:
        radiusKm = max(1.0, float(radiusRaw))
        budget = max(1.0, float(budgetRaw))
        targetCities = max(1, int(targetCitiesRaw))
    except ValueError:
        radiusKm = 500.0
        budget = 500.0
        targetCities = 2

    if searchType == "proximity":
        if not src:
            return render_template(
                "nearby_results.html",
                src=src or "N/A",
                result={"type": "proximity", "origin": None, "airports": [], "map_points": [], "radius_km": radiusKm, "count": 0},
            )

        result = route_service.findAirportsWithinRadius(src, radiusKm)
        return render_template("nearby_results.html", src=src, result=result)
    
    if searchType == "budget_loop":
        if not src:
            return render_template(
                "budget_results.html",
                src=src or "N/A",
                result = {
                            "type" : "budget_loop",
                            "origin" : None,
                            "budget" : budget,
                            "best_route" : None
                        },
            )
        result = route_service.findBestBudgetLoop(src, budget, targetCities)
        return render_template("budget_results.html",src=src, result = result)

    if not src or not dst or src == dst:
        return render_template(
            "results.html",
            src=src or "N/A",
            dst=dst or "N/A",
            mode=mode,
            search_type=searchType,
            result={"best": None, "routes": []},
        )

    def get_route_with_direct_fallback(source, destination, current_mode, date_str):
        no_direct_found = False
        final_mode = current_mode
        if current_mode == "direct":
            bfs_solver = BFS(route_service.weightedGraph.graph)
            direct_route = bfs_solver.shortest_path(source, destination, "direct")
            if direct_route and len(direct_route["route"]) == 2:
                best = route_service.buildRouteResult(direct_route["route"], current_mode, depart_date_str=date_str)
                if best:
                    best["mode"] = current_mode
                    res = {"best": best, "routes": []}
                    return res, final_mode, no_direct_found
            
            final_mode = "stops"
            no_direct_found = True
        
        res = route_service.computeAlgorithmResults(source, destination, final_mode, date_str)
        return res, final_mode, no_direct_found

    result, final_mode_outbound, no_direct = get_route_with_direct_fallback(src, dst, mode, departDate)
    
    dfsResult = route_service.computeDfsResults(src, dst, final_mode_outbound, sort_by="distance")
    result["dfs_routes"] = dfsResult.get("routes", [])
    result["dfs_timed_out"] = dfsResult.get("timed_out", False)
    result["dfs_sort_by"] = "distance"
    result["trip_type"] = tripType
    result["depart_date"] = departDate

    return_result = None
    return_no_direct = False
    
    if tripType == "return":
        return_result, final_mode_return, return_no_direct = get_route_with_direct_fallback(dst, src, mode, returnDate)
        
        returnDfsResult = route_service.computeDfsResults(dst, src, final_mode_return, sort_by="distance")
        return_result["dfs_routes"] = returnDfsResult.get("routes", [])
        return_result["dfs_timed_out"] = returnDfsResult.get("timed_out", False)
        return_result["dfs_sort_by"] = "distance"
        return_result["trip_type"] = "return"
        return_result["depart_date"] = returnDate

    return render_template("results.html", src=src, dst=dst, mode=mode, search_type=searchType, result=result, return_result=return_result, no_direct=no_direct, return_no_direct=return_no_direct)

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
    trip_type = request.args.get("trip_type", "oneway").strip()
    depart_date_str = request.args.get("depart_date", "").strip()
    return_date_str = request.args.get("return_date", "").strip()

    from datetime import datetime
    depart_date = None
    if depart_date_str:
        try:
            depart_date = datetime.strptime(depart_date_str, "%Y-%m-%d")
        except ValueError:
            pass

    return_date = None
    if return_date_str:
        try:
            return_date = datetime.strptime(return_date_str, "%Y-%m-%d")
        except ValueError:
            pass

    outbound_result = {}
    return_result = {}
    if src and dst and src != dst:
        outbound_result = route_service.get_flight_schedule(src, dst, depart_date)
        if trip_type == "return":
            return_result = route_service.get_flight_schedule(dst, src, return_date)
    return render_template(
        "schedule.html",
        airports=route_service.airports,
        src=src,
        dst=dst,
        outbound_result=outbound_result,
        return_result=return_result,
        trip_type=trip_type,
    )
 
 
@app.get("/hubs")
def hubs():
    hubs_list = route_service.get_hubs(top_n=20)
    return render_template("hubs.html", hubs=hubs_list)


if __name__ == "__main__":
    app.run(debug=True)
