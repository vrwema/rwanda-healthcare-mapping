"""
Rwanda Healthcare Referral Network Map for Streamlit
Enhanced version with access gap visualization and upgrade candidate analysis
"""

import streamlit as st
import pandas as pd
import geopandas as gpd
import numpy as np
import plotly.graph_objects as go
import requests
import time
from typing import Optional, Dict, Tuple, List
from functools import lru_cache
import json

# Cache configuration for API calls
CACHE_EXPIRY_HOURS = 24

# Color schemes
COLOR_SCHEMES = {
    'hospitals': {
        'CHUB': '#3498db',  # Blue
        'CHUK': '#e74c3c',  # Red
        'RMH': '#2ecc71',   # Green
        'KFH': '#9b59b6',   # Purple
        'default': '#95a5a6' # Gray
    },
    'access_gaps': {
        'critical': '#e74c3c',    # Red - > 3 hours
        'high': '#e67e22',        # Orange - 2-3 hours
        'moderate': '#f39c12',    # Yellow - 1.5-2 hours
        'low': '#2ecc71',         # Green - < 1.5 hours
    },
    'upgrade_candidates': {
        'hc_to_mhc': '#9b59b6',    # Purple
        'mhc_to_hospital': '#e67e22', # Orange
        'priority': '#e74c3c'      # Red for high priority
    },
    'facility_types': {
        'health_post': '#95a5a6',
        'health_center': '#3498db',
        'medicalized_hc': '#9b59b6',
        'district_hospital': '#e67e22',
        'provincial_hospital': '#27ae60',
        'national_referral': '#f1c40f'
    }
}

@st.cache_data(ttl=CACHE_EXPIRY_HOURS * 3600)
def get_mapbox_travel_time_cached(start_coords: tuple, end_coords: tuple, 
                                  access_token: str, profile='driving') -> Optional[float]:
    """
    Cached version of Mapbox API travel time calculation
    """
    try:
        base_url = f"https://api.mapbox.com/directions/v5/mapbox/{profile}"
        coords = f"{start_coords[0]},{start_coords[1]};{end_coords[0]},{end_coords[1]}"
        url = f"{base_url}/{coords}"
        
        params = {
            'access_token': access_token,
            'geometries': 'geojson',
            'overview': 'false'
        }
        
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('routes'):
                duration_hours = data['routes'][0]['duration'] / 3600
                return round(duration_hours, 2)
        
        return None
    except Exception as e:
        st.warning(f"Mapbox API error: {e}")
        return None

@st.cache_data(ttl=CACHE_EXPIRY_HOURS * 3600)
def get_osrm_travel_time_cached(start_coords: tuple, end_coords: tuple, 
                                profile='driving') -> Optional[float]:
    """
    Cached OSRM fallback for travel time calculation
    """
    try:
        url = f"http://router.project-osrm.org/route/v1/{profile}/"
        url += f"{start_coords[0]},{start_coords[1]};{end_coords[0]},{end_coords[1]}"
        
        params = {'overview': 'false', 'steps': 'false'}
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('routes'):
                duration_hours = data['routes'][0]['duration'] / 3600
                return round(duration_hours, 2)
        
        return None
    except Exception as e:
        return None

def calculate_access_gaps(df: pd.DataFrame, time_threshold: float = 2.0, 
                         distance_threshold: float = 50.0) -> pd.DataFrame:
    """
    Identify facilities with poor access to referral hospitals
    """
    df = df.copy()
    
    # Calculate access gap severity
    df['access_gap_severity'] = 'low'
    
    # Check both travel time and distance
    if 'Travel_Time_RealTime_Hours' in df.columns:
        df.loc[df['Travel_Time_RealTime_Hours'] > 3.0, 'access_gap_severity'] = 'critical'
        df.loc[(df['Travel_Time_RealTime_Hours'] > 2.0) & 
               (df['Travel_Time_RealTime_Hours'] <= 3.0), 'access_gap_severity'] = 'high'
        df.loc[(df['Travel_Time_RealTime_Hours'] > 1.5) & 
               (df['Travel_Time_RealTime_Hours'] <= 2.0), 'access_gap_severity'] = 'moderate'
    
    # Also consider distance if travel time not available
    if 'Dist_hosp' in df.columns:
        df.loc[(df['Dist_hosp'] > distance_threshold) & 
               (df['access_gap_severity'] == 'low'), 'access_gap_severity'] = 'moderate'
    
    return df

def identify_upgrade_candidates(hc_df: pd.DataFrame, hosp_df: pd.DataFrame, 
                               criteria: Dict) -> Dict[str, pd.DataFrame]:
    """
    Identify facilities that are candidates for upgrade based on criteria
    """
    candidates = {}
    
    # HC to MHC upgrade candidates
    hc_to_mhc_criteria = criteria.get('hc_to_mhc', {
        'min_population': 50000,
        'min_distance_to_hospital': 30,
        'min_travel_time': 1.5
    })
    
    hc_to_mhc = hc_df.copy()
    if 'Dist_hosp' in hc_to_mhc.columns:
        hc_to_mhc = hc_to_mhc[
            (hc_to_mhc['Dist_hosp'] > hc_to_mhc_criteria['min_distance_to_hospital']) |
            (hc_to_mhc.get('Travel_Time_RealTime_Hours', 0) > hc_to_mhc_criteria['min_travel_time'])
        ]
    candidates['hc_to_mhc'] = hc_to_mhc
    
    # MHC to Hospital upgrade candidates (if MHC data available)
    mhc_to_hosp_criteria = criteria.get('mhc_to_hospital', {
        'min_population': 100000,
        'min_distance_to_nth': 50,
        'serves_multiple_hc': True
    })
    
    # This would need MHC-specific data
    candidates['mhc_to_hospital'] = pd.DataFrame()  # Placeholder
    
    return candidates

def create_facility_markers(fig: go.Figure, facilities_df: gpd.GeoDataFrame, 
                          facility_type: str, filters: Dict, 
                          show_access_gaps: bool = False,
                          show_upgrade_candidates: bool = False) -> go.Figure:
    """
    Add facility markers to the map with proper styling and hover info
    """
    
    # Apply filters
    filtered_df = facilities_df.copy()
    
    if filters.get('district'):
        if 'District' in filtered_df.columns:
            filtered_df = filtered_df[filtered_df['District'].isin(filters['district'])]
    
    if filters.get('sub_district'):
        if 'Sub_District' in filtered_df.columns:
            filtered_df = filtered_df[filtered_df['Sub_District'].isin(filters['sub_district'])]
    
    # Apply travel time filter
    if filters.get('max_travel_time') and 'Travel_Time_RealTime_Hours' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['Travel_Time_RealTime_Hours'] <= filters['max_travel_time']]
    
    # Calculate access gaps if requested
    if show_access_gaps:
        filtered_df = calculate_access_gaps(filtered_df)
    
    # Group facilities for legend management
    if facility_type == 'health_posts':
        first_trace = True
        for _, row in filtered_df.iterrows():
            if row.geometry and not row.geometry.is_empty:
                hover_text = (
                    f"<b>Health Post:</b> {row.get('Facility Name', 'Unknown')}<br>"
                    f"<b>Type:</b> Primary Health Facility<br>"
                    f"<b>Location:</b> {row.geometry.y:.4f}, {row.geometry.x:.4f}"
                )
                
                fig.add_trace(go.Scattermapbox(
                    lat=[row.geometry.y],
                    lon=[row.geometry.x],
                    mode='markers',
                    marker=dict(size=3, symbol='circle', 
                              color=COLOR_SCHEMES['facility_types']['health_post']),
                    text=hover_text,
                    hoverinfo='text',
                    name='Health Posts',
                    legendgroup='health_posts',
                    showlegend=first_trace,
                ))
                first_trace = False
    
    elif facility_type == 'health_centers':
        # Color based on access gaps or referral hospital
        first_trace = True
        for _, row in filtered_df.iterrows():
            if row.geometry and not row.geometry.is_empty:
                # Determine color
                if show_access_gaps and 'access_gap_severity' in row:
                    color = COLOR_SCHEMES['access_gaps'][row['access_gap_severity']]
                    marker_size = 10 if row['access_gap_severity'] == 'critical' else 7
                else:
                    hospital = row.get('Hosp_name', 'Unknown')
                    color = COLOR_SCHEMES['hospitals'].get(hospital, 
                           COLOR_SCHEMES['hospitals']['default'])
                    marker_size = 7
                
                # Enhanced hover text
                travel_time_text = "Not calculated"
                if pd.notna(row.get('Travel_Time_RealTime_Hours')):
                    travel_time_text = f"{row['Travel_Time_RealTime_Hours']:.2f} hours"
                
                hover_text = (
                    f"<b>Health Center:</b> {row.get('HC_Name', 'Unknown')}<br>"
                    f"<b>Referred Hospital:</b> {row.get('Hosp_name', 'Unknown')}<br>"
                    f"<b>Distance to Hospital:</b> {row.get('Dist_hosp', 0):.1f} km<br>"
                    f"<b>Travel Time (Real-time):</b> {travel_time_text}<br>"
                )
                
                if show_access_gaps and 'access_gap_severity' in row:
                    hover_text += f"<b>Access Gap:</b> {row['access_gap_severity'].upper()}<br>"
                
                fig.add_trace(go.Scattermapbox(
                    lat=[row.geometry.y],
                    lon=[row.geometry.x],
                    mode='markers',
                    marker=dict(size=marker_size, symbol='circle', color=color),
                    text=hover_text,
                    hoverinfo='text',
                    name='Health Centers',
                    legendgroup='health_centers',
                    showlegend=first_trace,
                ))
                first_trace = False
    
    elif facility_type == 'hospitals':
        for hospital in filtered_df['Hospital Name'].unique():
            hospital_data = filtered_df[filtered_df['Hospital Name'] == hospital]
            color = COLOR_SCHEMES['hospitals'].get(hospital, 
                   COLOR_SCHEMES['hospitals']['default'])
            
            hover_texts = []
            for _, row in hospital_data.iterrows():
                travel_time_text = "Not calculated"
                if pd.notna(row.get('Travel_Time_RealTime_Hours')):
                    travel_time_text = f"{row['Travel_Time_RealTime_Hours']:.2f} hours"
                
                hover_text = (
                    f"<b>Hospital:</b> {row['Hospital Name']}<br>"
                    f"<b>Type:</b> District/Provincial Hospital<br>"
                    f"<b>Refers to:</b> {row.get('Refer to', 'N/A')}<br>"
                    f"<b>Distance to NTH:</b> {row.get('Distance to NTH', 0):.0f} km<br>"
                    f"<b>Travel Time to NTH:</b> {travel_time_text}"
                )
                hover_texts.append(hover_text)
            
            fig.add_trace(go.Scattermapbox(
                lat=hospital_data.geometry.y,
                lon=hospital_data.geometry.x,
                mode='markers',
                marker=dict(size=10, symbol='circle', color=color),
                text=hover_texts,
                hoverinfo='text',
                name=hospital,
                showlegend=True,
            ))
    
    elif facility_type == 'national_referral':
        first_trace = True
        for _, row in filtered_df.iterrows():
            if row.geometry and not row.geometry.is_empty:
                hover_text = (
                    f"<b>National Referral Hospital:</b> {row.get('Hospital Name', 'Unknown')}<br>"
                    f"<b>Type:</b> Tertiary Care (National Level)<br>"
                    f"<b>Services:</b> Specialized care, Complex procedures"
                )
                
                fig.add_trace(go.Scattermapbox(
                    lat=[row.geometry.y],
                    lon=[row.geometry.x],
                    mode='markers',
                    marker=dict(size=20, symbol='circle', 
                              color=COLOR_SCHEMES['facility_types']['national_referral']),
                    text=hover_text,
                    hoverinfo='text',
                    name='National Referral Hospitals',
                    legendgroup='national_referral_hospitals',
                    showlegend=first_trace,
                ))
                first_trace = False
    
    return fig

def add_referral_roads(fig: go.Figure, roads_df: gpd.GeoDataFrame, 
                      road_type: str, filters: Dict,
                      hospital_colors: Dict = None) -> go.Figure:
    """
    Add referral road networks to the map
    """
    # Apply filters if needed
    filtered_roads = roads_df.copy()
    
    first_road = True
    for _, row in filtered_roads.iterrows():
        road_geometry = row.geometry
        if road_geometry and road_geometry.geom_type == 'LineString':
            lon, lat = map(list, road_geometry.xy)
            
            # Determine color based on road type and associated facility
            if road_type == 'hc_to_hospital' and hospital_colors:
                color = hospital_colors.get(row.get('Hosp_name', ''), 
                       COLOR_SCHEMES['hospitals']['default'])
            elif road_type == 'hospital_to_nth':
                refer_to = row.get('Refer to', '')
                color = COLOR_SCHEMES['hospitals'].get(refer_to, 
                       COLOR_SCHEMES['hospitals']['default'])
            else:
                color = 'gray'
            
            fig.add_trace(go.Scattermapbox(
                lat=lat,
                lon=lon,
                mode='lines',
                hoverinfo='skip',
                line=dict(width=1, color=color),
                name=f'{road_type.replace("_", " ").title()} Roads',
                legendgroup=f'{road_type}_roads',
                showlegend=first_road
            ))
            first_road = False
    
    return fig

def add_boundaries(fig: go.Figure, district_gdf: gpd.GeoDataFrame, 
                  rwanda_gdf: gpd.GeoDataFrame) -> go.Figure:
    """
    Add administrative boundaries to the map
    """
    # Add district boundaries
    if not district_gdf.empty:
        district_geojson = district_gdf.geometry.__geo_interface__
        district_trace = go.Choroplethmapbox(
            geojson=district_geojson,
            locations=district_gdf.index,
            colorscale=[[0, 'rgba(0, 0, 0, 0)'], [1, 'rgba(0, 0, 0, 0)']],
            z=np.zeros(len(district_gdf)),
            hoverinfo='skip',
            marker_line_width=0.5,
            marker_line_color='gray',
            showlegend=False,
            showscale=False
        )
        fig.add_trace(district_trace)
    
    # Add Rwanda boundary
    if not rwanda_gdf.empty:
        rwanda_geojson = rwanda_gdf.geometry.__geo_interface__
        rwanda_trace = go.Choroplethmapbox(
            geojson=rwanda_geojson,
            locations=rwanda_gdf.index,
            colorscale=[[0, 'rgba(0, 0, 0, 0)'], [1, 'rgba(0, 0, 0, 0)']],
            z=np.zeros(len(rwanda_gdf)),
            hoverinfo='skip',
            marker_line_color='darkgray',
            marker_line_width=1.0,
            showlegend=False,
            showscale=False
        )
        fig.add_trace(rwanda_trace)
    
    return fig

def create_referral_map(
    # DataFrames
    hp_gdf: gpd.GeoDataFrame = None,
    hc_points: gpd.GeoDataFrame = None,
    hosp_points: gpd.GeoDataFrame = None,
    nrh_gdf: gpd.GeoDataFrame = None,
    hc_roads: gpd.GeoDataFrame = None,
    hosp_roads: gpd.GeoDataFrame = None,
    district_gdf: gpd.GeoDataFrame = None,
    rwanda_gdf: gpd.GeoDataFrame = None,
    
    # Filters
    filters: Dict = None,
    
    # Display options
    show_health_posts: bool = True,
    show_health_centers: bool = True,
    show_hospitals: bool = True,
    show_national_referral: bool = True,
    show_hc_roads: bool = True,
    show_hosp_roads: bool = True,
    show_boundaries: bool = True,
    show_access_gaps: bool = False,
    show_upgrade_candidates: bool = False,
    
    # Map settings
    mapbox_token: str = None,
    map_style: str = "carto-darkmatter",
    center_lat: float = -1.9403,
    center_lon: float = 29.8739,
    zoom: int = 8,
    
    # Performance options
    sample_facilities: bool = False,
    sample_size: int = 100
) -> go.Figure:
    """
    Create an interactive referral network map for Streamlit
    
    Returns:
        Plotly figure object ready for st.plotly_chart()
    """
    
    # Initialize filters if not provided
    if filters is None:
        filters = {}
    
    # Sample data if requested (for performance)
    if sample_facilities and hc_points is not None and len(hc_points) > sample_size:
        hc_points = hc_points.sample(n=sample_size, random_state=42)
    
    # Calculate upgrade candidates if requested
    upgrade_candidates = {}
    if show_upgrade_candidates and hc_points is not None and hosp_points is not None:
        upgrade_criteria = filters.get('upgrade_criteria', {})
        upgrade_candidates = identify_upgrade_candidates(hc_points, hosp_points, upgrade_criteria)
    
    # Create base figure
    fig = go.Figure()
    
    # Add boundaries first (bottom layer)
    if show_boundaries and district_gdf is not None and rwanda_gdf is not None:
        fig = add_boundaries(fig, district_gdf, rwanda_gdf)
    
    # Add referral roads
    if show_hc_roads and hc_roads is not None:
        # Generate hospital colors for consistency
        if hosp_points is not None:
            hospitals = hosp_points['Hospital Name'].unique()
            hospital_colors = {h: COLOR_SCHEMES['hospitals'].get(h, 
                              COLOR_SCHEMES['hospitals']['default']) for h in hospitals}
        else:
            hospital_colors = {}
        
        fig = add_referral_roads(fig, hc_roads, 'hc_to_hospital', filters, hospital_colors)
    
    if show_hosp_roads and hosp_roads is not None:
        fig = add_referral_roads(fig, hosp_roads, 'hospital_to_nth', filters)
    
    # Add facilities (in order of visual hierarchy)
    if show_health_posts and hp_gdf is not None:
        fig = create_facility_markers(fig, hp_gdf, 'health_posts', filters)
    
    if show_health_centers and hc_points is not None:
        fig = create_facility_markers(fig, hc_points, 'health_centers', filters,
                                     show_access_gaps, show_upgrade_candidates)
    
    if show_hospitals and hosp_points is not None:
        fig = create_facility_markers(fig, hosp_points, 'hospitals', filters)
    
    if show_national_referral and nrh_gdf is not None:
        fig = create_facility_markers(fig, nrh_gdf, 'national_referral', filters)
    
    # Update layout
    title = 'Rwanda Healthcare Referral Network'
    if show_access_gaps:
        title += ' - Access Gap Analysis'
    if show_upgrade_candidates:
        title += ' - Upgrade Candidates'
    
    fig.update_layout(
        title_text=title,
        title_x=0.5,
        mapbox_style=map_style,
        mapbox_accesstoken=mapbox_token,
        width=1200,
        height=800,
        mapbox_zoom=zoom,
        mapbox_center={"lat": center_lat, "lon": center_lon},
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
            bgcolor="rgba(0,0,0,0.5)",
            bordercolor="white",
            borderwidth=0.4,
            traceorder="normal"
        ),
        legend_tracegroupgap=10,
    )
    
    return fig

# Streamlit-specific helper functions
def create_streamlit_filters(hp_df, hc_df, hosp_df):
    """
    Create Streamlit sidebar filters for the map
    """
    filters = {}
    
    with st.sidebar:
        st.header("Map Filters")
        
        # District filter
        if 'District' in hc_df.columns:
            districts = st.multiselect(
                "Select Districts",
                options=sorted(hc_df['District'].dropna().unique()),
                default=[]
            )
            if districts:
                filters['district'] = districts
        
        # Sub-district filter
        if 'Sub_District' in hc_df.columns:
            sub_districts = st.multiselect(
                "Select Sub-Districts",
                options=sorted(hc_df['Sub_District'].dropna().unique()),
                default=[]
            )
            if sub_districts:
                filters['sub_district'] = sub_districts
        
        # Travel time threshold
        max_travel_time = st.slider(
            "Maximum Travel Time (hours)",
            min_value=0.5,
            max_value=5.0,
            value=3.0,
            step=0.5
        )
        filters['max_travel_time'] = max_travel_time
        
        # Distance threshold
        max_distance = st.slider(
            "Maximum Distance (km)",
            min_value=10,
            max_value=200,
            value=100,
            step=10
        )
        filters['max_distance'] = max_distance
        
        st.header("Display Options")
        
        # Layer toggles
        show_layers = {
            'health_posts': st.checkbox("Show Health Posts", value=True),
            'health_centers': st.checkbox("Show Health Centers", value=True),
            'hospitals': st.checkbox("Show Hospitals", value=True),
            'national_referral': st.checkbox("Show National Referral Hospitals", value=True),
            'hc_roads': st.checkbox("Show HC→Hospital Roads", value=True),
            'hosp_roads': st.checkbox("Show Hospital→NTH Roads", value=False),
            'boundaries': st.checkbox("Show Administrative Boundaries", value=True),
        }
        
        st.header("Analysis Options")
        
        # Analysis toggles
        show_access_gaps = st.checkbox("Show Access Gaps", value=False)
        show_upgrade_candidates = st.checkbox("Show Upgrade Candidates", value=False)
        
        # Performance options
        st.header("Performance")
        sample_facilities = st.checkbox("Sample Facilities (for performance)", value=False)
        if sample_facilities:
            sample_size = st.number_input("Sample Size", min_value=50, max_value=500, value=100)
        else:
            sample_size = None
        
    return filters, show_layers, show_access_gaps, show_upgrade_candidates, sample_facilities, sample_size

def display_map_metrics(hc_df, hosp_df, filters):
    """
    Display key metrics about the referral network
    """
    col1, col2, col3, col4 = st.columns(4)
    
    # Apply filters to get accurate metrics
    filtered_hc = hc_df.copy()
    if filters.get('district'):
        if 'District' in filtered_hc.columns:
            filtered_hc = filtered_hc[filtered_hc['District'].isin(filters['district'])]
    
    with col1:
        st.metric("Health Centers", len(filtered_hc))
    
    with col2:
        if 'Travel_Time_RealTime_Hours' in filtered_hc.columns:
            avg_travel = filtered_hc['Travel_Time_RealTime_Hours'].mean()
            st.metric("Avg Travel Time", f"{avg_travel:.1f} hrs" if not pd.isna(avg_travel) else "N/A")
        else:
            st.metric("Avg Travel Time", "N/A")
    
    with col3:
        if 'Travel_Time_RealTime_Hours' in filtered_hc.columns:
            critical = len(filtered_hc[filtered_hc['Travel_Time_RealTime_Hours'] > 3.0])
            st.metric("Critical Access Gaps", critical)
        else:
            st.metric("Critical Access Gaps", "N/A")
    
    with col4:
        st.metric("Hospitals", len(hosp_df) if hosp_df is not None else 0)