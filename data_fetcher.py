"""
data_fetcher.py
================
Builds a connected road-network graph for California, USA.

Data sources:
  - Nominatim (OpenStreetMap) geocoding API -> latitude / longitude of each city
  - OSRM routing API -> real driving distance (miles) for each road connection

"""

import json
import math
import sys
import time
from collections import deque

import requests

# ---------------------------------------------------------------------------
# Region configuration
# ---------------------------------------------------------------------------
REGION_NAME = "California, USA"

# 25 cities spread across the state (north coast, Bay Area, Central Valley,
# Central Coast, Sierra, Southern California, desert).
CITIES = [
    "Eureka, CA",
    "Redding, CA",
    "Chico, CA",
    "Santa Rosa, CA",
    "Sacramento, CA",
    "South Lake Tahoe, CA",
    "San Francisco, CA",
    "Oakland, CA",
    "San Jose, CA",
    "Stockton, CA",
    "Modesto, CA",
    "Merced, CA",
    "Fresno, CA",
    "Salinas, CA",
    "San Luis Obispo, CA",
    "Bakersfield, CA",
    "Santa Barbara, CA",
    "Los Angeles, CA",
    "Anaheim, CA",
    "San Bernardino, CA",
    "Riverside, CA",
    "Barstow, CA",
    "Palm Springs, CA",
    "San Diego, CA",
    "El Centro, CA",
]

# Undirected road connections. Each pair follows a real highway corridor
# (noted in the comment) so the graph looks like the actual road network.
ROAD_CONNECTIONS = [
    # North coast / far north
    ("Eureka, CA", "Santa Rosa, CA"),            # US-101
    ("Eureka, CA", "Redding, CA"),               # CA-299
    ("Redding, CA", "Chico, CA"),                # I-5 / CA-99
    ("Redding, CA", "Sacramento, CA"),           # I-5
    ("Chico, CA", "Sacramento, CA"),             # CA-99
    # Bay Area
    ("Santa Rosa, CA", "San Francisco, CA"),     # US-101
    ("Santa Rosa, CA", "Sacramento, CA"),        # CA-12 / I-80
    ("San Francisco, CA", "Oakland, CA"),        # I-80 Bay Bridge
    ("San Francisco, CA", "San Jose, CA"),       # US-101
    ("Oakland, CA", "San Jose, CA"),             # I-880
    ("Oakland, CA", "Sacramento, CA"),           # I-80
    ("Oakland, CA", "Stockton, CA"),             # I-580 / I-205
    # Sierra
    ("Sacramento, CA", "South Lake Tahoe, CA"),  # US-50
    ("Stockton, CA", "South Lake Tahoe, CA"),    # CA-88
    # Central Valley (CA-99 spine)
    ("Sacramento, CA", "Stockton, CA"),          # I-5
    ("Stockton, CA", "Modesto, CA"),             # CA-99
    ("Modesto, CA", "Merced, CA"),               # CA-99
    ("Merced, CA", "Fresno, CA"),                # CA-99
    ("Fresno, CA", "Bakersfield, CA"),           # CA-99
    ("San Jose, CA", "Merced, CA"),              # CA-152
    ("San Jose, CA", "Modesto, CA"),             # I-680 / I-580 / CA-132
    # Central Coast
    ("San Jose, CA", "Salinas, CA"),             # US-101
    ("Salinas, CA", "San Luis Obispo, CA"),      # US-101
    ("Salinas, CA", "Fresno, CA"),               # US-101 / CA-198 / I-5
    ("San Luis Obispo, CA", "Santa Barbara, CA"),# US-101
    ("San Luis Obispo, CA", "Bakersfield, CA"),  # CA-46 / CA-58
    ("San Luis Obispo, CA", "Fresno, CA"),       # CA-41
    # Southern California
    ("Santa Barbara, CA", "Los Angeles, CA"),    # US-101
    ("Bakersfield, CA", "Los Angeles, CA"),      # I-5 (Grapevine)
    ("Bakersfield, CA", "Barstow, CA"),          # CA-58
    ("Los Angeles, CA", "Anaheim, CA"),          # I-5
    ("Los Angeles, CA", "San Bernardino, CA"),   # I-10
    ("Anaheim, CA", "Riverside, CA"),            # CA-91
    ("Anaheim, CA", "San Diego, CA"),            # I-5
    ("San Bernardino, CA", "Riverside, CA"),     # I-215
    ("San Bernardino, CA", "Barstow, CA"),       # I-15
    ("Riverside, CA", "Palm Springs, CA"),       # I-10
    ("Riverside, CA", "San Diego, CA"),          # I-15
    ("Palm Springs, CA", "El Centro, CA"),       # CA-86
    ("San Diego, CA", "El Centro, CA"),          # I-8
]

USER_AGENT = "CS411-Search-Visualizer/1.0 (UIC CS411 student project, California graph)"
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
OSRM_URL = "https://router.project-osrm.org/route/v1/driving/{lon1},{lat1};{lon2},{lat2}"
METERS_TO_MILES = 0.000621371
MAX_RETRIES = 3


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def haversine_distance(coord1, coord2):
    """Great-circle distance in miles between (lat, lon) pairs."""
    lat1, lon1 = coord1
    lat2, lon2 = coord2
    r = 3958.8
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlmb / 2) ** 2
    return r * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def fetch_coordinates(city_name):
    """Return {"lat": float, "lon": float} for a city using Nominatim, or None."""
    params = {"q": city_name + ", USA", "format": "json", "limit": 1, "countrycodes": "us"}
    headers = {"User-Agent": USER_AGENT}
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.get(NOMINATIM_URL, params=params, headers=headers, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                if data:
                    return {"lat": float(data[0]["lat"]), "lon": float(data[0]["lon"])}
                return None
            print(f"  [Retry {attempt}] Nominatim HTTP {resp.status_code}")
        except requests.RequestException as e:
            print(f"  [Retry {attempt}] Nominatim error: {e}")
        time.sleep(2 * attempt)
    return None


def fetch_road_distance(loc1, loc2):
    """Return driving distance in miles between two locations using OSRM, or None."""
    url = OSRM_URL.format(lon1=loc1["lon"], lat1=loc1["lat"], lon2=loc2["lon"], lat2=loc2["lat"])
    headers = {"User-Agent": USER_AGENT}
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.get(url, params={"overview": "false"}, headers=headers, timeout=20)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("code") == "Ok" and data.get("routes"):
                    return round(data["routes"][0]["distance"] * METERS_TO_MILES, 2)
            print(f"  [Retry {attempt}] OSRM HTTP {resp.status_code}")
        except requests.RequestException as e:
            print(f"  [Retry {attempt}] OSRM error: {e}")
        time.sleep(2 * attempt)
    return None


def is_connected(graph):
    """BFS check that every city is reachable from the first one."""
    if not graph:
        return False
    start = next(iter(graph))
    seen = {start}
    queue = deque([start])
    while queue:
        node = queue.popleft()
        for nb in graph[node]:
            if nb not in seen:
                seen.add(nb)
                queue.append(nb)
    return len(seen) == len(graph)


# ---------------------------------------------------------------------------
# Main build
# ---------------------------------------------------------------------------
def build_graph(output_file="map_data.json"):
    print(f"Building road graph for {REGION_NAME}")
    print(f"Geocoding {len(CITIES)} cities with Nominatim ...")

    locations = {}
    for i, city in enumerate(CITIES, 1):
        coords = fetch_coordinates(city)
        if coords is None:
            sys.exit(f"[Error] Could not geocode {city}. Aborting so no incomplete graph is saved.")
        locations[city] = coords
        print(f"  [{i:2}/{len(CITIES)}] {city:<24} {coords['lat']:.5f}, {coords['lon']:.5f}")
        time.sleep(1.1)  # Nominatim usage policy: max 1 request per second

    print(f"\nFetching OSRM road distances for {len(ROAD_CONNECTIONS)} connections ...")
    graph = {city: {} for city in CITIES}
    edge_count = 0
    for u, v in ROAD_CONNECTIONS:
        dist = fetch_road_distance(locations[u], locations[v])
        if dist is None:
            sys.exit(f"[Error] OSRM failed for {u} <-> {v}. Aborting so no incomplete graph is saved.")
        graph[u][v] = dist
        graph[v][u] = dist
        edge_count += 1
        straight = haversine_distance((locations[u]["lat"], locations[u]["lon"]),
                                      (locations[v]["lat"], locations[v]["lon"]))
        print(f"  {u:<22} <-> {v:<22} road {dist:7.2f} mi  (straight {straight:6.1f} mi)")
        time.sleep(0.5)

    connected = is_connected(graph)
    if not connected:
        sys.exit("[Error] Graph is not connected. Add more ROAD_CONNECTIONS.")

    map_data = {
        "region": REGION_NAME,
        "total_cities": len(locations),
        "total_edges": edge_count,
        "connected": connected,
        "distance_unit": "miles",
        "sources": {
            "geocoding": "Nominatim OpenStreetMap API",
            "routing": "OSRM Routing API (router.project-osrm.org, driving profile)",
        },
        "locations": locations,
        "graph": graph,
    }
    with open(output_file, "w") as f:
        json.dump(map_data, f, indent=2)

    print(f"\nSaved {output_file}: {len(locations)} cities, {edge_count} edges, connected={connected}")


if __name__ == "__main__":
    build_graph()