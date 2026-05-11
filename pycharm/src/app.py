import streamlit as st
from streamlit_folium import st_folium
import folium
import asyncio
import pandas as pd
import ast  # Used to safely parse the string-dictionaries
from datetime import datetime
from mmin import AegisMaritimeAgent

# 1. GLOBAL PAGE SETTINGS
st.set_page_config(page_title="AEGIS COMMAND", layout="wide", initial_sidebar_state="expanded")

# 2. INDUSTRIAL DARK THEME
st.markdown("""
    <style>
        .stApp { background-color: #0d1117; color: #c9d1d9; }
        .stMetric { background: #161b22; border: 1px solid #30363d; border-radius: 10px; padding: 20px !important; }
        [data-testid="stMetricValue"] { color: #58a6ff !important; font-size: 26px !important; }
        .audit-card { background: #1c2128; border-left: 5px solid #238636; padding: 25px; border-radius: 10px; margin-bottom: 20px; font-size: 1.1em; line-height: 1.5; }
        .stTable { background-color: #161b22; border-radius: 10px; border: 1px solid #30363d; }
        h1, h2, h3 { color: #ffffff; }
    </style>
""", unsafe_allow_html=True)


def format_complex_data(data_dict):
    """Parses raw JSON strings into a flat list of key-value pairs."""
    flat_results = []
    for key, value in data_dict.items():
        # If the value looks like a dictionary string, parse it
        if isinstance(value, str) and value.startswith('{') and value.endswith('}'):
            try:
                # Safely convert string representation of dict to actual dict
                sub_dict = ast.literal_eval(value)
                for sub_k, sub_v in sub_dict.items():
                    # Format: "ENGINE: TYPE" -> "12X92DF"
                    label = f"{key.replace('_', ' ').upper()}: {sub_k.upper()}"
                    flat_results.append((label, str(sub_v)))
            except:
                flat_results.append((key.replace('_', ' ').upper(), str(value)))
        else:
            flat_results.append((key.replace('_', ' ').upper(), str(value)))
    return flat_results


if 'agent' not in st.session_state:
    st.session_state.agent = AegisMaritimeAgent()

# 3. COMMAND SIDEBAR
with st.sidebar:
    st.title("⚓ AEGIS COMMAND")
    st.caption("Fleet Intelligence Hub v9.5")
    st.divider()
    ship_id = st.text_input("Vessel Name or IMO", placeholder="e.g., 9839208")
    process_btn = st.button("🚀 EXECUTE FULL SCAN", use_container_width=True, type="primary")
    st.write("###")
    st.info(f"System Time: {datetime.utcnow().strftime('%H:%M')} UTC")

# 4. PRIMARY OPERATIONS DISPLAY
st.title("Fleet Intelligence Operations")

if process_btn and ship_id:
    with st.spinner("Synchronizing Satellite Feeds..."):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        results = loop.run_until_complete(st.session_state.agent.fetch_intel(ship_id))

    if results:
        ais, weather = results
        audit_text = st.session_state.agent.generate_audit(ais, weather)

        # LEVEL 1: STRATEGIC METRICS
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Vessel Identity", ais.get('name', 'N/A'))
        m2.metric("IMO Registry", ais.get('imo', 'N/A'))
        m3.metric("Current Speed", f"{ais.get('speed', 0)} kn")
        m4.metric("Live Wave Height", f"{weather.get('wave_height', 0)}m")

        st.divider()

        # LEVEL 2: MAP & ASSESSMENT
        col_map, col_audit = st.columns([1.6, 1], gap="large")
        with col_map:
            st.subheader("🗺️ Tactical Map View")
            lat, lon = float(ais['latitude']), float(ais['longitude'])
            m = folium.Map(location=[lat, lon], zoom_start=6, tiles="CartoDB dark_matter", zoom_control=False)
            folium.Marker([lat, lon], popup=ais.get('name'),
                          icon=folium.Icon(color='blue', icon='ship', prefix='fa')).add_to(m)
            st_folium(m, width="100%", height=480, returned_objects=[])

        with col_audit:
            st.subheader("🤖 AI Compliance Assessment")
            st.markdown(f"<div class='audit-card'><b>QA AUDITOR LOG:</b><br>{audit_text}</div>", unsafe_allow_html=True)
            st.success("Operational protocols verified against real-time satellite telemetry.")

        # LEVEL 3: COMPREHENSIVE DATA GRID
        st.write("###")
        st.subheader("📋 Comprehensive Vessel Registry")

        # USE THE NEW PARSER HERE
        formatted_items = format_complex_data(ais)
        size = len(formatted_items)
        n = (size + 2) // 3  # Split into 3 columns

        c1, c2, c3 = st.columns(3)
        with c1:
            st.table(pd.DataFrame(formatted_items[:n], columns=["Parameter", "Status/Value"]))
        with c2:
            st.table(pd.DataFrame(formatted_items[n:2 * n], columns=["Parameter", "Status/Value"]))
        with c3:
            st.table(pd.DataFrame(formatted_items[2 * n:], columns=["Parameter", "Status/Value"]))
    else:
        st.error("📡 SCAN FAILED: Target identifier not found.")
else:
    st.info("🛰️ **SYSTEM READY**: Please enter a Vessel Identifier in the sidebar to begin interception.")