from pathlib import Path

from flask import Flask, render_template, request
from Algorithms.BFS import BFS

from route_service import RouteService
import threading

app = Flask(__name__)
ROUND_TRIP_DISCOUNT = 0.15

BASE_DIR = Path(__file__).parent

ROUTES_FILE = BASE_DIR/"AirlineData"/"airline_routes.json"
AIRLINE_CLASSIFICATIONS_FILE = BASE_DIR/"AirlineData"/"airline_classifications.json"
route_service = RouteService(ROUTES_FILE, AIRLINE_CLASSIFICATIONS_FILE)

def precompute_hubs():
    route_service.get_hubs(top_n=20)
threading.Thread(target=precompute_hubs, daemon=True).start()


def format_price(amount):
    return f"${amount:.2f}"


def set_price_display_for_routes(route_items, price_display):
    for item in route_items or []:
        if isinstance(item, dict):
            item["price_display"] = price_display


def apply_round_trip_price_display(outbound_result, inbound_result, discount_rate=ROUND_TRIP_DISCOUNT):
    outbound_best = (outbound_result or {}).get("best")
    inbound_best = (inbound_result or {}).get("best")

    if not outbound_best or not inbound_best:
        return

    outbound_price = float(outbound_best.get("price", 0) or 0)
    inbound_price = float(inbound_best.get("price", 0) or 0)
    original_total = round(outbound_price + inbound_price, 2)
    discount_amount = round(original_total * discount_rate, 2)
    discounted_total = round(original_total - discount_amount, 2)

    outbound_best["outbound_price_total"] = round(outbound_price, 2)
    outbound_best["inbound_price_total"] = round(inbound_price, 2)
    outbound_best["original_round_trip_price"] = original_total
    outbound_best["round_trip_discount_amount"] = discount_amount
    outbound_best["round_trip_discount_pct"] = int(discount_rate * 100)
    outbound_best["price"] = discounted_total
    outbound_best["price_display"] = format_price(discounted_total)

    inbound_best["price_display"] = "-"
    inbound_best["hide_price_details"] = True

    set_price_display_for_routes((inbound_result or {}).get("routes"), "-")
    set_price_display_for_routes((inbound_result or {}).get("dfs_routes"), "-")


def choose_selected_route(base_result, route_codes, mode, depart_date_str=None):
    selected_key = tuple(route_codes)
    selected_route = None
    remaining_routes = []

    best = (base_result or {}).get("best")
    if best:
        if tuple(best.get("route", [])) == selected_key:
            selected_route = best
        else:
            remaining_routes.append(best)

    for item in (base_result or {}).get("routes", []):
        item_key = tuple(item.get("route", []))
        if item_key == selected_key:
            selected_route = item
        else:
            remaining_routes.append(item)

    if not selected_route:
        selected_route = route_service.buildRouteResult(route_codes, mode, depart_date_str=depart_date_str)

    return {
        "best": selected_route,
        "routes": remaining_routes,
    }

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

    def get_bellmanford_route_with_direct_fallback(source, destination, current_mode, date_str):
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

        res = route_service.computeBellmanFordResults(source, destination, final_mode, date_str)
        return res, final_mode, no_direct_found

    if tripType == "return":
        result, final_mode_outbound, no_direct = get_bellmanford_route_with_direct_fallback(src, dst, mode, departDate)
    else:
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
        return_result, final_mode_return, return_no_direct = get_bellmanford_route_with_direct_fallback(dst, src, mode, returnDate)
        
        returnDfsResult = route_service.computeDfsResults(dst, src, final_mode_return, sort_by="distance")
        return_result["dfs_routes"] = returnDfsResult.get("routes", [])
        return_result["dfs_timed_out"] = returnDfsResult.get("timed_out", False)
        return_result["dfs_sort_by"] = "distance"
        return_result["trip_type"] = "return"
        return_result["depart_date"] = returnDate

        apply_round_trip_price_display(result, return_result)

    return render_template("results.html", src=src, dst=dst, mode=mode, search_type=searchType, result=result, return_result=return_result, no_direct=no_direct, return_no_direct=return_no_direct)

@app.post("/route-option")
def route_option():
    src = request.form.get("src", "").strip()
    dst = request.form.get("dst", "").strip()
    mode = request.form.get("mode", "distance").strip()
    tripType = request.form.get("trip_type", "oneway").strip()
    departDate = request.form.get("depart_date", "").strip()
    returnDate = request.form.get("return_date", "").strip()
    selectionTarget = request.form.get("selection_target", "outbound").strip()
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

    if tripType == "return":
        outbound_base = route_service.computeBellmanFordResults(src, dst, mode, departDate)
        outbound_dfs = route_service.computeDfsResults(src, dst, mode, sort_by="distance")
        outbound_base["dfs_routes"] = outbound_dfs.get("routes", [])
        outbound_base["dfs_timed_out"] = outbound_dfs.get("timed_out", False)
        outbound_base["dfs_sort_by"] = "distance"
        outbound_base["trip_type"] = tripType
        outbound_base["depart_date"] = departDate

        inbound_base = route_service.computeBellmanFordResults(dst, src, mode, returnDate)
        inbound_dfs = route_service.computeDfsResults(dst, src, mode, sort_by="distance")
        inbound_base["dfs_routes"] = inbound_dfs.get("routes", [])
        inbound_base["dfs_timed_out"] = inbound_dfs.get("timed_out", False)
        inbound_base["dfs_sort_by"] = "distance"
        inbound_base["trip_type"] = "return"
        inbound_base["depart_date"] = returnDate

        if selectionTarget == "return":
            return_result = choose_selected_route(inbound_base, routeCodes, mode, returnDate)
            return_result["dfs_routes"] = inbound_base.get("dfs_routes", [])
            return_result["dfs_timed_out"] = inbound_base.get("dfs_timed_out", False)
            return_result["dfs_sort_by"] = inbound_base.get("dfs_sort_by", "distance")
            return_result["trip_type"] = "return"
            return_result["depart_date"] = returnDate
            result = outbound_base
        else:
            result = choose_selected_route(outbound_base, routeCodes, mode, departDate)
            result["dfs_routes"] = outbound_base.get("dfs_routes", [])
            result["dfs_timed_out"] = outbound_base.get("dfs_timed_out", False)
            result["dfs_sort_by"] = outbound_base.get("dfs_sort_by", "distance")
            result["trip_type"] = tripType
            result["depart_date"] = departDate
            return_result = inbound_base

        apply_round_trip_price_display(result, return_result)
        return render_template(
            "results.html",
            src=src,
            dst=dst,
            mode=mode,
            search_type="route",
            result=result,
            return_result=return_result,
            no_direct=False,
            return_no_direct=False,
        )

    baseResult = route_service.computeAlgorithmResults(src, dst, mode)
    result = choose_selected_route(baseResult, routeCodes, mode, departDate)
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
