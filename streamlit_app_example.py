"""
Sample Streamlit Application for Rwanda Healthcare Referral Network Map
"""

import streamlit as st
import pandas as pd
import geopandas as gpd
import numpy as np
from streamlit_referral_map import (
    create_referral_map, 
    create_streamlit_filters,
    display_map_metrics,
    get_mapbox_travel_time_cached,
    calculate_access_gaps
)

# Page configuration
st.set_page_config(
    page_title="Rwanda Healthcare Referral Network",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Title and description
st.title("🏥 Rwanda Healthcare Referral Network Analysis")
st.markdown("""
Interactive map showing the healthcare referral network with real-time travel times, 
access gap analysis, and facility upgrade recommendations.
""")

# Load data function
@st.cache_data
def load_data():
    """
    Load all required datasets
    Replace these with your actual data loading logic
    """
    try:
        # Load shapefiles and data
        rwanda = gpd.read_file("../Shapefiles/Rwanda/rwa_adm0_2006_NISR_WGS1984_20181002.shp")
        district = gpd.read_file("../Shapefiles/Rwanda/rwa_adm1_2006_NISR_WGS1984_20181002.shp")
        
        # Load health facility data
        hp = pd.read_excel("../Health Facility/Facility GIS_.xlsx", sheet_name='HP')
        
        # Convert to GeoDataFrame
        from shapely.geometry import Point
        hp_geometry = [Point(xy) for xy in zip(hp.longitude, hp.latitude)]
        hp_gdf = gpd.GeoDataFrame(hp, geometry=hp_geometry, crs='EPSG:4326')
        
        # Load other facility data (you'll need to adapt this to your data structure)
        hc_points = gpd.read_file("path_to_health_centers.gpkg")  # Update path
        hosp_points = gpd.read_file("path_to_hospitals.gpkg")  # Update path
        nrh_gdf = gpd.read_file("path_to_nrh.gpkg")  # Update path
        
        # Load road networks
        hc_roads = gpd.read_file("path_to_hc_roads.gpkg")  # Update path
        hosp_roads = gpd.read_file("path_to_hosp_roads.gpkg")  # Update path
        
        return {
            'rwanda': rwanda,
            'district': district,
            'hp_gdf': hp_gdf,
            'hc_points': hc_points,
            'hosp_points': hosp_points,
            'nrh_gdf': nrh_gdf,
            'hc_roads': hc_roads,
            'hosp_roads': hosp_roads
        }
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return None

# Load configuration
MAPBOX_TOKEN = st.secrets.get("MAPBOX_TOKEN", "your_mapbox_token_here")

# Main app
def main():
    # Load data
    with st.spinner("Loading data..."):
        data = load_data()
    
    if data is None:
        st.error("Failed to load data. Please check your data files.")
        return
    
    # Create filters in sidebar
    filters, show_layers, show_access_gaps, show_upgrade_candidates, sample_facilities, sample_size = \
        create_streamlit_filters(
            data.get('hp_gdf', pd.DataFrame()),
            data.get('hc_points', pd.DataFrame()),
            data.get('hosp_points', pd.DataFrame())
        )
    
    # Display metrics
    st.subheader("Network Metrics")
    display_map_metrics(
        data.get('hc_points', pd.DataFrame()),
        data.get('hosp_points', pd.DataFrame()),
        filters
    )
    
    # Add tabs for different views
    tab1, tab2, tab3 = st.tabs(["📍 Map View", "📊 Analysis", "📈 Statistics"])
    
    with tab1:
        # Create and display map
        with st.spinner("Generating map..."):
            # Get map center
            if data['district'] is not None and not data['district'].empty:
                rwanda_centroid = data['district'].union_all().centroid
                center_lat = rwanda_centroid.y
                center_lon = rwanda_centroid.x
            else:
                center_lat = -1.9403
                center_lon = 29.8739
            
            # Create the map
            fig = create_referral_map(
                hp_gdf=data.get('hp_gdf'),
                hc_points=data.get('hc_points'),
                hosp_points=data.get('hosp_points'),
                nrh_gdf=data.get('nrh_gdf'),
                hc_roads=data.get('hc_roads'),
                hosp_roads=data.get('hosp_roads'),
                district_gdf=data.get('district'),
                rwanda_gdf=data.get('rwanda'),
                filters=filters,
                show_health_posts=show_layers['health_posts'],
                show_health_centers=show_layers['health_centers'],
                show_hospitals=show_layers['hospitals'],
                show_national_referral=show_layers['national_referral'],
                show_hc_roads=show_layers['hc_roads'],
                show_hosp_roads=show_layers['hosp_roads'],
                show_boundaries=show_layers['boundaries'],
                show_access_gaps=show_access_gaps,
                show_upgrade_candidates=show_upgrade_candidates,
                mapbox_token=MAPBOX_TOKEN,
                center_lat=center_lat,
                center_lon=center_lon,
                sample_facilities=sample_facilities,
                sample_size=sample_size if sample_facilities else 100
            )
            
            # Display the map
            st.plotly_chart(fig, use_container_width=True)
        
        # Download button for map
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📥 Download Map as HTML"):
                import plotly.io as pio
                html_string = pio.to_html(fig, include_plotlyjs='cdn')
                st.download_button(
                    label="Download HTML",
                    data=html_string,
                    file_name="referral_network_map.html",
                    mime="text/html"
                )
    
    with tab2:
        st.subheader("Access Gap Analysis")
        
        if show_access_gaps and data.get('hc_points') is not None:
            # Calculate access gaps
            hc_with_gaps = calculate_access_gaps(data['hc_points'])
            
            # Display summary
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("### Access Gap Distribution")
                gap_counts = hc_with_gaps['access_gap_severity'].value_counts()
                st.bar_chart(gap_counts)
            
            with col2:
                st.markdown("### Critical Facilities")
                critical_facilities = hc_with_gaps[hc_with_gaps['access_gap_severity'] == 'critical']
                if not critical_facilities.empty:
                    st.dataframe(
                        critical_facilities[['HC_Name', 'Hosp_name', 'Dist_hosp', 'Travel_Time_RealTime_Hours']]
                        .head(10)
                    )
                else:
                    st.info("No critical access gaps found")
        
        if show_upgrade_candidates:
            st.subheader("Upgrade Candidates")
            
            # Display upgrade recommendations
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("### Health Centers → MHC Candidates")
                st.info("Facilities that could be upgraded to Medicalized Health Centers based on distance and population served")
                # Add your upgrade candidate logic here
            
            with col2:
                st.markdown("### MHC → Hospital Candidates")
                st.info("Medicalized Health Centers that could become District Hospitals")
                # Add your upgrade candidate logic here
    
    with tab3:
        st.subheader("Network Statistics")
        
        # Create statistical visualizations
        if data.get('hc_points') is not None and not data['hc_points'].empty:
            col1, col2 = st.columns(2)
            
            with col1:
                # Travel time distribution
                if 'Travel_Time_RealTime_Hours' in data['hc_points'].columns:
                    st.markdown("### Travel Time Distribution")
                    travel_times = data['hc_points']['Travel_Time_RealTime_Hours'].dropna()
                    
                    # Create histogram
                    import plotly.express as px
                    fig_hist = px.histogram(
                        travel_times, 
                        nbins=20,
                        title="Distribution of Travel Times to Referral Hospitals",
                        labels={'value': 'Travel Time (hours)', 'count': 'Number of Facilities'}
                    )
                    st.plotly_chart(fig_hist, use_container_width=True)
            
            with col2:
                # Distance distribution
                if 'Dist_hosp' in data['hc_points'].columns:
                    st.markdown("### Distance Distribution")
                    distances = data['hc_points']['Dist_hosp'].dropna()
                    
                    fig_dist = px.histogram(
                        distances,
                        nbins=20,
                        title="Distribution of Distances to Referral Hospitals",
                        labels={'value': 'Distance (km)', 'count': 'Number of Facilities'}
                    )
                    st.plotly_chart(fig_dist, use_container_width=True)
            
            # Summary statistics table
            st.markdown("### Summary Statistics")
            summary_stats = pd.DataFrame()
            
            if 'Travel_Time_RealTime_Hours' in data['hc_points'].columns:
                travel_stats = data['hc_points']['Travel_Time_RealTime_Hours'].describe()
                summary_stats['Travel Time (hours)'] = travel_stats
            
            if 'Dist_hosp' in data['hc_points'].columns:
                dist_stats = data['hc_points']['Dist_hosp'].describe()
                summary_stats['Distance (km)'] = dist_stats
            
            if not summary_stats.empty:
                st.dataframe(summary_stats.T.round(2))
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center'>
        <p>Rwanda Healthcare Referral Network Analysis Dashboard</p>
        <p style='font-size: 0.8em'>Data updated: 2024 | Powered by Streamlit & Plotly</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()