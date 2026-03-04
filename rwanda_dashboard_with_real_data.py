"""
Rwanda Healthcare Analytics Dashboard - With Real HMIS Data Integration
This version attempts to load actual HMIS data with real facility-sub_district associations
"""

import streamlit as st
import pandas as pd
import numpy as np
import geopandas as gpd
from shapely.geometry import Point
import plotly.graph_objects as go
import plotly.express as px
import random
import warnings
import os
import sys
warnings.filterwarnings('ignore')

# Page configuration
st.set_page_config(
    page_title="Rwanda Healthcare Analytics Dashboard",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if 'map_cache' not in st.session_state:
    st.session_state.map_cache = {}

# Title and description
st.title("🏥 Rwanda Healthcare Analytics Dashboard")
st.markdown("Real-time analysis of healthcare referral networks with actual facility data")

# Performance metrics (matching notebook exactly)
PERFORMANCE_METRICS = [
    'ANC',
    'OPD_new', 
    'OPD_old',
    'OPD_total',  # Will be calculated from OPD_new + OPD_old
    'Deliveries',
    'Labor_referrals',
    'Obstetric_complication_referrals'
]

METRIC_DESCRIPTIONS = {
    'ANC': 'ANC Visits',
    'OPD_new': 'OPD New Cases',
    'OPD_old': 'OPD Old Cases',
    'OPD_total': 'Total OPD (New + Old)', 
    'Deliveries': 'Deliveries',
    'Labor_referrals': 'Labor Referrals',
    'Obstetric_complication_referrals': 'Obstetric Complication Referrals'
}

# Color schemes
COLOR_SCHEMES = {
    'hospitals': {
        'CHUK': '#e74c3c',
        'CHUB': '#3498db',
        'RMH': '#2ecc71',
        'KFH': '#f39c12',
        'default': '#95a5a6'
    }
}

@st.cache_data(ttl=3600)
def load_real_hmis_data():
    """Load and process HMIS data exactly as in the notebook"""
    base_path = "/Users/nhiclap001/Desktop/MoH Leadership/Health Facility Mapping/Health Centers"
    
    try:
        # Read the CSV file directly
        csv_file_path = f"{base_path}/df_final_opd.csv"
        st.info("Loading data from df_final_opd.csv...")
        
        df_final_opd = pd.read_csv(csv_file_path)
        
        # Check if data was loaded successfully
        if df_final_opd.empty:
            st.warning("CSV file is empty")
            return None, False
        
        # Filter for specified facility categories (exactly as in notebook)
        filtered_df = df_final_opd[df_final_opd['facility_category'].isin([
            'Health Center', 'District Hospital', 'L2TH',
            'Medicalized Health Center', 'Provincial Hospital',
            'Teaching Hospital', 'Referral Hospital'
        ])]
        
        # Sum all values per facility name and group by sub_district
        result = filtered_df.groupby(['dataElement', 'district','sub_district', 'sector', 'name', 'facility_category']).agg({
            'value': 'sum'
        }).reset_index()
        
        result = result.sort_values(['sub_district', 'value'], ascending=[True, False])
        
        # Define constants and mappings (exactly as in notebook)
        DATA_ELEMENT_MAP = {
            "ri0XrmXSpEC": "ANC",
            "T6H8cO1Tr5t": "OPD_new",
            "o73Sit5drOc": "OPD_old",
            "TWmX6JS19hO": "Deliveries",
            "o84exadtl82": "Labor_referrals",
            "fICuyReInRd": "Obstetric_complication_referrals"
        }
        
        GROUP_COLUMNS = [
            "district",
            "sector",
            "sub_district",
            "name",
            "facility_category"
        ]
        
        df = result.copy()
        
        # Keep only relevant data elements
        df_filtered = df[df["dataElement"].isin(DATA_ELEMENT_MAP.keys())]
        
        # Pivot and aggregate
        facility_summary = (
            df_filtered
            .assign(indicator=df_filtered["dataElement"].map(DATA_ELEMENT_MAP))
            .pivot_table(
                index=GROUP_COLUMNS,
                columns="indicator",
                values="value",
                aggfunc="sum",
                fill_value=0
            )
            .reset_index()
        )
        
        # Remove facilities with zero activity
        activity_columns = ["ANC", "OPD_new", "OPD_old", "Deliveries"]
        
        # Check if all activity columns exist
        existing_activity_cols = [col for col in activity_columns if col in facility_summary.columns]
        if existing_activity_cols:
            facility_summary = facility_summary[
                (facility_summary[existing_activity_cols] > 0).any(axis=1)
            ]
        
        # Create total OPD column
        if 'OPD_new' in facility_summary.columns and 'OPD_old' in facility_summary.columns:
            facility_summary["OPD_total"] = (
                facility_summary["OPD_new"] + facility_summary["OPD_old"]
            )
        else:
            facility_summary["OPD_total"] = 0
        
        st.success(f"Loaded {len(facility_summary)} facilities from df_final_opd.csv")
        
        # Display unique sub-districts found
        if 'sub_district' in facility_summary.columns:
            unique_sub_districts = facility_summary['sub_district'].nunique()
            st.info(f"Found {unique_sub_districts} unique sub-districts in the data")
        
        return facility_summary, True  # True indicates real data was loaded
        
    except Exception as e:
        st.warning(f"Could not load CSV data: {e}")
        st.info("Using sample data with realistic facility names...")
        return None, False

@st.cache_data(ttl=3600)
def create_sample_performance_data():
    """Create sample data with realistic Rwanda facility names and sub-districts"""
    
    # Actual sub-districts from df_final_opd
    sub_districts = [
        'Kibogora Sub District', 'Kabutare Sub District',
        'Rutongo Sub District', 'Kibungo Sub District',
        'Bushenge Sub District', 'Ruhengeri Sub District',
        'Nemba Sub District', 'Kinihira Sub District',
        'Muhororo Sub District', 'Kaduha Sub District',
        'Kiziguro Sub District', 'Kirinda Sub District',
        'Kigeme Sub District', 'Kibagabaga Sub District',
        'Nyanza Sub District', 'Masaka Sub District',
        'Mugonero Sub District', 'Remera Rukoma Sub District',
        'Shyira Sub District', 'Munini Sub District',
        'Nyamata Sub District', 'Nyarugenge Sub District',
        'Gisenyi Sub District', 'Rwamagana Sub District',
        'Ngarama Sub District', 'Kibuye Sub District',
        'Kabaya Sub District', 'Gahini Sub District',
        'Rwinkwavu Sub District', 'Nyabikenke Sub District',
        'Kabgayi Sub District', 'Muhima Sub District', 'Ruli Sub District',
        'Gakoma Sub District', 'Byumba Sub District',
        'Butaro Sub District', 'Ruhango Sub District',
        'Gatonde Sub District', 'Nyagatare Sub District',
        'Murunda Sub District', 'Gatunda Sub District',
        'Kibilizi Sub District', 'Kirehe Sub District',
        'Gitwe Sub District', 'Mibilizi Sub District',
        'Gihundwe Sub District'
    ]
    
    # Map each sub-district to realistic facility names
    sub_district_facilities = {
        'Kibogora Sub District': {
            'hospital': 'Kibogora DH',
            'health_centers': ['Kibogora CS', 'Nyarushishi CS', 'Gatare CS', 'Muganza CS', 'Nkombo CS']
        },
        'Kabutare Sub District': {
            'hospital': 'Kabutare DH',
            'health_centers': ['Kabutare CS', 'Gishamvu CS', 'Huye CS', 'Simbi CS', 'Maraba CS']
        },
        'Shyira Sub District': {
            'hospital': 'Shyira DH',
            'health_centers': ['Shyira CS', 'Bisate CS', 'Kinigi CS', 'Nyange CS', 'Jenda CS', 
                              'Gataraga CS', 'Cyuve CS', 'Kivuruga CS', 'Bugeshi CS', 
                              'Mukamira CS', 'Ngororero CS', 'Kabatwa CS', 'Nyabihu CS']
        },
        'Nyanza Sub District': {
            'hospital': 'Nyanza DH',
            'health_centers': ['Nyanza CS', 'Busasamana CS', 'Busoro CS', 'Cyabakamyi CS', 'Kibirizi CS']
        },
        'Rwamagana Sub District': {
            'hospital': 'Rwamagana DH',
            'health_centers': ['Rwamagana CS', 'Avega CS', 'Karenge CS', 'Gahengeri CS', 'Muyumbu CS']
        },
        # Add more mappings for other sub-districts
    }
    
    facilities = []
    
    for sub_district in sub_districts:
        # Get facility names for this sub-district
        if sub_district in sub_district_facilities:
            mapping = sub_district_facilities[sub_district]
            
            # Add hospital
            opd_new = np.random.randint(2000, 5000)
            opd_old = np.random.randint(1500, 4000)
            facilities.append({
                'name': mapping['hospital'],
                'district': sub_district.replace(' Sub District', ''),
                'sub_district': sub_district,
                'facility_category': 'District Hospital',
                'ANC': np.random.randint(800, 1500),
                'OPD_new': opd_new,
                'OPD_old': opd_old,
                'OPD_total': opd_new + opd_old,
                'Deliveries': np.random.randint(300, 800),
                'Labor_referrals': np.random.randint(10, 50),
                'Obstetric_complication_referrals': np.random.randint(5, 30)
            })
            
            # Add health centers
            for hc_name in mapping['health_centers']:
                outperform = np.random.random() < 0.15
                opd_new = np.random.randint(3500 if outperform else 500, 6000 if outperform else 1800)
                opd_old = np.random.randint(2500 if outperform else 400, 4500 if outperform else 1400)
                
                facilities.append({
                    'name': hc_name,
                    'district': sub_district.replace(' Sub District', ''),
                    'sub_district': sub_district,
                    'facility_category': 'Health Center',
                    'ANC': np.random.randint(1200 if outperform else 200, 1800 if outperform else 700),
                    'OPD_new': opd_new,
                    'OPD_old': opd_old,
                    'OPD_total': opd_new + opd_old,
                    'Deliveries': np.random.randint(400 if outperform else 50, 900 if outperform else 250),
                    'Labor_referrals': np.random.randint(30 if outperform else 2, 60 if outperform else 15),
                    'Obstetric_complication_referrals': np.random.randint(20 if outperform else 1, 40 if outperform else 10)
                })
        else:
            # For sub-districts without specific mapping, create generic names
            hospital_name = f"{sub_district.replace(' Sub District', '')} DH"
            opd_new = np.random.randint(2000, 5000)
            opd_old = np.random.randint(1500, 4000)
            
            facilities.append({
                'name': hospital_name,
                'district': sub_district.replace(' Sub District', ''),
                'sub_district': sub_district,
                'facility_category': 'District Hospital',
                'ANC': np.random.randint(800, 1500),
                'OPD_new': opd_new,
                'OPD_old': opd_old,
                'OPD_total': opd_new + opd_old,
                'Deliveries': np.random.randint(300, 800),
                'Labor_referrals': np.random.randint(10, 50),
                'Obstetric_complication_referrals': np.random.randint(5, 30)
            })
            
            # Add 5-10 health centers per sub-district
            num_hc = np.random.randint(5, 11)
            for i in range(num_hc):
                hc_name = f"{sub_district.replace(' Sub District', '')} CS{i+1}"
                outperform = np.random.random() < 0.15
                opd_new = np.random.randint(3500 if outperform else 500, 6000 if outperform else 1800)
                opd_old = np.random.randint(2500 if outperform else 400, 4500 if outperform else 1400)
                
                facilities.append({
                    'name': hc_name,
                    'district': sub_district.replace(' Sub District', ''),
                    'sub_district': sub_district,
                    'facility_category': 'Health Center',
                    'ANC': np.random.randint(1200 if outperform else 200, 1800 if outperform else 700),
                    'OPD_new': opd_new,
                    'OPD_old': opd_old,
                    'OPD_total': opd_new + opd_old,
                    'Deliveries': np.random.randint(400 if outperform else 50, 900 if outperform else 250),
                    'Labor_referrals': np.random.randint(30 if outperform else 2, 60 if outperform else 15),
                    'Obstetric_complication_referrals': np.random.randint(20 if outperform else 1, 40 if outperform else 10)
                })
    
    return pd.DataFrame(facilities)

@st.cache_data(ttl=3600)
def load_map_data():
    """Load map data"""
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
        hc_referral = pd.read_excel(facility_file, sheet_name='HC Referral')
        hosp_referral = pd.read_excel(facility_file, sheet_name='DH Referrals')
        nrh_df = pd.read_excel(facility_file, sheet_name='NRH')
        
        # Load road geometries
        hc_roads = gpd.read_file(f"{base_path}/shapefiles/HC_to_hospital/Health_centers_to_Hospitals.gpkg")
        hosp_roads = gpd.read_file(f"{base_path}/shapefiles/Hospital_to_NTH/Hospitals_to_NTH_1.gpkg")
        
        # Process data
        hp_geometry = [Point(xy) for xy in zip(hp_df['Longitude'], hp_df['Latitude'])]
        hp_gdf = gpd.GeoDataFrame(hp_df, geometry=hp_geometry, crs='EPSG:4326')
        
        hc_merged = pd.merge(hc_df, hc_referral, on='Health center', how='left', suffixes=('', '_ref'))
        hc_geometry = [Point(xy) for xy in zip(hc_merged['Longitude'], hc_merged['Latitude'])]
        hc_points = gpd.GeoDataFrame(hc_merged, geometry=hc_geometry, crs='EPSG:4326')
        hc_points['HC_Name'] = hc_points['Health center']
        hc_points['Hosp_name'] = hc_points['Hospital']
        
        hosp_merged = pd.merge(hosp_df, hosp_referral, on='Hospital Name', how='left', suffixes=('', '_ref'))
        hosp_geometry = [Point(xy) for xy in zip(hosp_merged['Longitude'], hosp_merged['Latitude'])]
        hosp_points = gpd.GeoDataFrame(hosp_merged, geometry=hosp_geometry, crs='EPSG:4326')
        
        nrh_geometry = [Point(xy) for xy in zip(nrh_df['Longitude'], nrh_df['Latitude'])]
        nrh_gdf = gpd.GeoDataFrame(nrh_df, geometry=nrh_geometry, crs='EPSG:4326')
        
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
        st.error(f"Error loading map data: {str(e)}")
        return None

@st.cache_data
def analyze_facility_performance(facility_df, sub_district, metric):
    """Analyze facility performance within a specific sub-district"""
    
    if metric not in facility_df.columns:
        return None, []
    
    # Filter to only show facilities in the selected sub-district
    sub_df = facility_df[facility_df['sub_district'] == sub_district].copy()
    
    if len(sub_df) == 0:
        return None, []
    
    # Sort facilities by metric value (highest first)
    sub_df_sorted = sub_df.sort_values(metric, ascending=False).reset_index(drop=True)
    
    # Calculate average
    average_value = sub_df_sorted[metric].mean()
    
    # Identify hospitals in this sub-district (matching notebook categories)
    hospitals = sub_df_sorted[sub_df_sorted['facility_category'].isin([
        'District Hospital', 'Provincial Hospital', 'L2TH', 'Teaching Hospital', 'Referral Hospital'
    ])]
    
    # Identify HC/MHC that outperform ANY hospital
    outperformers = []
    if len(hospitals) > 0:
        min_hospital_value = hospitals[metric].min()
        
        # Find HC/MHC that outperform the lowest performing hospital
        hc_mhc = sub_df_sorted[sub_df_sorted['facility_category'].isin([
            'Health Center', 'Medicalized Health Center'
        ])]
        
        for _, facility in hc_mhc.iterrows():
            if facility[metric] > min_hospital_value:
                outperformers.append(facility['name'])
    
    # Create colors (matching notebook logic)
    colors = []
    for _, facility in sub_df_sorted.iterrows():
        if facility['name'] in outperformers:
            colors.append('#FF0000')  # RED for HC/MHC outperforming hospitals
        elif facility['facility_category'] in ['District Hospital', 'Provincial Hospital', 'L2TH', 'Teaching Hospital', 'Referral Hospital']:
            colors.append('#4169E1')  # BLUE for hospitals
        else:
            colors.append('#FFD700')  # GOLD for regular health centers
    
    # Create figure
    fig = go.Figure()
    
    # Add bar chart
    fig.add_trace(go.Bar(
        x=sub_df_sorted['name'],
        y=sub_df_sorted[metric],
        marker_color=colors,
        text=sub_df_sorted[metric].round(0).astype(int),
        textposition='outside',
        name='Facilities'
    ))
    
    # Add average line
    fig.add_trace(go.Scatter(
        x=sub_df_sorted['name'],
        y=[average_value] * len(sub_df_sorted),
        mode='lines',
        name=f'Average ({average_value:.0f})',
        line=dict(color='white', width=2, dash='dash'),
        hovertemplate=f'Average: {average_value:.0f}<extra></extra>'
    ))
    
    # Add annotation for average
    fig.add_annotation(
        x=len(sub_df_sorted) - 1,
        y=average_value,
        text=f"Avg: {average_value:.0f}",
        showarrow=False,
        bgcolor='rgba(255,255,255,0.8)',
        font=dict(color='black', size=10),
        xanchor='right'
    )
    
    fig.update_layout(
        title=f"{METRIC_DESCRIPTIONS[metric]} - {sub_district} ({len(sub_df_sorted)} facilities)",
        xaxis_title="Facilities in Sub-District",
        yaxis_title=METRIC_DESCRIPTIONS[metric],
        height=400,
        margin=dict(t=50, b=100),
        xaxis_tickangle=-45,
        template="plotly_dark",
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    return fig, outperformers

def main():
    # Try to load data from CSV first
    facility_summary, is_real_data = load_real_hmis_data()
    
    # If no CSV data, use sample data
    if facility_summary is None:
        facility_summary = create_sample_performance_data()
        is_real_data = False
    
    # Load map data
    map_data = load_map_data()
    
    if is_real_data:
        st.success("✅ Using actual data from df_final_opd.csv")
    else:
        st.info("📊 Using sample data with realistic facility names")
    
    # Create tabs
    tab1, tab2, tab3, tab4 = st.tabs(["📍 Map", "📊 Facility Performance", "⚠️ Alerts", "📈 Statistics"])
    
    # TAB 2: FACILITY PERFORMANCE
    with tab2:
        st.markdown("### Facility Performance Analysis by Sub-District")
        
        if facility_summary.empty:
            st.warning("No facility performance data available")
            return
        
        # Get unique sub-districts
        sub_districts = facility_summary['sub_district'].dropna().unique()
        sub_districts = sorted([str(s) for s in sub_districts])
        
        col1, col2 = st.columns([1, 3])
        
        with col1:
            selected_sub = st.selectbox(
                "Select Sub-District",
                options=sub_districts
            )
            
            selected_metric = st.selectbox(
                "Select Metric",
                options=PERFORMANCE_METRICS,
                format_func=lambda x: METRIC_DESCRIPTIONS[x]
            )
            
            # Show facilities in selected sub-district
            sub_facilities = facility_summary[facility_summary['sub_district'] == selected_sub]
            st.info(f"📊 {len(sub_facilities)} facilities in {selected_sub}")
            
            # Breakdown by facility type
            if 'facility_category' in sub_facilities.columns:
                hc_count = len(sub_facilities[sub_facilities['facility_category'].str.contains('Health Center', na=False)])
                hosp_count = len(sub_facilities[sub_facilities['facility_category'].str.contains('Hospital', na=False)])
                st.markdown(f"• {hc_count} Health Centers")
                st.markdown(f"• {hosp_count} Hospitals")
            
            st.markdown("""
            **Color Coding:**
            - 🔴 RED = HC outperforming hospitals
            - 🔵 BLUE = Hospitals
            - 🟡 GOLD = Health Centers
            """)
        
        with col2:
            fig, outperformers = analyze_facility_performance(
                facility_summary,
                selected_sub,
                selected_metric
            )
            
            if fig:
                st.plotly_chart(fig, use_container_width=True)
                
                if outperformers:
                    st.error(f"⚠️ {len(outperformers)} Health Centers outperforming hospitals in {selected_sub}!")
                    for facility in outperformers:
                        st.write(f"🔴 {facility}")
            else:
                st.info(f"No data available for {selected_sub}")
    
    # TAB 3: ALERTS
    with tab3:
        st.markdown("### ⚠️ Performance Alerts Dashboard")
        
        # Find all outperformers
        all_alerts = []
        sub_districts_for_alerts = facility_summary['sub_district'].dropna().unique()
        
        for sub_district in sub_districts_for_alerts:
            sub_df = facility_summary[facility_summary['sub_district'] == sub_district]
            hospitals = sub_df[sub_df['facility_category'].str.contains('Hospital', na=False)]
            hcs = sub_df[sub_df['facility_category'].str.contains('Health Center', na=False)]
            
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
                                '% Above': ((fac[metric] - min_hosp) / min_hosp * 100)
                            })
        
        if all_alerts:
            alerts_df = pd.DataFrame(all_alerts)
            
            # Metrics
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Alerts", len(alerts_df))
            with col2:
                st.metric("Facilities", alerts_df['Facility'].nunique())
            with col3:
                avg_excess = alerts_df['% Above'].mean()
                st.metric("Avg % Above", f"{avg_excess:.1f}%")
            
            # Display top alerts
            st.dataframe(alerts_df.head(20), use_container_width=True)
        else:
            st.success("✅ No performance alerts")
    
    # TAB 4: STATISTICS
    with tab4:
        st.markdown("### 📈 Statistical Overview")
        
        # Summary statistics
        stats = facility_summary[PERFORMANCE_METRICS].describe()
        st.dataframe(stats.round(1), use_container_width=True)
        
        # Distribution charts
        col1, col2 = st.columns(2)
        
        with col1:
            metric = st.selectbox(
                "Select metric for distribution",
                options=PERFORMANCE_METRICS,
                format_func=lambda x: METRIC_DESCRIPTIONS[x],
                key="dist"
            )
            
            fig = px.histogram(
                facility_summary,
                x=metric,
                color='facility_category',
                title=f"Distribution of {METRIC_DESCRIPTIONS[metric]}",
                template="plotly_dark"
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            fig2 = px.box(
                facility_summary,
                y=metric,
                x='facility_category',
                title=f"{METRIC_DESCRIPTIONS[metric]} by Facility Type",
                template="plotly_dark"
            )
            st.plotly_chart(fig2, use_container_width=True)

if __name__ == "__main__":
    main()