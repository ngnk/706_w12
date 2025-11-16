"""
Real-Time IoT Environmental Monitoring Dashboard

Features:
- Live sensor readings visualization
- Windowed aggregations from stream processor
- ML anomaly detection insights
- Interactive filtering and drill-down
- Real-time metrics and KPIs
"""

import time
from datetime import datetime, timedelta
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
from sqlalchemy import create_engine, text

# Page configuration
st.set_page_config(
    page_title="IoT Environmental Monitoring",
    page_icon="🌡️",
    layout="wide"
)

st.title("🌡️ Real-Time IoT Environmental Monitoring Dashboard")

# Database connection
DATABASE_URL = "postgresql://iot_user:iot_password@localhost:5432/iot_db"

@st.cache_resource
def get_engine(url: str):
    return create_engine(url, pool_pre_ping=True)

engine = get_engine(DATABASE_URL)


# Data loading functions
def load_recent_readings(location_filter: str = None, sensor_type_filter: str = None, 
                        limit: int = 500) -> pd.DataFrame:
    """Load recent raw sensor readings."""
    query = "SELECT * FROM sensor_readings WHERE 1=1"
    params = {}
    
    if location_filter and location_filter != "All":
        query += " AND location = :location"
        params["location"] = location_filter
    
    if sensor_type_filter and sensor_type_filter != "All":
        query += " AND sensor_type = :sensor_type"
        params["sensor_type"] = sensor_type_filter
    
    query += " ORDER BY timestamp DESC LIMIT :limit"
    params["limit"] = limit
    
    try:
        df = pd.read_sql_query(text(query), con=engine.connect(), params=params)
        if not df.empty and "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"])
        return df
    except Exception as e:
        st.error(f"Error loading readings: {e}")
        return pd.DataFrame()


def load_aggregates(hours_back: int = 2) -> pd.DataFrame:
    """Load windowed aggregations from stream processor."""
    cutoff = datetime.now() - timedelta(hours=hours_back)
    
    query = """
        SELECT * FROM sensor_aggregates 
        WHERE window_start >= :cutoff
        ORDER BY window_start DESC
    """
    
    try:
        df = pd.read_sql_query(
            text(query), 
            con=engine.connect(), 
            params={"cutoff": cutoff}
        )
        if not df.empty:
            df["window_start"] = pd.to_datetime(df["window_start"])
            df["window_end"] = pd.to_datetime(df["window_end"])
        return df
    except Exception as e:
        st.error(f"Error loading aggregates: {e}")
        return pd.DataFrame()


def load_ml_predictions(hours_back: int = 1) -> pd.DataFrame:
    """Load ML anomaly predictions."""
    cutoff = datetime.now() - timedelta(hours=hours_back)
    
    query = """
        SELECT * FROM ml_anomaly_predictions 
        WHERE timestamp >= :cutoff
        ORDER BY timestamp DESC
    """
    
    try:
        df = pd.read_sql_query(
            text(query), 
            con=engine.connect(), 
            params={"cutoff": cutoff}
        )
        if not df.empty:
            df["timestamp"] = pd.to_datetime(df["timestamp"])
        return df
    except Exception as e:
        st.error(f"Error loading ML predictions: {e}")
        return pd.DataFrame()


# Sidebar controls
st.sidebar.header("🎛️ Dashboard Controls")

# Tab selection
tab = st.sidebar.radio(
    "Select View",
    ["📊 Real-Time Monitoring", "⏰ Windowed Aggregates", "🤖 ML Anomaly Detection", "📈 Analytics"]
)

# Filters
locations = ["All", "Server Room", "Office Floor 3", "Warehouse", "Laboratory", "Manufacturing"]
sensor_types = ["All", "temperature", "humidity", "air_quality", "pressure", "co2"]

selected_location = st.sidebar.selectbox("Location Filter", locations)
selected_sensor = st.sidebar.selectbox("Sensor Type Filter", sensor_types)

update_interval = st.sidebar.slider("Update Interval (seconds)", min_value=3, max_value=30, value=10)
limit_records = st.sidebar.number_input("Records to Load", min_value=100, max_value=2000, value=500, step=100)

if st.sidebar.button("🔄 Refresh Now"):
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.caption(f"Last updated: {datetime.now().strftime('%H:%M:%S')}")

# Main content area
placeholder = st.empty()

# Auto-refresh loop
while True:
    with placeholder.container():
        
        if tab == "📊 Real-Time Monitoring":
            st.header("📊 Real-Time Sensor Readings")
            
            # Load data
            df_readings = load_recent_readings(
                selected_location if selected_location != "All" else None,
                selected_sensor if selected_sensor != "All" else None,
                int(limit_records)
            )
            
            if df_readings.empty:
                st.warning("⏳ Waiting for sensor data...")
                time.sleep(update_interval)
                continue
            
            # KPIs
            total_readings = len(df_readings)
            total_anomalies = df_readings["anomaly"].sum()
            anomaly_rate = (total_anomalies / total_readings * 100) if total_readings > 0 else 0.0
            unique_sensors = df_readings["sensor_id"].nunique()
            
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Total Readings", f"{total_readings:,}")
            col2.metric("Anomalies Detected", total_anomalies, delta=f"{anomaly_rate:.1f}%")
            col3.metric("Active Sensors", unique_sensors)
            col4.metric("Locations", df_readings["location"].nunique())
            
            # Recent readings table
            st.subheader("📋 Recent Readings (Top 15)")
            display_df = df_readings.head(15)[
                ["timestamp", "location", "sensor_type", "value", "unit", "anomaly"]
            ].copy()
            display_df["anomaly"] = display_df["anomaly"].map({True: "⚠️ Yes", False: "✓ No"})
            st.dataframe(display_df, use_container_width=True, hide_index=True)
            
            # Visualizations
            st.subheader("📈 Sensor Trends")
            
            col_left, col_right = st.columns(2)
            
            with col_left:
                # Time series by sensor type
                if not df_readings.empty:
                    fig_ts = px.line(
                        df_readings.sort_values("timestamp"),
                        x="timestamp",
                        y="value",
                        color="sensor_type",
                        title="Sensor Values Over Time",
                        labels={"value": "Reading Value", "timestamp": "Time"}
                    )
                    fig_ts.update_layout(height=400)
                    st.plotly_chart(fig_ts, use_container_width=True)
            
            with col_right:
                # Distribution by location
                location_counts = df_readings["location"].value_counts().reset_index()
                location_counts.columns = ["location", "count"]
                fig_loc = px.bar(
                    location_counts,
                    x="location",
                    y="count",
                    title="Readings by Location",
                    labels={"count": "Number of Readings"}
                )
                fig_loc.update_layout(height=400)
                st.plotly_chart(fig_loc, use_container_width=True)
            
            # Anomaly visualization
            if total_anomalies > 0:
                st.subheader("⚠️ Anomaly Distribution")
                anomaly_df = df_readings[df_readings["anomaly"] == True]
                
                col_a, col_b = st.columns(2)
                
                with col_a:
                    anomaly_by_type = anomaly_df["sensor_type"].value_counts().reset_index()
                    anomaly_by_type.columns = ["sensor_type", "count"]
                    fig_anom_type = px.pie(
                        anomaly_by_type,
                        values="count",
                        names="sensor_type",
                        title="Anomalies by Sensor Type"
                    )
                    st.plotly_chart(fig_anom_type, use_container_width=True)
                
                with col_b:
                    anomaly_by_loc = anomaly_df["location"].value_counts().reset_index()
                    anomaly_by_loc.columns = ["location", "count"]
                    fig_anom_loc = px.bar(
                        anomaly_by_loc,
                        x="location",
                        y="count",
                        title="Anomalies by Location",
                        color="count",
                        color_continuous_scale="Reds"
                    )
                    st.plotly_chart(fig_anom_loc, use_container_width=True)
        
        elif tab == "⏰ Windowed Aggregates":
            st.header("⏰ Stream Processing: Windowed Aggregations")
            st.caption("Real-time aggregations computed by the stream processor (1-minute windows)")
            
            # Load aggregates
            df_agg = load_aggregates(hours_back=2)
            
            if df_agg.empty:
                st.warning("⏳ Waiting for aggregated data from stream processor...")
                time.sleep(update_interval)
                continue
            
            # KPIs
            total_windows = len(df_agg)
            total_anomalies_in_windows = df_agg["anomaly_count"].sum()
            avg_readings_per_window = df_agg["count_readings"].mean()
            
            col1, col2, col3 = st.columns(3)
            col1.metric("Windows Processed", total_windows)
            col2.metric("Total Anomalies", int(total_anomalies_in_windows))
            col3.metric("Avg Readings/Window", f"{avg_readings_per_window:.1f}")
            
            # Recent aggregates table
            st.subheader("📊 Recent Windows (Top 10)")
            display_agg = df_agg.head(10)[
                ["window_start", "location", "sensor_type", "avg_value", 
                 "min_value", "max_value", "count_readings", "anomaly_count"]
            ].copy()
            st.dataframe(display_agg, use_container_width=True, hide_index=True)
            
            # Visualizations
            st.subheader("📈 Aggregate Trends")
            
            # Average values over time
            for sensor_type in df_agg["sensor_type"].unique():
                df_sensor = df_agg[df_agg["sensor_type"] == sensor_type].sort_values("window_start")
                
                fig = go.Figure()
                
                # Add average line
                fig.add_trace(go.Scatter(
                    x=df_sensor["window_start"],
                    y=df_sensor["avg_value"],
                    mode='lines+markers',
                    name='Average',
                    line=dict(color='blue', width=2)
                ))
                
                # Add min/max range
                fig.add_trace(go.Scatter(
                    x=df_sensor["window_start"],
                    y=df_sensor["max_value"],
                    mode='lines',
                    name='Max',
                    line=dict(color='lightgray', width=1),
                    showlegend=False
                ))
                
                fig.add_trace(go.Scatter(
                    x=df_sensor["window_start"],
                    y=df_sensor["min_value"],
                    mode='lines',
                    name='Min',
                    line=dict(color='lightgray', width=1),
                    fill='tonexty',
                    fillcolor='rgba(200, 200, 200, 0.3)',
                    showlegend=False
                ))
                
                fig.update_layout(
                    title=f"{sensor_type.title()} - Windowed Averages",
                    xaxis_title="Window Start Time",
                    yaxis_title="Value",
                    height=300
                )
                
                st.plotly_chart(fig, use_container_width=True)
        
        elif tab == "🤖 ML Anomaly Detection":
            st.header("🤖 Machine Learning Anomaly Detection")
            st.caption("Advanced anomaly detection using Isolation Forest")
            
            # Load ML predictions
            df_ml = load_ml_predictions(hours_back=1)
            
            if df_ml.empty:
                st.warning("⏳ Waiting for ML predictions...")
                time.sleep(update_interval)
                continue
            
            # KPIs
            total_predictions = len(df_ml)
            ml_anomalies = df_ml["is_anomaly"].sum()
            rule_anomalies = df_ml["rule_based_anomaly"].sum()
            ml_rate = (ml_anomalies / total_predictions * 100) if total_predictions > 0 else 0.0
            
            # Agreement between ML and rule-based
            agreement = ((df_ml["is_anomaly"] == df_ml["rule_based_anomaly"]).sum() / 
                        total_predictions * 100) if total_predictions > 0 else 0.0
            
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Total Predictions", f"{total_predictions:,}")
            col2.metric("ML Anomalies", ml_anomalies, delta=f"{ml_rate:.1f}%")
            col3.metric("Rule-based Anomalies", rule_anomalies)
            col4.metric("Detection Agreement", f"{agreement:.1f}%")
            
            # Recent ML anomalies
            st.subheader("🚨 Recent ML-Detected Anomalies")
            ml_anomalies_df = df_ml[df_ml["is_anomaly"] == True].head(10)
            
            if not ml_anomalies_df.empty:
                display_ml = ml_anomalies_df[
                    ["timestamp", "location", "sensor_type", "value", 
                     "anomaly_score", "rule_based_anomaly"]
                ].copy()
                display_ml["rule_based_anomaly"] = display_ml["rule_based_anomaly"].map(
                    {True: "✓", False: "✗"}
                )
                display_ml.columns = [
                    "Timestamp", "Location", "Sensor Type", "Value", 
                    "Anomaly Score", "Rule-based?"
                ]
                st.dataframe(display_ml, use_container_width=True, hide_index=True)
            else:
                st.info("No ML anomalies detected recently")
            
            # Comparison visualization
            st.subheader("📊 Detection Method Comparison")
            
            col_a, col_b = st.columns(2)
            
            with col_a:
                # Venn diagram data
                both = ((df_ml["is_anomaly"] == True) & (df_ml["rule_based_anomaly"] == True)).sum()
                only_ml = ((df_ml["is_anomaly"] == True) & (df_ml["rule_based_anomaly"] == False)).sum()
                only_rule = ((df_ml["is_anomaly"] == False) & (df_ml["rule_based_anomaly"] == True)).sum()
                
                comparison_data = pd.DataFrame({
                    "Category": ["Both Methods", "ML Only", "Rule-based Only"],
                    "Count": [both, only_ml, only_rule]
                })
                
                fig_comp = px.bar(
                    comparison_data,
                    x="Category",
                    y="Count",
                    title="Anomaly Detection Comparison",
                    color="Category",
                    color_discrete_map={
                        "Both Methods": "green",
                        "ML Only": "blue",
                        "Rule-based Only": "orange"
                    }
                )
                st.plotly_chart(fig_comp, use_container_width=True)
            
            with col_b:
                # Anomaly score distribution
                fig_score = px.histogram(
                    df_ml,
                    x="anomaly_score",
                    color="is_anomaly",
                    title="Anomaly Score Distribution",
                    labels={"anomaly_score": "Anomaly Score", "is_anomaly": "Is Anomaly"},
                    nbins=30
                )
                st.plotly_chart(fig_score, use_container_width=True)
        
        elif tab == "📈 Analytics":
            st.header("📈 Advanced Analytics")
            
            # Load all data
            df_readings = load_recent_readings(limit=1000)
            df_agg = load_aggregates(hours_back=6)
            df_ml = load_ml_predictions(hours_back=2)
            
            if df_readings.empty:
                st.warning("⏳ Waiting for data...")
                time.sleep(update_interval)
                continue
            
            # Correlation heatmap
            st.subheader("🔗 Sensor Correlations")
            
            # Pivot data for correlation
            pivot_data = df_readings.pivot_table(
                index="timestamp",
                columns="sensor_type",
                values="value",
                aggfunc="mean"
            )
            
            if not pivot_data.empty:
                corr_matrix = pivot_data.corr()
                
                fig_corr = px.imshow(
                    corr_matrix,
                    labels=dict(color="Correlation"),
                    x=corr_matrix.columns,
                    y=corr_matrix.columns,
                    color_continuous_scale="RdBu_r",
                    aspect="auto",
                    title="Sensor Type Correlations"
                )
                fig_corr.update_layout(height=400)
                st.plotly_chart(fig_corr, use_container_width=True)
            
            # Sensor statistics by location
            st.subheader("📊 Statistics by Location")
            
            stats_by_location = df_readings.groupby(["location", "sensor_type"]).agg({
                "value": ["mean", "std", "min", "max"],
                "anomaly": "sum"
            }).round(2)
            stats_by_location.columns = ["Mean", "Std Dev", "Min", "Max", "Anomalies"]
            stats_by_location = stats_by_location.reset_index()
            
            st.dataframe(stats_by_location, use_container_width=True, hide_index=True)
        
        st.markdown("---")
        st.caption(f"🔄 Auto-refresh: {update_interval}s | "
                  f"Next update: {datetime.now() + timedelta(seconds=update_interval)}")
    
    time.sleep(update_interval)
