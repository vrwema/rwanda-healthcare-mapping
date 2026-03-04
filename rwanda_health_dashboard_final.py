"""
Rwanda Healthcare Dashboard - Final Version
Complete integration of Referral Network Map and Facility Performance Analysis
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import json
import random
from typing import Optional, Dict, List

# Page configuration
st.set_page_config(
    page_title="Rwanda Healthcare Analytics Dashboard",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main > div {
        padding-top: 1rem;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        padding-left: 20px;
        padding-right: 20px;
    }
    div[data-testid="metric-container"] {
        background-color: rgba(28, 131, 225, 0.1);
        border: 1px solid rgba(28, 131, 225, 0.1);
        padding: 5% 5% 5% 10%;
        border-radius: 5px;
        overflow-wrap: break-word;
    }
</style>
""", unsafe_allow_html=True)

# Title
st.markdown("# 🏥 Rwanda Healthcare Analytics Dashboard")
st.markdown("**Comprehensive analysis of referral networks and facility performance across all 46 sub-districts**")

# Color schemes matching your notebook
COLOR_SCHEMES = {
    'facility_performance': {
        'hospital': '#4169E1',        # Blue for hospitals
        'health_center': '#FFD700',   # Gold for health centers
        'mhc': '#FFD700',             # Gold for MHC
        'outperformer': '#FF0000'     # Red for HC/MHC outperforming hospitals
    }
}

# Performance metrics
PERFORMANCE_METRICS = [
    'ANC',
    'OPD_new', 
    'OPD_old',
    'Deliveries',
    'Labor_referrals',
    'Obstetric_complication_referrals'
]

METRIC_DESCRIPTIONS = {
    'ANC': 'Antenatal Care',
    'OPD_new': 'New OPD Cases',
    'OPD_old': 'Old OPD Cases', 
    'Deliveries': 'Deliveries',
    'Labor_referrals': 'Labor Referrals',
    'Obstetric_complication_referrals': 'Obstetric Complication Referrals'
}

@st.cache_data
def load_sample_data():
    """Generate comprehensive sample data matching notebook structure"""
    np.random.seed(42)
    random.seed(42)
    
    # 46 sub-districts
    sub_districts = [f"Sub-District-{i+1}" for i in range(46)]
    districts = ['Kigali', 'Eastern', 'Western', 'Northern', 'Southern']
    
    # Generate facility performance data
    facilities = []
    for sub_district in sub_districts:
        # Add 1-2 hospitals per sub-district
        n_hospitals = np.random.randint(1, 3)
        for i in range(n_hospitals):
            facilities.append({
                'name': f'{sub_district} Hospital {i+1}',
                'sub_district': sub_district,
                'district': np.random.choice(districts),
                'facility_category': np.random.choice(['District Hospital', 'Provincial Hospital', 'L2TH']),
                'ANC': np.random.randint(800, 1500),
                'OPD_new': np.random.randint(2000, 5000),
                'OPD_old': np.random.randint(1500, 4000),
                'Deliveries': np.random.randint(300, 800),
                'Labor_referrals': np.random.randint(10, 50),
                'Obstetric_complication_referrals': np.random.randint(5, 30)
            })
        
        # Add 3-5 health centers
        n_hc = np.random.randint(3, 6)
        for i in range(n_hc):
            # 15% chance to outperform hospitals
            outperformer = np.random.random() < 0.15
            
            if outperformer:
                # These will show in RED
                facilities.append({
                    'name': f'{sub_district} HC {i+1}',
                    'sub_district': sub_district,
                    'district': np.random.choice(districts),
                    'facility_category': np.random.choice(['Health Center', 'Medicalized Health Center']),
                    'ANC': np.random.randint(1200, 1800),
                    'OPD_new': np.random.randint(3500, 6000),
                    'OPD_old': np.random.randint(2500, 4500),
                    'Deliveries': np.random.randint(400, 900),
                    'Labor_referrals': np.random.randint(30, 60),
                    'Obstetric_complication_referrals': np.random.randint(20, 40)
                })
            else:
                facilities.append({
                    'name': f'{sub_district} HC {i+1}',
                    'sub_district': sub_district,
                    'district': np.random.choice(districts),
                    'facility_category': np.random.choice(['Health Center', 'Medicalized Health Center']),
                    'ANC': np.random.randint(200, 700),
                    'OPD_new': np.random.randint(500, 1800),
                    'OPD_old': np.random.randint(400, 1400),
                    'Deliveries': np.random.randint(50, 250),
                    'Labor_referrals': np.random.randint(2, 15),
                    'Obstetric_complication_referrals': np.random.randint(1, 10)
                })
    
    facility_summary = pd.DataFrame(facilities)
    
    # Generate map data for health centers
    n_hc = 150
    hc_points = pd.DataFrame({
        'HC_Name': [f'Health Center {i+1}' for i in range(n_hc)],
        'District': np.random.choice(districts, n_hc),
        'Hosp_name': np.random.choice(['CHUK', 'CHUB', 'RMH', 'KFH'], n_hc),
        'Dist_hosp': np.random.uniform(10, 100, n_hc),
        'Travel_Time_RealTime_Hours': np.random.uniform(0.5, 4.5, n_hc),
        'Travel_Time_Ambulance_Hours': np.random.uniform(0.7, 5.0, n_hc),
        'Travel_Time_Private_Hours': np.random.uniform(0.6, 4.8, n_hc),
        'latitude': np.random.uniform(-2.5, -1.0, n_hc),
        'longitude': np.random.uniform(28.8, 30.5, n_hc)
    })
    
    # Hospital points data
    hosp_points = pd.DataFrame({
        'Hospital Name': ['CHUK', 'CHUB', 'RMH', 'KFH', 'Kibagabaga Hospital', 'Ruhengeri Hospital'],
        'Refer to': ['CHUK', 'CHUB', 'RMH', 'CHUK', 'CHUK', 'CHUB'],
        'Distance to NTH': [0, 0, 0, 0, 25, 67],
        'Travel_Time_RealTime_Hours': [0, 0, 0, 0, 0.5, 1.2],
        'Travel_Time_Simple_Hours': [0, 0, 0, 0, 0.4, 1.0],
        'latitude': [-1.9533, -2.3497, -1.8567, -1.9403, -1.9603, -1.6203],
        'longitude': [30.0605, 28.8997, 29.7477, 30.1205, 30.0805, 29.6405]
    })
    
    # National Referral Hospitals
    nrh_gdf = pd.DataFrame({
        'Hospital Name': ['CHUK', 'CHUB', 'RMH'],
        'latitude': [-1.9533, -2.3497, -1.8567],
        'longitude': [30.0605, 28.8997, 29.7477]
    })
    
    # Health posts
    n_hp = 50
    hp_gdf = pd.DataFrame({
        'Facility Name': [f'Health Post {i+1}' for i in range(n_hp)],
        'latitude': np.random.uniform(-2.5, -1.0, n_hp),
        'longitude': np.random.uniform(28.8, 30.5, n_hp)
    })
    
    return facility_summary, hc_points, hosp_points, nrh_gdf, hp_gdf, sub_districts

def create_enhanced_referral_map(hc_points, hosp_points, nrh_gdf, hp_gdf, show_roads=True, show_health_posts=True):
    """
    Create the exact map as in your notebook with all components
    """
    
    # Generate random colors for hospitals (like in notebook)
    def generate_color():
        return tuple(random.randint(0, 255) for _ in range(3))
    
    hospitals = hosp_points['Hospital Name'].unique()
    hospital_colors_dict = {hospital: generate_color() for hospital in hospitals}
    hospital_colors_dict_hex = {
        hospital: '#%02x%02x%02x' % color for hospital, color in hospital_colors_dict.items()
    }
    
    # Get Rwanda centroid (approximate)
    rwanda_centroid_lat = -1.9403
    rwanda_centroid_lon = 29.8739
    
    # Initialize figure
    fig = go.Figure()
    
    # Add district boundaries (simplified outline)
    district_outline = go.Scattermapbox(
        lat=[-1.0, -1.0, -2.6, -2.6, -1.0],
        lon=[28.8, 30.9, 30.9, 28.8, 28.8],
        mode='lines',
        line=dict(width=0.5, color='darkgray'),
        hoverinfo='skip',
        showlegend=False
    )
    fig.add_trace(district_outline)
    
    # Add health posts if enabled
    if show_health_posts:
        first_hp = True
        for _, row in hp_gdf.iterrows():
            hover_text = (
                f"<b>Health Post:</b> {row['Facility Name']}<br>"
                f"<b>Type:</b> Primary Health Facility<br>"
                f"<b>Location:</b> {row['latitude']:.4f}, {row['longitude']:.4f}"
            )
            
            hp_trace = go.Scattermapbox(
                lat=[row['latitude']],
                lon=[row['longitude']],
                mode='markers',
                marker=dict(size=3, symbol='circle', color='gray'),
                text=hover_text,
                hoverinfo='text',
                name='Health Posts',
                legendgroup='health_posts',
                showlegend=first_hp,
            )
            fig.add_trace(hp_trace)
            first_hp = False
    
    # Add referral roads if enabled
    if show_roads:
        first_road = True
        for _, hc_row in hc_points.iterrows():
            hosp_row = hosp_points[hosp_points['Hospital Name'] == hc_row['Hosp_name']]
            if not hosp_row.empty:
                color = hospital_colors_dict_hex.get(hc_row['Hosp_name'], 'gray')
                
                fig.add_trace(go.Scattermapbox(
                    lat=[hc_row['latitude'], hosp_row.iloc[0]['latitude']],
                    lon=[hc_row['longitude'], hosp_row.iloc[0]['longitude']],
                    mode='lines',
                    line=dict(width=1, color=color),
                    hoverinfo='skip',
                    name='HC to Hospital Roads',
                    legendgroup='hc_to_hosp_roads',
                    showlegend=first_road
                ))
                first_road = False
    
    # Add hospitals with enhanced hover
    for hospital, color in hospital_colors_dict_hex.items():
        hospital_data = hosp_points[hosp_points['Hospital Name'] == hospital]
        
        hover_texts = []
        for _, row in hospital_data.iterrows():
            realtime_text = f"{row['Travel_Time_RealTime_Hours']:.2f} hours" if pd.notna(row.get('Travel_Time_RealTime_Hours')) else "Not calculated"
            distance_text = f"{row.get('Distance to NTH', 0):.0f} km" if pd.notna(row.get('Distance to NTH')) else "N/A"
            
            hover_info = (
                f"<b>Hospital:</b> {row['Hospital Name']}<br>"
                f"<b>Type:</b> District/L2TH Hospital<br>"
                f"<b>Refers to:</b> {row.get('Refer to', 'N/A')}<br>"
                f"<b>Distance to NTH:</b> {distance_text}<br>"
                f"<b>Real-time travel time:</b> {realtime_text}"
            )
            hover_texts.append(hover_info)
        
        if not hospital_data.empty:
            hospital_trace = go.Scattermapbox(
                lat=hospital_data['latitude'],
                lon=hospital_data['longitude'],
                mode='markers',
                marker=dict(size=10, symbol='circle', color=color),
                text=hover_texts,
                hoverinfo='text',
                name=hospital,
                showlegend=False,
            )
            fig.add_trace(hospital_trace)
    
    # Add health centers with enhanced hover
    first_hc = True
    for _, row in hc_points.iterrows():
        hospital = row.get('Hosp_name', 'Unknown')
        distance = row.get('Dist_hosp', 0)
        color = hospital_colors_dict_hex.get(hospital, 'gray')
        
        ambulance_time = row.get('Travel_Time_Ambulance_Hours', None)
        private_time = row.get('Travel_Time_Private_Hours', None)
        realtime_time = row.get('Travel_Time_RealTime_Hours', None)
        
        ambulance_text = f"{ambulance_time:.1f} hours" if pd.notna(ambulance_time) else "Not calculated"
        private_text = f"{private_time:.1f} hours" if pd.notna(private_time) else "Not calculated"
        realtime_text = f"{realtime_time:.2f} hours" if pd.notna(realtime_time) else "Not calculated"
        
        hover_text = (
            f"<b>Health Center:</b> {row['HC_Name']}<br>"
            f"<b>Referred Hospital:</b> {hospital}<br>"
            f"<b>Distance to Hospital:</b> {distance:.1f} km<br>"
            f"<b>Travel Times to Hospital:</b><br>"
            f"• Estimated (Ambulance): {ambulance_text}<br>"
            f"• Estimated (Private car): {private_text}<br>"
            f"• Real-time (Mapbox/OSRM): {realtime_text}<br>"
            f"<b>Type:</b> Health Center (Secondary Care)"
        )
        
        hc_trace = go.Scattermapbox(
            lat=[row['latitude']],
            lon=[row['longitude']],
            mode='markers',
            marker=dict(size=7, symbol='circle', color=color),
            text=hover_text,
            hoverinfo='text',
            name='Health Centers',
            legendgroup='health_centers',
            showlegend=first_hc,
        )
        fig.add_trace(hc_trace)
        first_hc = False
    
    # Add national referral hospitals
    first_nrh = True
    for _, row in nrh_gdf.iterrows():
        hover_text = (
            f"<b>National Referral Hospital:</b> {row['Hospital Name']}<br>"
            f"<b>Type:</b> Tertiary Care (National Level)<br>"
            f"<b>Location:</b> {row['latitude']:.4f}, {row['longitude']:.4f}<br>"
            f"<b>Services:</b> Specialized care, Complex procedures"
        )
        
        nrh_trace = go.Scattermapbox(
            lat=[row['latitude']],
            lon=[row['longitude']],
            mode='markers',
            marker=dict(size=20, symbol='circle', color='gold'),
            text=hover_text,
            hoverinfo='text',
            name='National Referral Hospitals',
            legendgroup='national_referral_hospitals',
            showlegend=first_nrh,
        )
        fig.add_trace(nrh_trace)
        first_nrh = False
    
    # Update layout (exactly like notebook)
    fig.update_layout(
        title_text='Rwanda Healthcare Referral Network with Real-Time Travel Times',
        title_x=0.5,
        mapbox_style="carto-darkmatter",
        width=1200,
        height=800,
        mapbox_zoom=8,
        mapbox_center={"lat": rwanda_centroid_lat, "lon": rwanda_centroid_lon},
        margin={"r": 10, "t": 50, "l": 10, "b": 10},
        coloraxis_showscale=False,
        plot_bgcolor="black",
        paper_bgcolor="black",
        legend=dict(
            orientation="h",
            yanchor="top",
            xanchor="center",
            x=0.5,
            y=1.05,
            font=dict(color="white", size=10),
            bgcolor="black",
            bordercolor="white",
            borderwidth=0.4,
            traceorder="normal"
        ),
        legend_tracegroupgap=10,
    )
    
    return fig

def analyze_facility_performance(facility_df, sub_district, metric):
    """
    Analyze facility performance exactly like in notebook
    """
    # Filter for sub-district
    sub_df = facility_df[facility_df['sub_district'] == sub_district].copy()
    
    if len(sub_df) == 0:
        return None, []
    
    # Sort by metric value
    sub_df_sorted = sub_df.sort_values(metric, ascending=False).reset_index(drop=True)
    
    # Calculate average
    sub_avg = sub_df_sorted[metric].mean()
    
    # Identify hospitals
    hospitals = sub_df_sorted[sub_df_sorted['facility_category'].isin([
        'District Hospital', 'Provincial Hospital', 'L2TH', 'Teaching Hospital'
    ])]
    
    # Find HC/MHC that outperform hospitals
    outperformers = []
    if len(hospitals) > 0:
        min_hospital_value = hospitals[metric].min()
        hc_mhc = sub_df_sorted[sub_df_sorted['facility_category'].isin([
            'Health Center', 'Medicalized Health Center'
        ])]
        
        for _, facility in hc_mhc.iterrows():
            if facility[metric] > min_hospital_value:
                outperformers.append(facility['name'])
    
    # Create colors (RED for outperformers, BLUE for hospitals, GOLD for HC/MHC)
    colors = []
    for _, facility in sub_df_sorted.iterrows():
        if facility['name'] in outperformers:
            colors.append('#FF0000')  # RED
        elif facility['facility_category'] in ['District Hospital', 'Provincial Hospital', 'L2TH']:
            colors.append('#4169E1')  # BLUE
        else:
            colors.append('#FFD700')  # GOLD
    
    # Create plotly figure
    fig = go.Figure()
    
    # Add bars
    fig.add_trace(go.Bar(
        x=sub_df_sorted['name'],
        y=sub_df_sorted[metric],
        marker_color=colors,
        text=sub_df_sorted[metric],
        textposition='outside',
        hovertemplate='<b>%{x}</b><br>' +
                      f'{METRIC_DESCRIPTIONS[metric]}: %{{y}}<br>' +
                      '<extra></extra>'
    ))
    
    # Add average line
    fig.add_hline(
        y=sub_avg,
        line_dash="dash",
        line_color="white",
        annotation_text=f"Average: {sub_avg:.0f}",
        annotation_position="right"
    )
    
    # Update layout to match notebook style
    fig.update_layout(
        title={
            'text': f"{METRIC_DESCRIPTIONS[metric]} by Facility ({sub_district})",
            'font': {'size': 22, 'color': 'white'}
        },
        xaxis_title="",
        yaxis_title=f"Number of {METRIC_DESCRIPTIONS[metric]}",
        template="plotly_dark",
        height=500,
        showlegend=False,
        xaxis={'tickangle': -45, 'tickfont': {'color': 'white'}},
        yaxis={'tickfont': {'color': 'white'}},
        plot_bgcolor='black',
        paper_bgcolor='black',
        font={'color': 'white'}
    )
    
    return fig, outperformers

# Main app
def main():
    # Load data
    with st.spinner("Loading data..."):
        facility_summary, hc_points, hosp_points, nrh_gdf, hp_gdf, sub_districts = load_sample_data()
    
    # Sidebar
    st.sidebar.header("🔍 Global Filters")
    
    selected_districts = st.sidebar.multiselect(
        "Filter by District",
        options=sorted(facility_summary['district'].unique()),
        default=[]
    )
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("### Map Options")
    show_roads = st.sidebar.checkbox("Show Referral Roads", value=True)
    show_health_posts = st.sidebar.checkbox("Show Health Posts", value=True)
    
    # Create tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "📍 Referral Network Map",
        "📊 Facility Performance Analysis", 
        "⚠️ Alerts Dashboard",
        "📈 Statistics"
    ])
    
    # TAB 1: REFERRAL NETWORK MAP
    with tab1:
        st.markdown("### Healthcare Referral Network")
        
        # Display map
        map_fig = create_enhanced_referral_map(
            hc_points, hosp_points, nrh_gdf, hp_gdf,
            show_roads=show_roads,
            show_health_posts=show_health_posts
        )
        st.plotly_chart(map_fig, use_container_width=True)
        
        # Metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("🏥 Health Centers", len(hc_points))
        with col2:
            avg_dist = hc_points['Dist_hosp'].mean()
            st.metric("📏 Avg Distance", f"{avg_dist:.1f} km")
        with col3:
            avg_time = hc_points['Travel_Time_RealTime_Hours'].mean()
            st.metric("⏱️ Avg Travel Time", f"{avg_time:.1f} hrs")
        with col4:
            critical = len(hc_points[hc_points['Travel_Time_RealTime_Hours'] > 3])
            st.metric("🚨 Critical Access", critical)
    
    # TAB 2: FACILITY PERFORMANCE
    with tab2:
        st.markdown("### Facility Performance Analysis")
        st.markdown("""
        **Color Coding:**
        - 🔴 **RED** = HC/MHC outperforming hospitals
        - 🔵 **BLUE** = Hospitals
        - 🟡 **GOLD/YELLOW** = Health Centers and Medicalized Health Centers
        """)
        
        col1, col2 = st.columns([1, 3])
        
        with col1:
            # Sub-district selector
            selected_sub_district = st.selectbox(
                "Select Sub-District",
                options=sorted(sub_districts),
                help="Choose from 46 sub-districts"
            )
            
            # Metric selector
            selected_metric = st.selectbox(
                "Select Metric",
                options=PERFORMANCE_METRICS,
                format_func=lambda x: f"{x} ({METRIC_DESCRIPTIONS[x]})"
            )
            
            # Info about selected sub-district
            sub_df = facility_summary[facility_summary['sub_district'] == selected_sub_district]
            if not sub_df.empty:
                st.markdown("#### Sub-District Info")
                n_hospitals = len(sub_df[sub_df['facility_category'].str.contains('Hospital')])
                n_hc = len(sub_df[sub_df['facility_category'].str.contains('Health Center|Medicalized')])
                st.write(f"Hospitals: **{n_hospitals}**")
                st.write(f"Health Centers: **{n_hc}**")
                st.write(f"Total Facilities: **{len(sub_df)}**")
        
        with col2:
            # Performance chart
            perf_fig, outperformers = analyze_facility_performance(
                facility_summary, selected_sub_district, selected_metric
            )
            
            if perf_fig:
                st.plotly_chart(perf_fig, use_container_width=True)
                
                # Alert if there are outperformers
                if outperformers:
                    st.error(f"""
                    ⚠️ **ALERT for {selected_sub_district}:**
                    
                    {len(outperformers)} HC/MHC are outperforming hospitals in {METRIC_DESCRIPTIONS[selected_metric]}:
                    """)
                    for facility in outperformers:
                        facility_data = facility_summary[facility_summary['name'] == facility].iloc[0]
                        value = facility_data[selected_metric]
                        st.write(f"🔴 **{facility}**: {value:.0f}")
            else:
                st.info("No data available for selected sub-district")
        
        # Generate all reports button
        st.markdown("---")
        if st.button("📊 Generate Analysis for All 46 Sub-Districts"):
            with st.spinner("Generating comprehensive analysis..."):
                st.success("Analysis would be generated for all 46 sub-districts across all 6 metrics")
                st.info("This would create 276 charts (46 sub-districts × 6 metrics)")
    
    # TAB 3: ALERTS DASHBOARD
    with tab3:
        st.markdown("### ⚠️ Comprehensive Alerts Dashboard")
        
        # Find all outperformers
        all_alerts = []
        for sub_district in sub_districts:
            sub_df = facility_summary[facility_summary['sub_district'] == sub_district]
            hospitals = sub_df[sub_df['facility_category'].str.contains('Hospital')]
            hc_mhc = sub_df[sub_df['facility_category'].str.contains('Health Center|Medicalized')]
            
            if len(hospitals) > 0 and len(hc_mhc) > 0:
                for metric in PERFORMANCE_METRICS:
                    min_hospital = hospitals[metric].min()
                    outperforming = hc_mhc[hc_mhc[metric] > min_hospital]
                    
                    for _, facility in outperforming.iterrows():
                        all_alerts.append({
                            'Sub-District': sub_district,
                            'Facility': facility['name'],
                            'Category': facility['facility_category'],
                            'Metric': metric,
                            'Value': facility[metric],
                            'Min Hospital Value': min_hospital,
                            'Excess': facility[metric] - min_hospital,
                            '% Above': ((facility[metric] - min_hospital) / min_hospital * 100)
                        })
        
        alerts_df = pd.DataFrame(all_alerts)
        
        if not alerts_df.empty:
            # Summary metrics
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Alerts", len(alerts_df))
            with col2:
                st.metric("Sub-Districts Affected", alerts_df['Sub-District'].nunique())
            with col3:
                st.metric("Facilities Involved", alerts_df['Facility'].nunique())
            with col4:
                avg_excess = alerts_df['% Above'].mean()
                st.metric("Avg % Above Hospital", f"{avg_excess:.1f}%")
            
            # Filter options
            st.markdown("---")
            col1, col2 = st.columns(2)
            
            with col1:
                metric_filter = st.selectbox(
                    "Filter by Metric",
                    options=['All'] + list(PERFORMANCE_METRICS),
                    format_func=lambda x: x if x == 'All' else METRIC_DESCRIPTIONS[x]
                )
            
            with col2:
                threshold = st.slider(
                    "Minimum % Above Hospital",
                    min_value=0,
                    max_value=100,
                    value=20,
                    step=10
                )
            
            # Apply filters
            filtered_alerts = alerts_df.copy()
            if metric_filter != 'All':
                filtered_alerts = filtered_alerts[filtered_alerts['Metric'] == metric_filter]
            filtered_alerts = filtered_alerts[filtered_alerts['% Above'] >= threshold]
            
            # Display
            if not filtered_alerts.empty:
                st.markdown(f"### Showing {len(filtered_alerts)} Alerts")
                
                # Chart
                top_20 = filtered_alerts.nlargest(20, '% Above')
                fig = px.bar(
                    top_20,
                    x='Facility',
                    y='% Above',
                    color='Metric',
                    title="Top 20 HC/MHC Outperforming Hospitals",
                    template="plotly_dark",
                    hover_data=['Sub-District', 'Value', 'Min Hospital Value']
                )
                fig.update_layout(xaxis_tickangle=-45)
                st.plotly_chart(fig, use_container_width=True)
                
                # Table
                st.markdown("### Alert Details")
                display_cols = ['Sub-District', 'Facility', 'Metric', 'Value', 'Min Hospital Value', '% Above']
                display_df = filtered_alerts[display_cols].copy()
                display_df['% Above'] = display_df['% Above'].round(1)
                st.dataframe(display_df, use_container_width=True, height=400)
        else:
            st.success("✅ No alerts found - All hospitals are performing above HC/MHC levels")
    
    # TAB 4: STATISTICS
    with tab4:
        st.markdown("### 📈 Statistical Overview")
        
        # Overall statistics
        st.markdown("#### Performance Statistics Across All Facilities")
        stats = facility_summary[PERFORMANCE_METRICS].describe().round(1)
        st.dataframe(stats, use_container_width=True)
        
        # Distributions
        st.markdown("---")
        st.markdown("#### Metric Distributions")
        
        col1, col2 = st.columns(2)
        
        with col1:
            metric1 = st.selectbox(
                "Select first metric for distribution",
                options=PERFORMANCE_METRICS,
                format_func=lambda x: METRIC_DESCRIPTIONS[x]
            )
            
            fig1 = px.histogram(
                facility_summary,
                x=metric1,
                color='facility_category',
                title=f"Distribution of {METRIC_DESCRIPTIONS[metric1]}",
                template="plotly_dark"
            )
            st.plotly_chart(fig1, use_container_width=True)
        
        with col2:
            metric2 = st.selectbox(
                "Select second metric for comparison",
                options=PERFORMANCE_METRICS,
                format_func=lambda x: METRIC_DESCRIPTIONS[x],
                index=1
            )
            
            fig2 = px.box(
                facility_summary,
                y=metric2,
                x='facility_category',
                title=f"{METRIC_DESCRIPTIONS[metric2]} by Facility Type",
                template="plotly_dark"
            )
            st.plotly_chart(fig2, use_container_width=True)
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; padding: 20px'>
        <p><b>Rwanda Healthcare Analytics Dashboard</b></p>
        <p>Comprehensive analysis of referral networks and facility performance</p>
        <p style='font-size: 0.9em; color: gray'>All 46 sub-districts | 6 performance metrics | Real-time travel analysis</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()