# --- 0. INSTALL DEPENDENCIES ---
!pip install requests searoute groq thefuzz prettytable geopy -q

import os
import requests
import searoute as sr
from groq import Groq
from thefuzz import process
from prettytable import PrettyTable
from geopy.geocoders import Nominatim
from google.colab import userdata

# --- 1. CONFIGURATION & KEYS ---
# Fetching keys from Colab Secrets (Left Sidebar -> Key Icon)
try:
    GROQ_API_KEY = userdata.get("GROQ_API_KEY")
    AIS_KEY = userdata.get("AISSTREAM_API_KEY")
except:
    print("❌ ERROR: Please add GROQ_API_KEY and AISSTREAM_API_KEY to Colab Secrets.")

# Ships for auto-correction logic
COMMON_SHIPS = [
    "EMMA MAERSK", "INS VIKRANT", "EVER GIVEN", "TI EUROPE",
    "MSC OSCAR", "CSCL GLOBE", "HMM ALGECIRAS", "MOL TRIUMPH"
]

# Initialize services
client = Groq(api_key=GROQ_API_KEY)
geolocator = Nominatim(user_agent="aegis_intel_colab_2026")

# --- 2. VALIDATION TOOLS ---

def is_valid_imo(imo):
    """Checks the 7-digit IMO checksum."""
    imo = str(imo).strip().upper().replace("IMO", "")
    if not imo.isdigit() or len(imo) != 7:
        return False
    digits = [int(d) for d in imo]
    check_sum = sum(digits[i] * (7 - i) for i in range(6))
    return check_sum % 10 == digits[6]

def normalize_input(user_input):
    """Corrects typos and identifies input type."""
    clean = user_input.strip().upper()
    if clean.isdigit() and len(clean) == 7:
        return (clean, "IMO") if is_valid_imo(clean) else (None, "INVALID_IMO")

    best_match, score = process.extractOne(clean, COMMON_SHIPS)
    if score > 80:
        return best_match, "NAME"
    return clean, "NAME"

# --- 3. DATA FETCHING ---

def get_live_weather(lat, lon):
    """Fetches real-time wave height."""
    try:
        url = f"https://marine-api.open-meteo.com/v1/marine?latitude={lat}&longitude={lon}&current=wave_height"
        res = requests.get(url, timeout=5).json()
        wave = res['current']['wave_height']
        status = "⚠️ ROUGH" if wave > 2.5 else "✅ CALM"
        return f"{wave}m {status}"
    except:
        return "N/A"

def get_port_and_geo(lat, lon):
    """Finds nearest port and sea address."""
    try:
        loc = geolocator.reverse(f"{lat}, {lon}", language='en', timeout=5)
        addr = loc.address if loc else "Open Sea"
        # searoute uses [lon, lat]
        route = sr.searoute([lon, lat], [0, 0], units="naut", include_ports=True)
        port_info = route['properties'].get('port_origin', {})
        dist = round(route['properties'].get('length', 0), 1)
        p_name = f"{port_info.get('name', 'Unknown')} ({port_info.get('cty', '??')})"
        return addr, p_name, f"{dist} NM"
    except:
        return "Unknown Location", "Unknown Port", "N/A"

def fetch_ais_data(target):
    """Calls the Maritime API."""
    url = "https://datadocked.com/api/vessels_operations/get-vessel-info"
    headers = {"x-api-key": AIS_KEY}
    try:
        res = requests.get(url, headers=headers, params={"imo_or_mmsi": target}, timeout=10)
        return res.json() if res.status_code == 200 else None
    except:
        return None

# --- 4. MAIN INTERFACE ---

def run_agent():
    print("\n🚢 " + "=" * 50)
    print("      AGS MARITIME INTELLIGENCE | COLAB EDITION")
    print("=" * 55)

    while True:
        user_input = input("\nEnter Ship Name or 7-digit IMO (or 'exit'): ").strip()
        if user_input.lower() in ['exit', 'quit']: break

        target, input_type = normalize_input(user_input)
        if input_type == "INVALID_IMO":
            print(f"❌ Checksum Failed for IMO: {user_input}")
            continue

        print(f"📡 Querying Live AIS for {target}...")
        data = fetch_ais_data(target)

        if not data or "error" in data:
            print(f"⚠️ No active signal found for '{target}'.")
            continue

        # Enrichment
        lat, lon = data.get("latitude"), data.get("longitude")
        address, near_port, dist_to_land = get_port_and_geo(lat, lon)
        weather = get_live_weather(lat, lon)

        # Output Table
        table = PrettyTable(["Intelligence Field", "Live Status"])
        table.align = "l"
        table.max_width["Live Status"] = 50

        table.add_row(["NAME", data.get("name")])
        table.add_row(["IMO / MMSI", f"{data.get('imo')} / {data.get('mmsi')}"])
        table.add_row(["FLAG", data.get("country", "Unknown")])
        table.add_row(["LOCATION", address])
        table.add_row(["SEA STATE", weather])
        table.add_row(["DESTINATION", data.get("destination") or "Unknown"])
        table.add_row(["NEAREST PORT", near_port])
        table.add_row(["DIST TO PORT", dist_to_land])
        table.add_row(["STATUS", data.get("nav_status") or "Underway"])

        print(table)

if __name__ == "__main__":
    run_agent()
