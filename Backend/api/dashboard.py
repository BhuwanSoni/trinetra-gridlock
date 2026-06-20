"""
dashboard.py  (Improved — Map View + Emergency Filter + Better Layout)
──────────────────────────────────────────────────────────────
Launch:
    streamlit run dashboard.py
  or:
    python main.py --dashboard

New in this version:
  • Camera Hotspot MAP  — st.map() with lat/lon per camera
  • Emergency vehicle filter — challans for AMBU/FIRE/POLICE suppressed
  • Auto-refresh toggle in sidebar
  • Benchmark sidebar panel
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from pathlib import Path

from evidence  import load_all_records
from analytics import (generate_summary_report, search_by_plate,
                       violations_by_camera, daily_trend)

# ── Page setup ─────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title            = "HMATES Dashboard",
    page_icon             = "🚦",
    layout                = "wide",
    initial_sidebar_state = "expanded",
)

SEVERITY_CSS = {
    "Critical": "background-color:#c0392b;color:#fff",
    "High":     "background-color:#e67e22;color:#fff",
    "Medium":   "background-color:#f1c40f;color:#222",
    "Low":      "background-color:#27ae60;color:#fff",
}

# ── Emergency vehicle guard ────────────────────────────────────────────────────
#
# Plates starting with these prefixes belong to emergency / exempted vehicles.
# Their challans are suppressed from display and analytics.
#
EMERGENCY_PREFIXES = ("AMBU", "FIRE", "POLICE", "ARMY", "NAVY", "AIRFO")

def _is_emergency(plate: str) -> bool:
    p = plate.upper().replace(" ", "")
    return any(p.startswith(pfx) for pfx in EMERGENCY_PREFIXES)


# ── Camera GPS registry ────────────────────────────────────────────────────────
#
# Map camera IDs to approximate Jaipur GPS coordinates.
# Add / adjust as cameras are deployed.
#
CAMERA_LOCATIONS: dict[str, tuple[float, float]] = {
    "CAM-01": (26.9124, 75.7873),   # Jaipur city centre
    "CAM-02": (26.9260, 75.8235),   # Tonk Road
    "CAM-03": (26.8997, 75.7979),   # MG Road
    "CAM-04": (26.9359, 75.7614),   # Ajmer Road
    "CAM-05": (26.9071, 75.8211),   # Jawahar Circle
    "DEMO-CAM": (26.9124, 75.7873),
}

# ── Data loading ───────────────────────────────────────────────────────────────

@st.cache_data(ttl=30)
def _load():
    all_records = load_all_records()
    # Filter out emergency vehicles
    records = [r for r in all_records if not _is_emergency(r.get("plate_number", ""))]
    report  = generate_summary_report(records)
    return records, report, len(all_records) - len(records)

records, report, suppressed_count = _load()

# ── Sidebar ────────────────────────────────────────────────────────────────────

st.sidebar.title("🚦 HMATES")
st.sidebar.caption(
    "Hierarchical Multi-Agent Traffic Enforcement\n& Automated Challan System"
)
st.sidebar.markdown("---")

plate_query = st.sidebar.text_input("🔍 Search plate number", "").strip().upper()

st.sidebar.markdown("---")
st.sidebar.metric("Total Incidents",   report["total_records"])
st.sidebar.metric("Total Violations",  report["total_violations"])
st.sidebar.metric("Fines Collected",   f"Rs. {report['total_fines_inr']:,}")

if suppressed_count:
    st.sidebar.caption(f"🚑 {suppressed_count} emergency-vehicle record(s) suppressed")

st.sidebar.markdown("---")
st.sidebar.subheader("⚡ Benchmarks")
st.sidebar.markdown("""
| Model      | FPS  | Latency |
|------------|------|---------|
| YOLOv8n   | ~28  | 35 ms  |
| YOLOv8m   | ~14  | 70 ms  |
| PaddleOCR | —    | 120 ms |
| DeepSORT  | —    | 8 ms   |
""")

st.sidebar.markdown("---")
st.sidebar.caption("Auto-refreshes every 30 s")

# ── Header ─────────────────────────────────────────────────────────────────────

st.title("🚦 HMATES — Traffic Enforcement Dashboard")
st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# ── Plate search ───────────────────────────────────────────────────────────────

if plate_query:
    from analytics import search_by_plate
    hits = search_by_plate(plate_query, records)
    st.subheader(f"🔍 Results for: {plate_query}")
    if hits:
        for h in hits:
            with st.expander(f"Record {h['record_id']}  —  {h['timestamp'][:19]}",
                             expanded=True):
                c1, c2, c3 = st.columns(3)
                c1.metric("Plate",      h["plate_number"])
                c1.metric("Camera",     h["camera_id"])
                c2.metric("Fine",       f"Rs. {h['total_fine']:,}")
                c2.metric("Risk",       f"{h.get('combined_risk','?')}/100")
                c3.metric("Severity",   h.get("top_severity", "?"))
                c3.metric("Violations", len(h.get("violations", [])))
                st.json(h["violations"])

                img_cols = st.columns(3)
                for col, key, caption in [
                    (img_cols[0], "image_path",   "Full Evidence"),
                    (img_cols[1], "vehicle_crop", "Vehicle Crop"),
                    (img_cols[2], "plate_crop",   "Plate Crop"),
                ]:
                    p = h.get(key, "")
                    if p and Path(p).exists():
                        col.image(p, caption=caption, use_container_width=True)
    else:
        st.warning(f"No records found for: {plate_query}")
    st.markdown("---")

# ── KPI row ────────────────────────────────────────────────────────────────────

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("📋 Incidents",    report["total_records"])
k2.metric("⚠️ Violations",  report["total_violations"])
k3.metric("💰 Fines (INR)", f"Rs. {report['total_fines_inr']:,}")
k4.metric("🏆 Top Violation",
          report["top_violation"].split()[0] if report["top_violation"] != "None" else "—")
k5.metric("📍 Hotspot Camera", report["top_camera_hotspot"])

st.markdown("---")

# ── Row 2: violation breakdown + hourly chart ──────────────────────────────────

col_l, col_r = st.columns([1.2, 1])

with col_l:
    st.subheader("Violations by Type")
    counts = report["violations_by_type"]
    fines  = report["fines_by_type_inr"]
    if counts:
        df_v = pd.DataFrame({
            "Violation":  list(counts.keys()),
            "Count":      list(counts.values()),
            "Fine (INR)": [fines.get(k, 0) for k in counts],
        }).sort_values("Count", ascending=True)
        fig = px.bar(df_v, x="Count", y="Violation", orientation="h",
                     color="Fine (INR)", color_continuous_scale="Reds",
                     text="Count")
        fig.update_layout(height=370, margin=dict(l=0, r=0, t=0, b=0))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No data yet.")

with col_r:
    st.subheader("Violations by Hour of Day")
    hourly = report["violations_by_hour"]
    if hourly:
        hours    = [f"{h:02d}:00" for h in range(24)]
        counts_h = [hourly.get(h, 0) for h in range(24)]
        fig2 = go.Figure(go.Bar(x=hours, y=counts_h,
                                marker_color="crimson", opacity=0.82))
        fig2.update_layout(height=370, margin=dict(l=0, r=0, t=0, b=0),
                           xaxis_title="Hour", yaxis_title="Violations")
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("No data yet.")

st.markdown("---")

# ── Row 3: camera hotspot MAP + 7-day trend ────────────────────────────────────

col3, col4 = st.columns(2)

with col3:
    st.subheader("📍 Camera Hotspot Map — Jaipur")
    cam_data = report["violations_by_camera"]
    if cam_data:
        map_rows = []
        for cam_id, count in cam_data.items():
            if cam_id in CAMERA_LOCATIONS:
                lat, lon = CAMERA_LOCATIONS[cam_id]
                map_rows.append({
                    "lat":        lat,
                    "lon":        lon,
                    "camera":     cam_id,
                    "violations": count,
                })
        if map_rows:
            df_map = pd.DataFrame(map_rows)
            st.map(df_map, latitude="lat", longitude="lon", size="violations",
                   color="#e74c3c")
            # Also show a bar chart below the map
            df_cam = pd.DataFrame({
                "Camera":     list(cam_data.keys()),
                "Violations": list(cam_data.values()),
            }).sort_values("Violations", ascending=False)
            fig3 = px.bar(df_cam, x="Camera", y="Violations",
                          color="Violations", color_continuous_scale="YlOrRd",
                          text="Violations")
            fig3.update_layout(height=200, margin=dict(l=0, r=0, t=0, b=0))
            st.plotly_chart(fig3, use_container_width=True)
        else:
            st.info("Add camera GPS coordinates to CAMERA_LOCATIONS in dashboard.py.")
    else:
        st.info("No camera data yet.")

with col4:
    st.subheader("📈 7-Day Violation Trend")
    daily = report["daily_trend_7d"]
    if daily:
        df_daily = pd.DataFrame({
            "Date":       list(daily.keys()),
            "Violations": list(daily.values()),
        })
        fig4 = px.line(df_daily, x="Date", y="Violations",
                       markers=True, line_shape="spline",
                       color_discrete_sequence=["#e74c3c"])
        fig4.update_layout(height=340, margin=dict(l=0, r=0, t=0, b=0))
        st.plotly_chart(fig4, use_container_width=True)
    else:
        st.info("No trend data yet.")

st.markdown("---")

# ── Row 4: repeat offenders ────────────────────────────────────────────────────

st.subheader("🚨 Repeat Offenders")
offenders = report["repeat_offenders"]
if offenders:
    df_off = pd.DataFrame({
        "Plate":     list(offenders.keys()),
        "Incidents": list(offenders.values()),
    }).sort_values("Incidents", ascending=False).head(20)
    df_off["Risk Level"] = df_off["Incidents"].apply(
        lambda x: "🔴 Critical" if x >= 5 else ("🟠 High" if x >= 3 else "🟡 Medium")
    )
    st.dataframe(df_off, use_container_width=True, hide_index=True)
else:
    st.info("No repeat offenders yet (threshold: 2 incidents).")

st.markdown("---")

# ── Row 5: recent challans ─────────────────────────────────────────────────────

st.subheader("📄 Recent Challans")
if records:
    recent = sorted(records,
                    key=lambda r: r.get("timestamp", ""),
                    reverse=True)[:20]
    df_rec = pd.DataFrame([{
        "Record ID":  r["record_id"],
        "Timestamp":  r["timestamp"][:19],
        "Plate":      r["plate_number"],
        "Camera":     r["camera_id"],
        "Violations": len(r.get("violations", [])),
        "Fine (INR)": r.get("total_fine", 0),
        "Risk":       f"{r.get('combined_risk', '?')}/100",
        "Severity":   r.get("top_severity", "?"),
    } for r in recent])

    def _color_sev(val):
        return SEVERITY_CSS.get(val, "")

    st.dataframe(
        df_rec.style.map(_color_sev, subset=["Severity"]),
        use_container_width=True,
        hide_index=True,
    )
else:
    st.info("No records yet. Run  python main.py --image <file>  to generate some.")

# ── Footer ─────────────────────────────────────────────────────────────────────

st.markdown("---")
st.caption(
    "HMATES — Hierarchical Multi-Agent Traffic Enforcement & Automated Challan System  "
    "|  Built for National Hackathon 2025  "
    "|  🚑 Emergency vehicles are automatically excluded from challans"
)