"""
Test Streamlit App - Rwanda Healthcare Referral Network Map
This version creates sample data to demonstrate the functionality
"""

import streamlit as st
import pandas as pd
import numpy as np
import geopandas as gpd
from shapely.geometry import Point, LineString
import plotly.graph_objects as go

# Page configuration
st.set_page_config(
    page_title="Rwanda Healthcare Referral Network - Demo",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Title
st.title("🏥 Rwanda Healthcare Referral Network Analysis - Demo")
st.info("This is a demonstration using sample data. Connect your actual data files for full functionality.")

# Create sample data for demonstration
@st.cache_data
def create_sample_data():
    """Create sample data to demonstrate the map functionality"""
    
    # Sample health centers
    np.random.seed(42)
    n_hc = 50
    hc_data = {
        'HC_Name': [f'Health Center {i+1}' for i in range(n_hc)],
        'District': np.random.choice(['Kigali', 'Eastern', 'Western', 'Northern', 'Southern'], n_hc),
        'Hosp_name': np.random.choice(['CHUK', 'CHUB', 'RMH', 'District Hospital A', 'District Hospital B'], n_hc),
        'Dist_hosp': np.random.uniform(10, 100, n_hc),
        'Travel_Time_RealTime_Hours': np.random.uniform(0.5, 4.5, n_hc),
        'latitude': np.random.uniform(-2.5, -1.0, n_hc),
        'longitude': np.random.uniform(28.8, 30.5, n_hc)
    }
    hc_df = pd.DataFrame(hc_data)
    geometry = [Point(xy) for xy in zip(hc_df.longitude, hc_df.latitude)]
    hc_gdf = gpd.GeoDataFrame(hc_df, geometry=geometry, crs='EPSG:4326')
    
    # Add access gap severity based on travel time
    hc_gdf['access_gap_severity'] = pd.cut(
        hc_gdf['Travel_Time_RealTime_Hours'],
        bins=[0, 1.5, 2.0, 3.0, 10],
        labels=['low', 'moderate', 'high', 'critical']
    )
    
    # Sample hospitals
    hosp_data = {
        'Hospital Name': ['CHUK', 'CHUB', 'RMH', 'District Hospital A', 'District Hospital B'],
        'Refer to': ['National', 'National', 'National', 'CHUK', 'CHUB'],
        'Distance to NTH': [0, 0, 0, 45, 67],
        'latitude': [-1.95, -2.35, -1.85, -2.1, -1.7],
        'longitude': [30.06, 28.9, 29.7, 29.3, 30.2]
    }
    hosp_df = pd.DataFrame(hosp_data)
    geometry = [Point(xy) for xy in zip(hosp_df.longitude, hosp_df.latitude)]
    hosp_gdf = gpd.GeoDataFrame(hosp_df, geometry=geometry, crs='EPSG:4326')
    
    # Sample health posts
    n_hp = 30
    hp_data = {
        'Facility Name': [f'Health Post {i+1}' for i in range(n_hp)],
        'latitude': np.random.uniform(-2.5, -1.0, n_hp),
        'longitude': np.random.uniform(28.8, 30.5, n_hp)
    }
    hp_df = pd.DataFrame(hp_data)
    geometry = [Point(xy) for xy in zip(hp_df.longitude, hp_df.latitude)]
    hp_gdf = gpd.GeoDataFrame(hp_df, geometry=geometry, crs='EPSG:4326')
    
    return hc_gdf, hosp_gdf, hp_gdf

# Color schemes
COLOR_SCHEMES = {
    'hospitals': {
        'CHUK': '#e74c3c',
        'CHUB': '#3498db',
        'RMH': '#2ecc71',
        'District Hospital A': '#f39c12',
        'District Hospital B': '#9b59b6',
        'default': '#95a5a6'
    },
    'access_gaps': {
        'critical': '#e74c3c',
        'high': '#e67e22',
        'moderate': '#f39c12',
        'low': '#2ecc71'
    }
}

def create_map(hc_gdf, hosp_gdf, hp_gdf, show_access_gaps=False, filters=None):
    """Create the interactive map"""
    
    # Apply filters
    filtered_hc = hc_gdf.copy()
    if filters:
        if 'district' in filters and filters['district']:
            filtered_hc = filtered_hc[filtered_hc['District'].isin(filters['district'])]
        if 'max_travel_time' in filters:
            filtered_hc = filtered_hc[filtered_hc['Travel_Time_RealTime_Hours'] <= filters['max_travel_time']]
    
    # Initialize figure
    fig = go.Figure()
    
    # Add health posts
    fig.add_trace(go.Scattermapbox(
        lat=hp_gdf.geometry.y,
        lon=hp_gdf.geometry.x,
        mode='markers',
        marker=dict(size=4, color='gray'),
        text=[f"Health Post: {name}" for name in hp_gdf['Facility Name']],
        hoverinfo='text',
        name='Health Posts',
        showlegend=True
    ))
    
    # Add health centers with color coding
    for _, row in filtered_hc.iterrows():
        if show_access_gaps:
            color = COLOR_SCHEMES['access_gaps'][row['access_gap_severity']]
            size = 12 if row['access_gap_severity'] == 'critical' else 8
        else:
            color = COLOR_SCHEMES['hospitals'].get(row['Hosp_name'], COLOR_SCHEMES['hospitals']['default'])
            size = 8
        
        hover_text = (
            f"<b>{row['HC_Name']}</b><br>"
            f"District: {row['District']}<br>"
            f"Referral Hospital: {row['Hosp_name']}<br>"
            f"Distance: {row['Dist_hosp']:.1f} km<br>"
            f"Travel Time: {row['Travel_Time_RealTime_Hours']:.2f} hours"
        )
        
        if show_access_gaps:
            hover_text += f"<br>Access Gap: {row['access_gap_severity'].upper()}"
        
        fig.add_trace(go.Scattermapbox(
            lat=[row.geometry.y],
            lon=[row.geometry.x],
            mode='markers',
            marker=dict(size=size, color=color),
            text=hover_text,
            hoverinfo='text',
            name='Health Centers' if _ == 0 else '',
            showlegend=(_ == 0),
            legendgroup='hc'
        ))
    
    # Add hospitals
    for _, row in hosp_gdf.iterrows():
        color = COLOR_SCHEMES['hospitals'].get(row['Hospital Name'], COLOR_SCHEMES['hospitals']['default'])
        
        hover_text = (
            f"<b>{row['Hospital Name']}</b><br>"
            f"Type: {'National Referral' if row['Refer to'] == 'National' else 'District Hospital'}<br>"
            f"Refers to: {row['Refer to']}"
        )
        
        fig.add_trace(go.Scattermapbox(
            lat=[row.geometry.y],
            lon=[row.geometry.x],
            mode='markers',
            marker=dict(size=15, color=color),
            text=hover_text,
            hoverinfo='text',
            name=row['Hospital Name'],
            showlegend=True
        ))
    
    # Update layout
    fig.update_layout(
        mapbox=dict(
            style="carto-positron",
            zoom=6.5,
            center=dict(lat=-1.9403, lon=29.8739)
        ),
        margin={"r": 0, "t": 40, "l": 0, "b": 0},
        height=600,
        title="Rwanda Healthcare Referral Network" + (" - Access Gaps" if show_access_gaps else ""),
        showlegend=True,
        legend=dict(
            yanchor="top",
            y=0.99,
            xanchor="left",
            x=0.01,
            bgcolor="rgba(255,255,255,0.8)"
        )
    )
    
    return fig

def main():
    # Load sample data
    hc_gdf, hosp_gdf, hp_gdf = create_sample_data()
    
    # Sidebar filters
    st.sidebar.header("🔍 Filters")
    
    # District filter
    selected_districts = st.sidebar.multiselect(
        "Select Districts",
        options=sorted(hc_gdf['District'].unique()),
        default=[]
    )
    
    # Travel time filter
    max_travel_time = st.sidebar.slider(
        "Maximum Travel Time (hours)",
        min_value=0.5,
        max_value=5.0,
        value=5.0,
        step=0.5
    )
    
    # Display options
    st.sidebar.header("📊 Display Options")
    show_access_gaps = st.sidebar.checkbox("Show Access Gaps", value=False)
    show_statistics = st.sidebar.checkbox("Show Statistics", value=True)
    
    # Compile filters
    filters = {
        'district': selected_districts if selected_districts else None,
        'max_travel_time': max_travel_time
    }
    
    # Display metrics
    if show_statistics:
        col1, col2, col3, col4 = st.columns(4)
        
        # Apply filters for metrics
        filtered_hc = hc_gdf.copy()
        if filters['district']:
            filtered_hc = filtered_hc[filtered_hc['District'].isin(filters['district'])]
        filtered_hc = filtered_hc[filtered_hc['Travel_Time_RealTime_Hours'] <= filters['max_travel_time']]
        
        with col1:
            st.metric("Health Centers", len(filtered_hc))
        
        with col2:
            avg_travel = filtered_hc['Travel_Time_RealTime_Hours'].mean()
            st.metric("Avg Travel Time", f"{avg_travel:.1f} hrs")
        
        with col3:
            critical = len(filtered_hc[filtered_hc['access_gap_severity'] == 'critical'])
            st.metric("Critical Gaps", critical)
        
        with col4:
            st.metric("Hospitals", len(hosp_gdf))
    
    # Create tabs
    tab1, tab2, tab3 = st.tabs(["📍 Map", "📊 Analysis", "📈 Statistics"])
    
    with tab1:
        # Create and display map
        with st.spinner("Generating map..."):
            fig = create_map(hc_gdf, hosp_gdf, hp_gdf, show_access_gaps, filters)
            st.plotly_chart(fig, use_container_width=True)
        
        # Legend for access gaps
        if show_access_gaps:
            st.markdown("### Access Gap Legend")
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.markdown("🟢 **Low**: < 1.5 hours")
            with col2:
                st.markdown("🟡 **Moderate**: 1.5-2 hours")
            with col3:
                st.markdown("🟠 **High**: 2-3 hours")
            with col4:
                st.markdown("🔴 **Critical**: > 3 hours")
    
    with tab2:
        st.subheader("Access Gap Analysis")
        
        # Apply filters
        analysis_df = hc_gdf.copy()
        if filters['district']:
            analysis_df = analysis_df[analysis_df['District'].isin(filters['district'])]
        analysis_df = analysis_df[analysis_df['Travel_Time_RealTime_Hours'] <= filters['max_travel_time']]
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Access gap distribution
            gap_counts = analysis_df['access_gap_severity'].value_counts()
            st.bar_chart(gap_counts)
            
        with col2:
            # Critical facilities table
            critical = analysis_df[analysis_df['access_gap_severity'] == 'critical']
            if not critical.empty:
                st.markdown("### Critical Access Facilities")
                display_df = critical[['HC_Name', 'District', 'Travel_Time_RealTime_Hours', 'Dist_hosp']].copy()
                display_df.columns = ['Health Center', 'District', 'Travel Time (hrs)', 'Distance (km)']
                st.dataframe(display_df.head(10))
            else:
                st.info("No critical access gaps found with current filters")
    
    with tab3:
        st.subheader("Network Statistics")
        
        # Travel time distribution
        import plotly.express as px
        
        fig_hist = px.histogram(
            hc_gdf,
            x='Travel_Time_RealTime_Hours',
            nbins=20,
            title="Travel Time Distribution",
            labels={'Travel_Time_RealTime_Hours': 'Travel Time (hours)', 'count': 'Number of Facilities'},
            color_discrete_sequence=['#3498db']
        )
        st.plotly_chart(fig_hist, use_container_width=True)
        
        # Summary statistics
        st.markdown("### Summary Statistics")
        summary = hc_gdf[['Travel_Time_RealTime_Hours', 'Dist_hosp']].describe()
        summary.columns = ['Travel Time (hours)', 'Distance (km)']
        st.dataframe(summary.round(2))
        
        # District comparison
        st.markdown("### Average Travel Time by District")
        district_avg = hc_gdf.groupby('District')['Travel_Time_RealTime_Hours'].mean().round(2)
        st.bar_chart(district_avg)
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center'>
        <p>This is a demonstration using sample data</p>
        <p style='font-size: 0.9em'>To use real data, update the data loading function with your actual files</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()