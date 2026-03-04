"""
Rwanda Healthcare Analytics Dashboard - Optimized Final Version
Maximum performance with all features preserved
"""

import streamlit as st
import pandas as pd
import numpy as np
import geopandas as gpd
from shapely.geometry import Point, LineString
import plotly.graph_objects as go
import plotly.express as px
import random
from geopy.distance import geodesic
import os
import warnings
import requests
import time
from typing import Optional, Dict, List, Tuple
import hashlib
import json
warnings.filterwarnings('ignore')

# Page configuration
st.set_page_config(
    page_title="Rwanda Healthcare Analytics Dashboard",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Mapbox configuration
# Token will be loaded from Streamlit secrets or environment variables
MAPBOX_TOKEN = st.secrets.get("MAPBOX_TOKEN", os.environ.get("MAPBOX_TOKEN", "your-mapbox-token-here"))

# Initialize session state
if 'selected_sub_district' not in st.session_state:
    st.session_state.selected_sub_district = None
if 'selected_metric' not in st.session_state:
    st.session_state.selected_metric = 'OPD_total'
if 'travel_time_cache' not in st.session_state:
    st.session_state.travel_time_cache = {}
if 'map_cache' not in st.session_state:
    st.session_state.map_cache = {}

# Constants
PERFORMANCE_METRICS = ['ANC', 'OPD_new', 'OPD_old', 'OPD_total', 'Deliveries', 
                      'Labor_referrals', 'Obstetric_complication_referrals']
METRIC_DESCRIPTIONS = {
    'ANC': 'Antenatal Care Visits',
    'OPD_new': 'New Outpatient Cases',
    'OPD_old': 'Old Outpatient Cases',
    'OPD_total': 'Total Outpatient Cases',
    'Deliveries': 'Total Deliveries',
    'Labor_referrals': 'Labor Referrals',
    'Obstetric_complication_referrals': 'Obstetric Complication Referrals'
}
DATA_ELEMENT_MAP = {
    "ri0XrmXSpEC": "ANC",
    "T6H8cO1Tr5t": "OPD_new",
    "o73Sit5drOc": "OPD_old",
    "TWmX6JS19hO": "Deliveries",
    "o84exadtl82": "Labor_referrals",
    "fICuyReInRd": "Obstetric_complication_referrals"
}

@st.cache_data(persist="disk", ttl=86400)
def get_mapbox_travel_time(start_coords: tuple, end_coords: tuple) -> Optional[float]:
    """Get travel time using Mapbox Directions API with caching"""
    try:
        # Check session cache first
        cache_key = f"{start_coords}_{end_coords}"
        if cache_key in st.session_state.travel_time_cache:
            return st.session_state.travel_time_cache[cache_key]
        
        base_url = f"https://api.mapbox.com/directions/v5/mapbox/driving"
        coords = f"{start_coords[0]},{start_coords[1]};{end_coords[0]},{end_coords[1]}"
        url = f"{base_url}/{coords}"
        
        params = {
            'access_token': MAPBOX_TOKEN,
            'geometries': 'geojson',
            'overview': 'false'
        }
        
        response = requests.get(url, params=params, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('routes'):
                duration_hours = data['routes'][0]['duration'] / 3600
                result = round(duration_hours, 2)
                st.session_state.travel_time_cache[cache_key] = result
                return result
        
        return None
    except:
        return None

@st.cache_data(persist="disk", ttl=7200)
def load_real_hmis_data():
    """Load and process HMIS data with optimized caching"""
    try:
        # Use relative path for deployment
        csv_path = "df_final_opd.csv"  # File should be in same directory as script
        df = pd.read_csv(csv_path, low_memory=False)
        
        # Filter for relevant facilities
        facility_categories = ['Health Center', 'District Hospital', 'L2TH', 
                              'Medicalized Health Center', 'Provincial Hospital', 
                              'Teaching Hospital', 'Referral Hospital']
        df_filtered = df[df['facility_category'].isin(facility_categories)]
        
        # Map data elements
        df_filtered['indicator'] = df_filtered['dataElement'].map(DATA_ELEMENT_MAP)
        
        # Pivot efficiently - using actual column names from the CSV
        GROUP_COLUMNS = ['name', 'sub_district', 'district', 'province', 'facility_category']
        # Only use columns that exist in the dataframe
        existing_columns = [col for col in GROUP_COLUMNS if col in df_filtered.columns]
        
        facility_summary = df_filtered.pivot_table(
            index=existing_columns,
            columns='indicator',
            values='value',
            aggfunc='sum',
            fill_value=0
        ).reset_index()
        
        # Calculate OPD_total
        if 'OPD_new' in facility_summary.columns and 'OPD_old' in facility_summary.columns:
            facility_summary['OPD_total'] = facility_summary['OPD_new'] + facility_summary['OPD_old']
        
        return facility_summary, True
        
    except Exception as e:
        st.warning(f"Could not load CSV data: {e}")
        return pd.DataFrame(), False

def calculate_road_length(geometry):
    """Calculate actual road length from LineString geometry"""
    if geometry is None:
        return 0
    
    total_distance = 0
    
    if geometry.geom_type == 'LineString':
        coords = list(geometry.coords)
        for i in range(len(coords) - 1):
            point1 = (coords[i][1], coords[i][0])
            point2 = (coords[i+1][1], coords[i+1][0])
            total_distance += geodesic(point1, point2).kilometers
    
    elif geometry.geom_type == 'MultiLineString':
        for line in geometry.geoms:
            coords = list(line.coords)
            for i in range(len(coords) - 1):
                point1 = (coords[i][1], coords[i][0])
                point2 = (coords[i+1][1], coords[i+1][0])
                total_distance += geodesic(point1, point2).kilometers
    
    return total_distance

@st.cache_data(persist="disk", ttl=3600)
def load_map_data():
    """Load map data with optimized caching"""
    try:
        base_path = "/Users/nhiclap001/Desktop/MoH Leadership/Health Facility Mapping"
        
        # Load shapefiles
        rwanda = gpd.read_file(f"{base_path}/Shapefiles/Rwanda/rwa_adm0_2006_NISR_WGS1984_20181002.shp")
        district = gpd.read_file(f"{base_path}/Shapefiles/Rwanda/rwa_adm1_2006_NISR_WGS1984_20181002.shp")
        
        # Load facility data
        facility_file = f"{base_path}/Health Facility/Facility GIS_.xlsx"
        hp_df = pd.read_excel(facility_file, sheet_name='HP')
        hc_df = pd.read_excel(facility_file, sheet_name='HC')
        hosp_df = pd.read_excel(facility_file, sheet_name='HOSP')
        
        # Load road geometries with distance data
        hc_roads_path = f"{base_path}/Shapefiles/HC_to_hospital/Health_centers_to_Hospitals.gpkg"
        if not os.path.exists(hc_roads_path):
            hc_roads_path = f"{base_path}/shapefiles/HC_to_hospital/Health_centers_to_Hospitals.gpkg"
        hc_roads = gpd.read_file(hc_roads_path)
        
        # Convert distance from meters to kilometers
        if 'Dist_hosp' in hc_roads.columns:
            hc_roads['distance_km'] = hc_roads['Dist_hosp'] / 1000.0
        
        hosp_roads_path = f"{base_path}/Shapefiles/Hospital_to_NTH/Hospitals_to_NTH_1.gpkg"
        if not os.path.exists(hosp_roads_path):
            hosp_roads_path = f"{base_path}/shapefiles/Hospital_to_NTH/Hospitals_to_NTH_1.gpkg"
        hosp_roads = gpd.read_file(hosp_roads_path)
        
        # Create GeoDataFrames
        hp_geometry = [Point(xy) for xy in zip(hp_df['Longitude'], hp_df['Latitude'])]
        hp_gdf = gpd.GeoDataFrame(hp_df, geometry=hp_geometry, crs='EPSG:4326')
        
        hc_geometry = [Point(xy) for xy in zip(hc_df['Longitude'], hc_df['Latitude'])]
        hc_gdf = gpd.GeoDataFrame(hc_df, geometry=hc_geometry, crs='EPSG:4326')
        hc_gdf['HC_Name'] = hc_gdf['Health center']
        
        # Define specific Medicalized Health Centers
        medicalized_health_centers = [
            'Rutare (Gicumbi) MHC', 'Gikonko (Gisagara) MHC', 'Bweyeye MHC',
            'Remera (Gasabo) MHC', 'Mahama refugee camp II MHC', 'Gatenga MHC',
            'Nyabitimbo MHC', 'Kanyinya MHC', 'Ngeruka MHC', 'Nyarurenzi MHC',
            'Bigogwe MHC'
        ]
        
        # Load HMIS data to get facility categories
        try:
            facility_summary, _ = load_real_hmis_data()
            if not facility_summary.empty and 'name' in facility_summary.columns and 'facility_category' in facility_summary.columns:
                # Create a mapping of facility names to categories
                category_map = facility_summary[['name', 'facility_category']].drop_duplicates().set_index('name')['facility_category'].to_dict()
                # Map categories to health centers using HC_Name first
                hc_gdf['facility_category'] = hc_gdf['HC_Name'].map(category_map)
                # Also try with alternative name column if first mapping didn't work well
                unmapped = hc_gdf['facility_category'].isna()
                if unmapped.any():
                    hc_gdf.loc[unmapped, 'facility_category'] = hc_gdf.loc[unmapped, 'Health center'].map(category_map)
        except:
            # If we can't load categories, continue without them
            pass
        
        # Ensure specific MHCs are properly categorized
        for mhc_name in medicalized_health_centers:
            # Check both HC_Name and Health center columns for matches
            mask_hc_name = hc_gdf['HC_Name'].str.contains(mhc_name.replace(' MHC', ''), case=False, na=False)
            mask_health_center = hc_gdf['Health center'].str.contains(mhc_name.replace(' MHC', ''), case=False, na=False)
            hc_gdf.loc[mask_hc_name | mask_health_center, 'facility_category'] = 'Medicalized Health Center'
        
        # Fill any remaining NaN values with 'Health Center'
        hc_gdf['facility_category'] = hc_gdf['facility_category'].fillna('Health Center')
        
        # Add hospital referral mapping to health centers
        hc_to_hospital = {}
        for _, road in hc_roads.iterrows():
            hc_name = road.get('HC_Name', '')
            hosp_name = road.get('Hosp_name', '')
            if hc_name and hosp_name:
                hc_to_hospital[hc_name] = hosp_name
        
        # Map hospitals to health centers
        hc_gdf['referral_hospital'] = hc_gdf['HC_Name'].map(hc_to_hospital)
        # Try alternative mapping if some are missing
        unmapped = hc_gdf['referral_hospital'].isna()
        if unmapped.any():
            hc_gdf.loc[unmapped, 'referral_hospital'] = hc_gdf.loc[unmapped, 'Health center'].map(hc_to_hospital)
        
        hosp_geometry = [Point(xy) for xy in zip(hosp_df['Longitude'], hosp_df['Latitude'])]
        hosp_gdf = gpd.GeoDataFrame(hosp_df, geometry=hosp_geometry, crs='EPSG:4326')
        
        # Create NRH dataframe
        nrh_data = [
            {'Hospital Name': 'CHUK', 'Latitude': -1.9536, 'Longitude': 30.0606},
            {'Hospital Name': 'CHUB', 'Latitude': -2.4667, 'Longitude': 28.8667},
            {'Hospital Name': 'RMH', 'Latitude': -1.9431, 'Longitude': 30.0616}
        ]
        nrh_df = pd.DataFrame(nrh_data)
        nrh_geometry = [Point(xy) for xy in zip(nrh_df['Longitude'], nrh_df['Latitude'])]
        nrh_gdf = gpd.GeoDataFrame(nrh_df, geometry=nrh_geometry, crs='EPSG:4326')
        
        return {
            'rwanda': rwanda,
            'district': district,
            'hp_gdf': hp_gdf,
            'hc_points': hc_gdf,
            'hosp_points': hosp_gdf,
            'nrh_gdf': nrh_gdf,
            'hc_roads': hc_roads,
            'hosp_roads': hosp_roads
        }
        
    except Exception as e:
        st.warning(f"Could not load map data: {e}")
        return None

def create_optimized_map(map_data, show_roads=True, show_health_posts=False, 
                         show_distances=True, show_travel_times=False,
                         selected_facility=None, show_hc=True, show_mhc=True,
                         show_hospitals=True, show_nrh=True, highlight_mhc_referrals=True,
                         selected_sub_district=None):
    """Create optimized map with batch processing and facility filtering"""
    
    # Check cache first (include all parameters in cache key)
    cache_key = f"{show_roads}_{show_health_posts}_{show_distances}_{show_travel_times}_{selected_facility}_{show_hc}_{show_mhc}_{show_hospitals}_{show_nrh}_{highlight_mhc_referrals}_{selected_sub_district}"
    if cache_key in st.session_state.map_cache:
        return st.session_state.map_cache[cache_key]
    
    if map_data is None:
        return None
    
    # Extract data
    hc_points = map_data.get('hc_points')
    hosp_points = map_data.get('hosp_points')
    nrh_gdf = map_data.get('nrh_gdf')
    hp_gdf = map_data.get('hp_gdf')
    hc_roads = map_data.get('hc_roads')
    hosp_roads = map_data.get('hosp_roads')
    district = map_data.get('district')
    rwanda = map_data.get('rwanda')
    
    # Filter by sub-district if selected
    if selected_sub_district and hc_points is not None and not hc_points.empty:
        # Load HMIS data to get sub-district mapping
        facility_summary, _ = load_real_hmis_data()
        if not facility_summary.empty and 'name' in facility_summary.columns and 'sub_district' in facility_summary.columns:
            # Create a mapping of facility names to sub-districts
            sub_district_map = facility_summary[['name', 'sub_district']].drop_duplicates().set_index('name')['sub_district'].to_dict()
            
            # Add sub_district column to hc_points
            hc_points = hc_points.copy()
            hc_points['sub_district'] = hc_points['HC_Name'].map(sub_district_map)
            # Try alternative mapping if some are missing
            unmapped = hc_points['sub_district'].isna()
            if unmapped.any():
                hc_points.loc[unmapped, 'sub_district'] = hc_points.loc[unmapped, 'Health center'].map(sub_district_map)
            
            # Filter health centers by sub-district
            hc_points_filtered = hc_points[hc_points['sub_district'] == selected_sub_district].copy()
            
            # Get list of health centers in the selected sub-district
            selected_hcs = hc_points_filtered['HC_Name'].tolist()
            
            # Filter roads to only show connections from these health centers
            if hc_roads is not None and not hc_roads.empty:
                hc_roads_filtered = hc_roads[hc_roads['HC_Name'].isin(selected_hcs)].copy()
            else:
                hc_roads_filtered = hc_roads
            
            # Get the hospitals that these health centers refer to
            if hc_roads_filtered is not None and not hc_roads_filtered.empty:
                referral_hospitals = hc_roads_filtered['Hosp_name'].dropna().unique().tolist()
                # Filter hospital points to only show referral hospitals
                if hosp_points is not None and not hosp_points.empty:
                    hosp_points_filtered = hosp_points[hosp_points['Hospital Name'].isin(referral_hospitals)].copy()
                else:
                    hosp_points_filtered = hosp_points
            else:
                hosp_points_filtered = hosp_points
                
            # Use filtered data
            hc_points = hc_points_filtered
            hc_roads = hc_roads_filtered
            hosp_points = hosp_points_filtered
    
    # Initialize figure with all traces collected
    traces = []
    
    # Add district boundaries
    if district is not None and not district.empty:
        district_geojson = district.geometry.__geo_interface__
        traces.append(go.Choroplethmapbox(
            geojson=district_geojson,
            locations=district.index,
            colorscale=[[0, 'rgba(0, 0, 0, 0)'], [1, 'rgba(0, 0, 0, 0)']],
            z=np.zeros(len(district)),
            hoverinfo='skip',
            marker_line_width=0.5,
            marker_line_color='gray',
            showlegend=False,
            showscale=False
        ))
    
    # Add Rwanda boundaries
    if rwanda is not None and not rwanda.empty:
        rwanda_geojson = rwanda.geometry.__geo_interface__
        traces.append(go.Choroplethmapbox(
            geojson=rwanda_geojson,
            locations=rwanda.index,
            colorscale=[[0, 'rgba(0, 0, 0, 0)'], [1, 'rgba(0, 0, 0, 0)']],
            z=np.zeros(len(rwanda)),
            hoverinfo='skip',
            marker_line_color='darkgray',
            marker_line_width=0.5,
            showlegend=False,
            showscale=False
        ))
    
    # Batch process roads if enabled
    if show_roads:
        if hc_roads is not None and not hc_roads.empty:
            # Process roads (limit for performance)
            for idx, road in hc_roads.head(100).iterrows():
                road_geometry = road.geometry
                if road_geometry and road_geometry.geom_type == 'LineString':
                    lon, lat = map(list, road_geometry.xy)
                    
                    # Calculate distance
                    road_distance = road['distance_km'] if 'distance_km' in road else calculate_road_length(road_geometry)
                    hover_text = f"{road.get('HC_Name', 'HC')} → {road.get('Hosp_name', 'Hospital')}: {road_distance:.1f} km"
                    
                    # Add road trace
                    traces.append(go.Scattermapbox(
                        lat=lat,
                        lon=lon,
                        mode='lines',
                        hoverinfo='text',
                        hovertext=hover_text,
                        line=dict(width=1.5, color='rgba(100, 200, 255, 0.4)'),
                        showlegend=False
                    ))
                    
                    # Add distance label
                    if show_distances and len(lon) >= 2:
                        mid_idx = len(lon) // 2
                        label_text = f'{road_distance:.1f} km'
                        
                        # Add travel time if cached
                        if show_travel_times and 'Long_hc' in road and 'Lat_hc' in road:
                            cache_key = f"{road['Long_hc']}_{road['Lat_hc']}_{road['Long_hosp']}_{road['Lat_hosp']}"
                            if cache_key in st.session_state.travel_time_cache:
                                label_text += f' ({st.session_state.travel_time_cache[cache_key]:.1f}h)'
                        
                        traces.append(go.Scattermapbox(
                            mode='text',
                            lon=[lon[mid_idx]],
                            lat=[lat[mid_idx]],
                            text=label_text,
                            textfont=dict(size=8, color='white', family='Arial'),
                            showlegend=False,
                            hoverinfo='skip'
                        ))
    
    # Add health posts if enabled
    if show_health_posts and hp_gdf is not None and not hp_gdf.empty:
        traces.append(go.Scattermapbox(
            mode='markers',
            lon=hp_gdf.geometry.x,
            lat=hp_gdf.geometry.y,
            marker=dict(size=3, color='lightgray', opacity=0.6),
            text=hp_gdf.get('Facility Name', hp_gdf.index),
            hovertemplate='<b>Health Post</b><br>%{text}<extra></extra>',
            showlegend=False,
            name='Health Posts'
        ))
    
    # Add health centers with different colors for Medicalized Health Centers
    if hc_points is not None and not hc_points.empty:
        # Check if we have facility category information
        if 'facility_category' in hc_points.columns:
            # Separate regular health centers and medicalized health centers
            regular_hc = hc_points[hc_points['facility_category'] == 'Health Center']
            medicalized_hc = hc_points[hc_points['facility_category'] == 'Medicalized Health Center']
            
            # Add regular health centers (blue)
            if show_hc and not regular_hc.empty:
                if selected_facility and selected_facility in regular_hc['HC_Name'].values:
                    # Highlight selected facility
                    selected = regular_hc[regular_hc['HC_Name'] == selected_facility]
                    others = regular_hc[regular_hc['HC_Name'] != selected_facility]
                    
                    if not others.empty:
                        traces.append(go.Scattermapbox(
                            mode='markers',
                            lon=others.geometry.x,
                            lat=others.geometry.y,
                            marker=dict(size=8, color='#3498db', opacity=0.3),
                            text=others['HC_Name'],
                            hovertemplate='<b>Health Center</b><br>%{text}<extra></extra>',
                            showlegend=False,
                            name='Health Centers'
                        ))
                    
                    traces.append(go.Scattermapbox(
                        mode='markers',
                        lon=selected.geometry.x,
                        lat=selected.geometry.y,
                        marker=dict(size=15, color='red', opacity=1),
                        text=selected['HC_Name'],
                        hovertemplate='<b>SELECTED: Health Center</b><br>%{text}<extra></extra>',
                        showlegend=False,
                        name='Selected'
                    ))
                else:
                    traces.append(go.Scattermapbox(
                        mode='markers',
                        lon=regular_hc.geometry.x,
                        lat=regular_hc.geometry.y,
                        marker=dict(size=8, color='#3498db', opacity=0.8),
                        text=regular_hc['HC_Name'],
                        hovertemplate='<b>Health Center</b><br>%{text}<extra></extra>',
                        showlegend=False,
                        name='Health Centers'
                    ))
            
            # Add medicalized health centers (green)
            if show_mhc and not medicalized_hc.empty:
                if selected_facility and selected_facility in medicalized_hc['HC_Name'].values:
                    # Highlight selected facility
                    selected = medicalized_hc[medicalized_hc['HC_Name'] == selected_facility]
                    others = medicalized_hc[medicalized_hc['HC_Name'] != selected_facility]
                    
                    if not others.empty:
                        traces.append(go.Scattermapbox(
                            mode='markers',
                            lon=others.geometry.x,
                            lat=others.geometry.y,
                            marker=dict(size=10, color='#2ecc71', opacity=0.3),
                            text=others['HC_Name'],
                            hovertemplate='<b>Medicalized Health Center</b><br>%{text}<extra></extra>',
                            showlegend=False,
                            name='Medicalized HC'
                        ))
                    
                    traces.append(go.Scattermapbox(
                        mode='markers',
                        lon=selected.geometry.x,
                        lat=selected.geometry.y,
                        marker=dict(size=15, color='red', opacity=1),
                        text=selected['HC_Name'],
                        hovertemplate='<b>SELECTED: Medicalized Health Center</b><br>%{text}<extra></extra>',
                        showlegend=False,
                        name='Selected'
                    ))
                else:
                    traces.append(go.Scattermapbox(
                        mode='markers',
                        lon=medicalized_hc.geometry.x,
                        lat=medicalized_hc.geometry.y,
                        marker=dict(size=10, color='#2ecc71', opacity=0.9),
                        text=medicalized_hc['HC_Name'],
                        hovertemplate='<b>Medicalized Health Center</b><br>%{text}<extra></extra>',
                        showlegend=False,
                        name='Medicalized HC'
                    ))
        else:
            # No category info, show all as regular health centers
            if show_hc:
                traces.append(go.Scattermapbox(
                    mode='markers',
                    lon=hc_points.geometry.x,
                    lat=hc_points.geometry.y,
                    marker=dict(size=8, color='#3498db', opacity=0.8),
                    text=hc_points['HC_Name'],
                    hovertemplate='<b>Health Center</b><br>%{text}<extra></extra>',
                    showlegend=False,
                    name='Health Centers'
                ))
    
    # Add hospitals with P icon
    if show_hospitals and hosp_points is not None and not hosp_points.empty:
        if selected_facility and selected_facility in hosp_points['Hospital Name'].values:
            # Highlight selected hospital
            selected = hosp_points[hosp_points['Hospital Name'] == selected_facility]
            others = hosp_points[hosp_points['Hospital Name'] != selected_facility]
            
            if not others.empty:
                traces.append(go.Scattermapbox(
                    mode='markers+text',
                    lon=others.geometry.x,
                    lat=others.geometry.y,
                    text='P',
                    textfont=dict(size=14, color='white', family='Arial Black'),
                    textposition='middle center',
                    marker=dict(size=20, color='gold', opacity=0.3),
                    hovertext=others['Hospital Name'],
                    hovertemplate='<b>Hospital</b><br>%{hovertext}<extra></extra>',
                    showlegend=False,
                    name='Hospitals'
                ))
            
            traces.append(go.Scattermapbox(
                mode='markers+text',
                lon=selected.geometry.x,
                lat=selected.geometry.y,
                text='P',
                textfont=dict(size=18, color='white', family='Arial Black'),
                textposition='middle center',
                marker=dict(size=30, color='red', opacity=1),
                hovertext=selected['Hospital Name'],
                hovertemplate='<b>SELECTED: Hospital</b><br>%{hovertext}<extra></extra>',
                showlegend=False,
                name='Selected'
            ))
        else:
            traces.append(go.Scattermapbox(
                mode='markers+text',
                lon=hosp_points.geometry.x,
                lat=hosp_points.geometry.y,
                text='P',
                textfont=dict(size=14, color='white', family='Arial Black'),
                textposition='middle center',
                marker=dict(size=20, color='gold', opacity=0.9),
                hovertext=hosp_points['Hospital Name'],
                hovertemplate='<b>Hospital</b><br>%{hovertext}<extra></extra>',
                showlegend=False,
                name='Hospitals'
            ))
    
    # Add NRH with P icon
    if show_nrh and nrh_gdf is not None and not nrh_gdf.empty:
        traces.append(go.Scattermapbox(
            mode='markers+text',
            lon=nrh_gdf.geometry.x,
            lat=nrh_gdf.geometry.y,
            text='P',
            textfont=dict(size=16, color='white', family='Arial Black'),
            textposition='middle center',
            marker=dict(size=24, color='darkgoldenrod', opacity=1),
            hovertext=nrh_gdf.get('Hospital Name', 'NRH'),
            hovertemplate='<b>National Referral Hospital</b><br>%{hovertext}<extra></extra>',
            showlegend=False,
            name='National Referral Hospitals'
        ))
    
    # Create figure with all traces at once
    fig = go.Figure(data=traces)
    
    # Update layout
    fig.update_layout(
        mapbox=dict(
            style="carto-darkmatter",
            accesstoken=MAPBOX_TOKEN,
            zoom=6.5,
            center=dict(lat=-1.9403, lon=29.8739)
        ),
        margin={"r": 0, "t": 0, "l": 0, "b": 0},
        height=600,
        showlegend=False
    )
    
    # Cache the result
    st.session_state.map_cache[cache_key] = fig
    
    return fig

@st.cache_data
def analyze_facility_performance(facility_df, sub_district, metric):
    """Analyze facility performance with caching"""
    if metric not in facility_df.columns:
        return None, []
    
    sub_df = facility_df[facility_df['sub_district'] == sub_district].copy()
    
    if len(sub_df) == 0:
        return None, []
    
    sub_df_sorted = sub_df.sort_values(metric, ascending=False).reset_index(drop=True)
    average_value = sub_df_sorted[metric].mean()
    
    hospitals = sub_df_sorted[sub_df_sorted['facility_category'].isin([
        'District Hospital', 'Provincial Hospital', 'L2TH', 'Teaching Hospital', 'Referral Hospital'
    ])]
    
    hcs = sub_df_sorted[sub_df_sorted['facility_category'].isin([
        'Health Center', 'Medicalized Health Center'
    ])]
    
    outperformers = []
    if len(hospitals) > 0 and len(hcs) > 0:
        min_hospital_value = hospitals[metric].min()
        outperforming_hcs = hcs[hcs[metric] > min_hospital_value]
        outperformers = outperforming_hcs['name'].tolist()
    
    # Create optimized plot
    colors = []
    for _, row in sub_df_sorted.iterrows():
        if row['name'] in outperformers:
            colors.append('red')
        elif row['facility_category'] in ['District Hospital', 'Provincial Hospital', 'L2TH', 'Teaching Hospital', 'Referral Hospital']:
            colors.append('blue')
        else:
            colors.append('gold')
    
    # Create bar chart with facility names on x-axis and data labels
    # Separate the data by color for legend
    red_indices = [i for i, c in enumerate(colors) if c == 'red']
    blue_indices = [i for i, c in enumerate(colors) if c == 'blue']
    gold_indices = [i for i, c in enumerate(colors) if c == 'gold']
    
    fig = go.Figure()
    
    # Add red bars (HC/MHC outperforming hospitals)
    if red_indices:
        red_data = sub_df_sorted.iloc[red_indices]
        fig.add_trace(go.Bar(
            x=red_data['name'],
            y=red_data[metric],
            text=red_data[metric].apply(lambda x: f'{x:,.0f}'),
            textposition='outside',
            marker_color='red',
            name='HC/MHC Outperforming Hospitals',
            hovertemplate='<b>%{x}</b><br>' + METRIC_DESCRIPTIONS[metric] + ': %{y:,.0f}<extra></extra>',
            textfont=dict(size=10, color='white'),
            legendgroup='outperformers',
            showlegend=True
        ))
    
    # Add blue bars (Hospitals)
    if blue_indices:
        blue_data = sub_df_sorted.iloc[blue_indices]
        fig.add_trace(go.Bar(
            x=blue_data['name'],
            y=blue_data[metric],
            text=blue_data[metric].apply(lambda x: f'{x:,.0f}'),
            textposition='outside',
            marker_color='blue',
            name='Hospitals',
            hovertemplate='<b>%{x}</b><br>' + METRIC_DESCRIPTIONS[metric] + ': %{y:,.0f}<extra></extra>',
            textfont=dict(size=10, color='white'),
            legendgroup='hospitals',
            showlegend=True
        ))
    
    # Add gold bars (Health Centers/MHC)
    if gold_indices:
        gold_data = sub_df_sorted.iloc[gold_indices]
        fig.add_trace(go.Bar(
            x=gold_data['name'],
            y=gold_data[metric],
            text=gold_data[metric].apply(lambda x: f'{x:,.0f}'),
            textposition='outside',
            marker_color='gold',
            name='Health Centers/MHC',
            hovertemplate='<b>%{x}</b><br>' + METRIC_DESCRIPTIONS[metric] + ': %{y:,.0f}<extra></extra>',
            textfont=dict(size=10, color='white'),
            legendgroup='healthcenters',
            showlegend=True
        ))
    
    # Add average line
    fig.add_trace(go.Scatter(
        x=sub_df_sorted['name'].tolist(),
        y=[average_value] * len(sub_df_sorted),
        mode='lines',
        line=dict(color='white', width=2, dash='dash'),
        name='Average',
        hovertemplate='Average: %{y:.0f}<extra></extra>',
        showlegend=True
    ))
    
    fig.add_annotation(
        x=sub_df_sorted['name'].iloc[-1],  # Position at last facility name
        y=average_value,
        text=f"Avg: {average_value:,.0f}",
        showarrow=False,
        bgcolor='rgba(255,255,255,0.8)',
        font=dict(color='black', size=10),
        xanchor='right',
        yanchor='middle'
    )
    
    fig.update_layout(
        title=f"{METRIC_DESCRIPTIONS[metric]} - {sub_district} ({len(sub_df_sorted)} facilities)",
        xaxis_title="Health Facilities",
        yaxis_title=METRIC_DESCRIPTIONS[metric],
        height=500,  # Increased height for data labels
        margin=dict(t=80, b=150, l=80, r=40),  # Increased margins for labels
        xaxis=dict(
            tickangle=-45,  # Rotate x-axis labels
            tickmode='array',
            tickvals=sub_df_sorted['name'].tolist(),
            ticktext=[name[:25] + '...' if len(name) > 25 else name for name in sub_df_sorted['name']],  # Truncate long names
            tickfont=dict(size=10)
        ),
        yaxis=dict(
            gridcolor='rgba(128, 128, 128, 0.3)',  # Subtle grid lines
            zeroline=True,
            zerolinecolor='rgba(128, 128, 128, 0.5)'
        ),
        template="plotly_dark",
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="top",
            y=1.15,
            xanchor="center",
            x=0.5,
            bgcolor="rgba(0, 0, 0, 0.5)",
            bordercolor="white",
            borderwidth=1,
            font=dict(size=11, color='white')
        ),
        bargap=0.2  # Space between bars
    )
    
    return fig, outperformers

def main():
    st.title("🏥 Rwanda Healthcare Analytics Dashboard - Optimized")
    st.markdown("*High-performance version with all features*")
    
    # Load data with progress indicator
    with st.spinner('Loading data...'):
        facility_summary, is_real_data = load_real_hmis_data()
        map_data = load_map_data()
    
    if facility_summary is None or facility_summary.empty:
        st.error("❌ Could not load data")
        return
    
    # Get unique sub-districts
    if 'sub_district' in facility_summary.columns:
        sub_districts = facility_summary['sub_district'].dropna().unique()
        sub_districts = sorted([str(s) for s in sub_districts])
        
        if st.session_state.selected_sub_district is None and len(sub_districts) > 0:
            st.session_state.selected_sub_district = sub_districts[0]
    else:
        sub_districts = []
        st.session_state.selected_sub_district = None
    
    # Create tabs
    tab1, tab2, tab3, tab4 = st.tabs(["📍 Map", "📊 Facility Performance", "⚠️ Alerts", "📈 Statistics"])
    
    # TAB 1: MAP
    with tab1:
        st.markdown("### Rwanda Healthcare Referral Network Map")
        
        if map_data:
            col1, col2 = st.columns([3, 1])
            
            with col2:
                st.markdown("#### 📍 Sub-District Filter")
                
                # Add sub-district selector
                map_sub_district = st.selectbox(
                    "Select Sub-District:",
                    options=["All"] + sub_districts,
                    help="Filter map to show only facilities in selected sub-district"
                )
                
                if map_sub_district == "All":
                    map_sub_district = None
                
                st.markdown("#### 🔍 Find Facility")
                
                # Create list of all facilities for search
                all_facilities = []
                if 'hc_points' in map_data and map_data['hc_points'] is not None:
                    all_facilities.extend(map_data['hc_points']['HC_Name'].tolist())
                if 'hosp_points' in map_data and map_data['hosp_points'] is not None:
                    all_facilities.extend(map_data['hosp_points']['Hospital Name'].tolist())
                
                # Search/filter box
                selected_facility = st.selectbox(
                    "Search for a facility:",
                    options=["None"] + sorted(all_facilities),
                    help="Type to search for a specific health facility"
                )
                
                if selected_facility == "None":
                    selected_facility = None
                
                st.markdown("#### 🏥 Facility Types")
                show_hc = st.checkbox("Health Centers (Blue)", value=True)
                show_mhc = st.checkbox("Medicalized HC (Green)", value=True)
                show_hospitals = st.checkbox("Hospitals (Gold P)", value=True)
                show_nrh = st.checkbox("National Referral (Dark Gold P)", value=True)
                
                st.markdown("#### 🗺️ Map Options")
                show_roads = st.checkbox("Show Roads", value=True)
                highlight_mhc_referrals = st.checkbox("Highlight MHC Referral Network", value=True,
                                                     help="Show actual referral connections for Medicalized Health Centers")
                show_health_posts = st.checkbox("Show Health Posts", value=False)
                show_distances = st.checkbox("Show Distances", value=True)
                show_travel_times = st.checkbox("Show Travel Times", value=False, 
                                              help="Calculate real-time travel times (slower)")
                
                # Pre-calculate travel times if requested
                if show_travel_times and map_data.get('hc_roads') is not None:
                    if st.button("Calculate Travel Times"):
                        progress_bar = st.progress(0)
                        hc_roads = map_data['hc_roads']
                        total = min(20, len(hc_roads))
                        
                        for idx, road in hc_roads.head(total).iterrows():
                            if 'Long_hc' in road and 'Lat_hc' in road:
                                hc_coords = (road['Long_hc'], road['Lat_hc'])
                                hosp_coords = (road['Long_hosp'], road['Lat_hosp'])
                                travel_time = get_mapbox_travel_time(hc_coords, hosp_coords)
                                
                                if travel_time:
                                    cache_key = f"{road['Long_hc']}_{road['Lat_hc']}_{road['Long_hosp']}_{road['Lat_hosp']}"
                                    st.session_state.travel_time_cache[cache_key] = travel_time
                                
                                progress_bar.progress((idx + 1) / total)
                        
                        progress_bar.empty()
                        st.success(f"✅ Calculated {len(st.session_state.travel_time_cache)} travel times")
                
                st.markdown("#### 📊 Facility Counts")
                if 'hc_points' in map_data and map_data['hc_points'] is not None:
                    hc_data = map_data['hc_points']
                    if 'facility_category' in hc_data.columns:
                        regular_count = len(hc_data[hc_data['facility_category'] == 'Health Center'])
                        medicalized_count = len(hc_data[hc_data['facility_category'] == 'Medicalized Health Center'])
                        st.metric("🔵 Health Centers", regular_count)
                        st.metric("🟢 Medicalized HC", medicalized_count)
                    else:
                        st.metric("🏥 All Health Centers", len(hc_data))
                st.metric("🟡 Hospitals", len(map_data.get('hosp_points', [])))
                st.metric("⚪ Health Posts", len(map_data.get('hp_gdf', [])))
                st.metric("🟤 NRH", len(map_data.get('nrh_gdf', [])))
                
                # Show MHC Referral Network
                if highlight_mhc_referrals:
                    st.markdown("#### 🔗 MHC Referral Network")
                    with st.expander("View MHC → Hospital Connections"):
                        st.markdown("""
                        **Medicalized Health Center Referrals:**
                        - 🟢 Bigogwe MHC → Shyira DH
                        - 🟢 Bweyeye MHC → Bushenge PH
                        - 🟢 Gatenga MHC → Nyarugenge DH
                        - 🟢 Gikonko (Gisagara) MHC → Gakoma DH
                        - 🟢 Kanyinya MHC → Muhima DH
                        - 🟢 Mahama refugee camp II MHC → Kirehe DH
                        - 🟢 Ngeruka MHC → Nyamata DH
                        - 🟢 Nyabitimbo MHC → Mibilizi DH
                        - 🟢 Nyarurenzi MHC → Muhima DH
                        - 🟢 Remera (Gasabo) MHC → Kibagabaga DH
                        - 🟢 Rutare (Gicumbi) MHC → Byumba DH
                        """)
            
            with col1:
                # Create and display map with filters
                fig = create_optimized_map(
                    map_data,
                    show_roads=show_roads,
                    show_health_posts=show_health_posts,
                    show_distances=show_distances,
                    show_travel_times=show_travel_times,
                    selected_facility=selected_facility,
                    show_hc=show_hc,
                    show_mhc=show_mhc,
                    show_hospitals=show_hospitals,
                    show_nrh=show_nrh,
                    highlight_mhc_referrals=highlight_mhc_referrals,
                    selected_sub_district=map_sub_district
                )
                if fig:
                    st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Map data not available")
    
    # TAB 2: FACILITY PERFORMANCE
    with tab2:
        st.markdown("### Facility Performance Analysis by Sub-District")
        
        col1, col2 = st.columns([1, 3])
        
        with col1:
            selected_sub = st.selectbox(
                "Select Sub-District",
                options=sub_districts,
                index=sub_districts.index(st.session_state.selected_sub_district) if st.session_state.selected_sub_district in sub_districts else 0
            )
            
            selected_metric = st.selectbox(
                "Select Metric",
                options=[m for m in PERFORMANCE_METRICS if m in facility_summary.columns],
                format_func=lambda x: METRIC_DESCRIPTIONS[x]
            )
            
            # Update session state
            st.session_state.selected_sub_district = selected_sub
            st.session_state.selected_metric = selected_metric
        
        with col2:
            if selected_sub:
                fig, outperformers = analyze_facility_performance(
                    facility_summary, selected_sub, selected_metric
                )
                
                if fig:
                    st.plotly_chart(fig, use_container_width=True)
                    
                    if outperformers:
                        st.markdown("#### 🔴 Health Centers Outperforming Hospitals:")
                        for facility in outperformers:
                            st.write(f"🔴 {facility}")
                else:
                    st.info(f"No data available for {selected_sub}")
    
    # TAB 3: ALERTS
    with tab3:
        st.markdown("### ⚠️ Performance Alerts Dashboard")
        
        if st.session_state.selected_sub_district:
            st.info(f"Showing alerts for: {st.session_state.selected_sub_district}")
            alerts_data = facility_summary[facility_summary['sub_district'] == st.session_state.selected_sub_district]
        else:
            alerts_data = facility_summary
        
        # Find outperformers
        all_alerts = []
        sub_districts_for_alerts = [st.session_state.selected_sub_district] if st.session_state.selected_sub_district else alerts_data['sub_district'].dropna().unique()
        
        for sub_district in sub_districts_for_alerts:
            sub_df = alerts_data[alerts_data['sub_district'] == sub_district] if st.session_state.selected_sub_district else facility_summary[facility_summary['sub_district'] == sub_district]
            hospitals = sub_df[sub_df['facility_category'].isin([
                'District Hospital', 'Provincial Hospital', 'L2TH', 'Teaching Hospital', 'Referral Hospital'
            ])]
            hcs = sub_df[sub_df['facility_category'].isin(['Health Center', 'Medicalized Health Center'])]
            
            if len(hospitals) > 0 and len(hcs) > 0:
                for metric in PERFORMANCE_METRICS:
                    if metric in sub_df.columns:
                        min_hosp = hospitals[metric].min()
                        outperforming = hcs[hcs[metric] > min_hosp]
                        
                        for _, fac in outperforming.iterrows():
                            all_alerts.append({
                                'Facility': fac['name'],
                                'Sub-District': sub_district,
                                'Metric': METRIC_DESCRIPTIONS.get(metric, metric),
                                'Value': fac[metric],
                                'Min Hospital': min_hosp,
                                '% Above': ((fac[metric] - min_hosp) / min_hosp * 100) if min_hosp > 0 else 0
                            })
        
        if all_alerts:
            alerts_df = pd.DataFrame(all_alerts)
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Alerts", len(alerts_df))
            with col2:
                st.metric("Facilities with Alerts", alerts_df['Facility'].nunique())
            with col3:
                if len(alerts_df) > 0:
                    avg_excess = alerts_df['% Above'].mean()
                    st.metric("Avg % Above Hospital", f"{avg_excess:.1f}%")
            
            st.dataframe(alerts_df.round(1), use_container_width=True)
        else:
            st.success("✅ No performance alerts")
    
    # TAB 4: STATISTICS
    with tab4:
        st.markdown("### 📈 Statistical Overview")
        
        if st.session_state.selected_sub_district:
            st.info(f"Showing statistics for: {st.session_state.selected_sub_district}")
            stats_data = facility_summary[facility_summary['sub_district'] == st.session_state.selected_sub_district]
        else:
            stats_data = facility_summary
        
        metric_cols = [col for col in PERFORMANCE_METRICS if col in stats_data.columns]
        if metric_cols:
            stats = stats_data[metric_cols].describe()
            st.dataframe(stats.round(1), use_container_width=True)
            
            col1, col2 = st.columns(2)
            
            with col1:
                metric = st.selectbox(
                    "Select metric for distribution",
                    options=metric_cols,
                    format_func=lambda x: METRIC_DESCRIPTIONS[x],
                    key="dist"
                )
                
                if 'facility_category' in stats_data.columns:
                    fig = px.histogram(
                        stats_data,
                        x=metric,
                        color='facility_category',
                        title=f"Distribution of {METRIC_DESCRIPTIONS[metric]}",
                        template="plotly_dark"
                    )
                    st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                if 'facility_category' in stats_data.columns:
                    fig2 = px.box(
                        stats_data,
                        y=metric,
                        x='facility_category',
                        title=f"{METRIC_DESCRIPTIONS[metric]} by Facility Type",
                        template="plotly_dark"
                    )
                    st.plotly_chart(fig2, use_container_width=True)
            
            st.markdown("### 🏆 Top 10 Performers")
            top_performers = stats_data.nlargest(10, metric)[['name', 'sub_district', 'facility_category', metric]]
            st.dataframe(top_performers, use_container_width=True)
        else:
            st.warning("No metric data available for statistics")

if __name__ == "__main__":
    main()