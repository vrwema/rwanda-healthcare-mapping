"""
Comprehensive Rwanda Healthcare Dashboard
Combines Referral Network Map with Facility Performance Analysis
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import requests
import time
from typing import Optional, Dict, List, Tuple
import json

# Page configuration
st.set_page_config(
    page_title="Rwanda Healthcare Analytics Dashboard",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        padding-left: 20px;
        padding-right: 20px;
        background-color: rgba(255, 255, 255, 0.05);
        border-radius: 5px 5px 0px 0px;
    }
    .stTabs [aria-selected="true"] {
        background-color: rgba(255, 255, 255, 0.1);
    }
    .metric-card {
        background-color: rgba(255, 255, 255, 0.05);
        padding: 20px;
        border-radius: 10px;
        margin-bottom: 20px;
    }
</style>
""", unsafe_allow_html=True)

# Title
st.title("🏥 Rwanda Healthcare Analytics Dashboard")
st.markdown("**Comprehensive analysis of referral networks and facility performance**")

# Initialize session state for data persistence
if 'data_loaded' not in st.session_state:
    st.session_state.data_loaded = False
    st.session_state.hc_data = None
    st.session_state.hosp_data = None
    st.session_state.facility_summary = None
    st.session_state.sub_districts = []

# Color schemes
COLOR_SCHEMES = {
    'facility_performance': {
        'hospital': '#4169E1',        # Blue for hospitals
        'health_center': '#FFD700',   # Gold for health centers
        'mhc': '#FFD700',             # Gold for MHC
        'outperformer': '#FF0000'     # Red for HC/MHC outperforming hospitals
    },
    'hospitals': {
        'CHUK': '#e74c3c',
        'CHUB': '#3498db',
        'RMH': '#2ecc71',
        'KFH': '#9b59b6',
        'default': '#95a5a6'
    },
    'access_gaps': {
        'critical': '#e74c3c',
        'high': '#e67e22',
        'moderate': '#f39c12',
        'low': '#2ecc71'
    }
}

# Performance metrics list
PERFORMANCE_METRICS = [
    'ANC',
    'OPD_new',
    'OPD_old',
    'Deliveries',
    'Labor_referrals',
    'Obstetric_complication_referrals'
]

METRIC_DESCRIPTIONS = {
    'ANC': 'Antenatal Care Registrations',
    'OPD_new': 'New OPD Cases',
    'OPD_old': 'Follow-up OPD Cases',
    'Deliveries': 'Total Deliveries',
    'Labor_referrals': 'Labor Referral Cases',
    'Obstetric_complication_referrals': 'Obstetric Complication Referrals'
}

@st.cache_data
def load_sample_data():
    """Load sample data for demonstration"""
    np.random.seed(42)
    
    # Generate sample sub-districts (46 total)
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
                'facility_category': np.random.choice(['District Hospital', 'Provincial Hospital']),
                'ANC': np.random.randint(800, 1500),
                'OPD_new': np.random.randint(2000, 5000),
                'OPD_old': np.random.randint(1500, 4000),
                'Deliveries': np.random.randint(300, 800),
                'Labor_referrals': np.random.randint(10, 50),
                'Obstetric_complication_referrals': np.random.randint(5, 30)
            })
        
        # Add 3-5 health centers per sub-district
        n_hc = np.random.randint(3, 6)
        for i in range(n_hc):
            # Some HCs might outperform hospitals (10% chance)
            outperformer = np.random.random() < 0.1
            base_values = {
                'ANC': np.random.randint(1200 if outperformer else 200, 1800 if outperformer else 700),
                'OPD_new': np.random.randint(3500 if outperformer else 500, 6000 if outperformer else 1800),
                'OPD_old': np.random.randint(2500 if outperformer else 400, 4500 if outperformer else 1400),
                'Deliveries': np.random.randint(400 if outperformer else 50, 900 if outperformer else 250),
                'Labor_referrals': np.random.randint(30 if outperformer else 2, 60 if outperformer else 15),
                'Obstetric_complication_referrals': np.random.randint(20 if outperformer else 1, 40 if outperformer else 10)
            }
            
            facilities.append({
                'name': f'{sub_district} HC {i+1}',
                'sub_district': sub_district,
                'district': np.random.choice(districts),
                'facility_category': np.random.choice(['Health Center', 'Medicalized Health Center']),
                **base_values
            })
    
    facility_df = pd.DataFrame(facilities)
    
    # Generate map data
    n_hc = 100
    hc_data = {
        'HC_Name': [f'Health Center {i+1}' for i in range(n_hc)],
        'District': np.random.choice(districts, n_hc),
        'Sub_District': np.random.choice(sub_districts[:20], n_hc),  # Use first 20 for map
        'Hosp_name': np.random.choice(['CHUK', 'CHUB', 'RMH', 'District Hospital A'], n_hc),
        'Dist_hosp': np.random.uniform(10, 100, n_hc),
        'Travel_Time_RealTime_Hours': np.random.uniform(0.5, 4.5, n_hc),
        'latitude': np.random.uniform(-2.5, -1.0, n_hc),
        'longitude': np.random.uniform(28.8, 30.5, n_hc)
    }
    hc_df = pd.DataFrame(hc_data)
    
    # Hospital data
    hosp_data = {
        'Hospital Name': ['CHUK', 'CHUB', 'RMH', 'District Hospital A'],
        'Refer to': ['National', 'National', 'National', 'CHUK'],
        'Distance to NTH': [0, 0, 0, 45],
        'latitude': [-1.95, -2.35, -1.85, -2.1],
        'longitude': [30.06, 28.9, 29.7, 29.3]
    }
    hosp_df = pd.DataFrame(hosp_data)
    
    return facility_df, hc_df, hosp_df, sub_districts

def create_referral_map(hc_df, hosp_df, show_roads=True, selected_districts=None):
    """
    Create the complete referral network map with all components
    """
    # Filter by selected districts if provided
    if selected_districts:
        hc_df = hc_df[hc_df['District'].isin(selected_districts)]
    
    # Initialize figure
    fig = go.Figure()
    
    # Add district boundaries (simplified - just a box around Rwanda)
    fig.add_trace(go.Scattermapbox(
        lat=[-2.5, -1.0, -1.0, -2.5, -2.5],
        lon=[28.8, 28.8, 30.5, 30.5, 28.8],
        mode='lines',
        line=dict(width=2, color='darkgray'),
        hoverinfo='skip',
        showlegend=False
    ))
    
    # Generate hospital colors
    hospital_colors = {}
    for hosp in hosp_df['Hospital Name'].unique():
        hospital_colors[hosp] = COLOR_SCHEMES['hospitals'].get(hosp, COLOR_SCHEMES['hospitals']['default'])
    
    # Add referral roads if enabled
    if show_roads:
        # Add roads from health centers to hospitals
        for _, hc_row in hc_df.iterrows():
            hosp_row = hosp_df[hosp_df['Hospital Name'] == hc_row['Hosp_name']]
            if not hosp_row.empty:
                color = hospital_colors.get(hc_row['Hosp_name'], 'gray')
                # Convert hex color to rgba with transparency
                if color.startswith('#'):
                    r = int(color[1:3], 16)
                    g = int(color[3:5], 16)
                    b = int(color[5:7], 16)
                    rgba_color = f'rgba({r},{g},{b},0.3)'
                else:
                    rgba_color = 'rgba(128,128,128,0.3)'  # Default gray with transparency
                
                fig.add_trace(go.Scattermapbox(
                    lat=[hc_row['latitude'], hosp_row.iloc[0]['latitude']],
                    lon=[hc_row['longitude'], hosp_row.iloc[0]['longitude']],
                    mode='lines',
                    line=dict(width=1, color=rgba_color),
                    hoverinfo='skip',
                    showlegend=False
                ))
    
    # Add health centers
    for hosp_name in hospital_colors:
        hc_subset = hc_df[hc_df['Hosp_name'] == hosp_name]
        if not hc_subset.empty:
            hover_texts = []
            for _, row in hc_subset.iterrows():
                hover_text = (
                    f"<b>{row['HC_Name']}</b><br>"
                    f"District: {row['District']}<br>"
                    f"Referral: {row['Hosp_name']}<br>"
                    f"Distance: {row['Dist_hosp']:.1f} km<br>"
                    f"Travel Time: {row['Travel_Time_RealTime_Hours']:.2f} hours"
                )
                hover_texts.append(hover_text)
            
            fig.add_trace(go.Scattermapbox(
                lat=hc_subset['latitude'],
                lon=hc_subset['longitude'],
                mode='markers',
                marker=dict(size=7, color=hospital_colors[hosp_name]),
                text=hover_texts,
                hoverinfo='text',
                name=f'HC → {hosp_name}',
                showlegend=True
            ))
    
    # Add hospitals
    for _, row in hosp_df.iterrows():
        color = hospital_colors.get(row['Hospital Name'], 'gold')
        size = 20 if row['Refer to'] == 'National' else 12
        
        hover_text = (
            f"<b>{row['Hospital Name']}</b><br>"
            f"Type: {'National Referral' if row['Refer to'] == 'National' else 'District Hospital'}<br>"
        )
        
        fig.add_trace(go.Scattermapbox(
            lat=[row['latitude']],
            lon=[row['longitude']],
            mode='markers',
            marker=dict(size=size, color=color, symbol='hospital'),
            text=hover_text,
            hoverinfo='text',
            name=row['Hospital Name'],
            showlegend=True
        ))
    
    # Update layout
    fig.update_layout(
        mapbox=dict(
            style="carto-darkmatter",
            zoom=6.5,
            center=dict(lat=-1.9403, lon=29.8739)
        ),
        margin={"r": 0, "t": 40, "l": 0, "b": 0},
        height=600,
        title="Rwanda Healthcare Referral Network",
        showlegend=True,
        legend=dict(
            yanchor="top",
            y=0.99,
            xanchor="left",
            x=0.01,
            bgcolor="rgba(0,0,0,0.7)",
            font=dict(color="white", size=10)
        )
    )
    
    return fig

def analyze_facility_performance(facility_df, sub_district, metric, show_alert=True):
    """
    Analyze facility performance for a specific sub-district and metric
    """
    # Filter for sub-district
    sub_df = facility_df[facility_df['sub_district'] == sub_district].copy()
    
    if len(sub_df) == 0:
        return None, []
    
    # Sort by metric value
    sub_df = sub_df.sort_values(metric, ascending=False).reset_index(drop=True)
    
    # Calculate average
    avg_value = sub_df[metric].mean()
    
    # Identify hospitals
    hospitals = sub_df[sub_df['facility_category'].isin([
        'District Hospital', 'Provincial Hospital', 'L2TH', 'Teaching Hospital'
    ])]
    
    # Find HC/MHC that outperform hospitals
    outperformers = []
    if len(hospitals) > 0:
        min_hospital_value = hospitals[metric].min()
        hc_mhc = sub_df[sub_df['facility_category'].isin([
            'Health Center', 'Medicalized Health Center'
        ])]
        
        for _, facility in hc_mhc.iterrows():
            if facility[metric] > min_hospital_value:
                outperformers.append(facility['name'])
    
    # Create visualization
    colors = []
    for _, facility in sub_df.iterrows():
        if facility['name'] in outperformers:
            colors.append(COLOR_SCHEMES['facility_performance']['outperformer'])
        elif facility['facility_category'] in ['District Hospital', 'Provincial Hospital']:
            colors.append(COLOR_SCHEMES['facility_performance']['hospital'])
        elif facility['facility_category'] == 'Medicalized Health Center':
            colors.append(COLOR_SCHEMES['facility_performance']['mhc'])
        else:
            colors.append(COLOR_SCHEMES['facility_performance']['health_center'])
    
    # Create plotly figure
    fig = go.Figure()
    
    # Add bars
    fig.add_trace(go.Bar(
        x=sub_df['name'],
        y=sub_df[metric],
        marker_color=colors,
        text=sub_df[metric],
        textposition='outside',
        hovertemplate='<b>%{x}</b><br>' +
                      f'{METRIC_DESCRIPTIONS[metric]}: %{{y}}<br>' +
                      '<extra></extra>'
    ))
    
    # Add average line
    fig.add_hline(
        y=avg_value,
        line_dash="dash",
        line_color="white",
        annotation_text=f"Average: {avg_value:.0f}",
        annotation_position="right"
    )
    
    # Update layout
    fig.update_layout(
        title=f"{METRIC_DESCRIPTIONS[metric]} - {sub_district}",
        xaxis_title="Facility",
        yaxis_title=METRIC_DESCRIPTIONS[metric],
        template="plotly_dark",
        height=500,
        showlegend=False,
        xaxis={'tickangle': -45}
    )
    
    return fig, outperformers

def create_comparison_matrix(facility_df, selected_districts=None, selected_metrics=None):
    """
    Create a matrix comparing all sub-districts across metrics
    """
    if selected_districts:
        facility_df = facility_df[facility_df['district'].isin(selected_districts)]
    
    if not selected_metrics:
        selected_metrics = PERFORMANCE_METRICS
    
    # Calculate averages by sub-district
    avg_data = facility_df.groupby('sub_district')[selected_metrics].mean()
    
    # Create heatmap
    fig = px.imshow(
        avg_data.T,
        labels=dict(x="Sub-District", y="Metric", color="Average Value"),
        aspect="auto",
        color_continuous_scale="RdYlGn",
        template="plotly_dark"
    )
    
    fig.update_layout(
        title="Performance Matrix: Sub-Districts vs Metrics",
        height=400
    )
    
    return fig

def identify_all_outperformers(facility_df):
    """
    Identify all HC/MHC that outperform hospitals across all metrics
    """
    all_outperformers = []
    
    for sub_district in facility_df['sub_district'].unique():
        sub_df = facility_df[facility_df['sub_district'] == sub_district]
        
        # Get hospitals in this sub-district
        hospitals = sub_df[sub_df['facility_category'].isin([
            'District Hospital', 'Provincial Hospital'
        ])]
        
        if len(hospitals) == 0:
            continue
        
        # Get HC/MHC
        hc_mhc = sub_df[sub_df['facility_category'].isin([
            'Health Center', 'Medicalized Health Center'
        ])]
        
        for metric in PERFORMANCE_METRICS:
            min_hospital = hospitals[metric].min()
            
            for _, facility in hc_mhc.iterrows():
                if facility[metric] > min_hospital:
                    all_outperformers.append({
                        'Sub-District': sub_district,
                        'Facility': facility['name'],
                        'Category': facility['facility_category'],
                        'Metric': metric,
                        'Value': facility[metric],
                        'Min Hospital Value': min_hospital,
                        'Difference': facility[metric] - min_hospital,
                        'Percentage Above': ((facility[metric] - min_hospital) / min_hospital * 100)
                    })
    
    return pd.DataFrame(all_outperformers)

# Main app
def main():
    # Load data
    with st.spinner("Loading data..."):
        facility_df, hc_df, hosp_df, sub_districts = load_sample_data()
        st.session_state.facility_summary = facility_df
        st.session_state.hc_data = hc_df
        st.session_state.hosp_data = hosp_df
        st.session_state.sub_districts = sub_districts
        st.session_state.data_loaded = True
    
    # Sidebar filters
    st.sidebar.header("🔍 Global Filters")
    
    selected_districts = st.sidebar.multiselect(
        "Select Districts",
        options=sorted(facility_df['district'].unique()),
        default=[]
    )
    
    st.sidebar.markdown("---")
    
    # Create tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📍 Referral Network Map",
        "📊 Facility Performance",
        "🔄 Comparison Matrix",
        "⚠️ Alerts & Outperformers",
        "📈 Statistics"
    ])
    
    # TAB 1: REFERRAL NETWORK MAP
    with tab1:
        st.header("Healthcare Referral Network")
        
        col1, col2 = st.columns([3, 1])
        
        with col2:
            st.markdown("### Map Options")
            show_roads = st.checkbox("Show Referral Roads", value=True)
            map_style = st.selectbox(
                "Map Style",
                ["carto-darkmatter", "carto-positron", "open-street-map", "stamen-terrain"]
            )
        
        with col1:
            # Create and display map
            map_fig = create_referral_map(
                st.session_state.hc_data,
                st.session_state.hosp_data,
                show_roads=show_roads,
                selected_districts=selected_districts if selected_districts else None
            )
            
            # Update map style if changed
            if map_style != "carto-darkmatter":
                map_fig.update_layout(mapbox_style=map_style)
            
            st.plotly_chart(map_fig, use_container_width=True)
        
        # Map statistics
        st.markdown("### Network Statistics")
        col1, col2, col3, col4 = st.columns(4)
        
        filtered_hc = st.session_state.hc_data
        if selected_districts:
            filtered_hc = filtered_hc[filtered_hc['District'].isin(selected_districts)]
        
        with col1:
            st.metric("Health Centers", len(filtered_hc))
        with col2:
            avg_distance = filtered_hc['Dist_hosp'].mean()
            st.metric("Avg Distance", f"{avg_distance:.1f} km")
        with col3:
            avg_travel = filtered_hc['Travel_Time_RealTime_Hours'].mean()
            st.metric("Avg Travel Time", f"{avg_travel:.1f} hrs")
        with col4:
            critical = len(filtered_hc[filtered_hc['Travel_Time_RealTime_Hours'] > 3])
            st.metric("Critical Access", critical, help="Facilities >3 hours from hospital")
    
    # TAB 2: FACILITY PERFORMANCE
    with tab2:
        st.header("Facility Performance Analysis")
        
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.markdown("### Analysis Options")
            
            # Sub-district selector
            selected_sub_district = st.selectbox(
                "Select Sub-District",
                options=sorted(st.session_state.sub_districts),
                index=0
            )
            
            # Metric selector
            selected_metric = st.selectbox(
                "Select Metric",
                options=PERFORMANCE_METRICS,
                format_func=lambda x: METRIC_DESCRIPTIONS[x]
            )
            
            # Show outperformers alert
            show_alerts = st.checkbox("Show Alerts", value=True)
            
            # Analysis description
            st.markdown(f"""
            ### Color Coding:
            - 🔴 **Red**: HC/MHC outperforming hospitals
            - 🔵 **Blue**: Hospitals
            - 🟡 **Gold**: Health Centers/MHC
            """)
        
        with col2:
            # Create performance chart
            perf_fig, outperformers = analyze_facility_performance(
                st.session_state.facility_summary,
                selected_sub_district,
                selected_metric,
                show_alerts
            )
            
            if perf_fig:
                st.plotly_chart(perf_fig, use_container_width=True)
                
                # Show alerts if there are outperformers
                if show_alerts and outperformers:
                    st.warning(f"""
                    ⚠️ **Alert for {selected_sub_district}**
                    
                    {len(outperformers)} Health Centers/MHCs are outperforming hospitals in {METRIC_DESCRIPTIONS[selected_metric]}:
                    """)
                    for facility in outperformers:
                        st.write(f"- 🔴 {facility}")
            else:
                st.info("No data available for selected sub-district")
        
        # Batch analysis option
        st.markdown("---")
        if st.button("📊 Generate Reports for All Sub-Districts"):
            with st.spinner("Generating reports..."):
                progress_bar = st.progress(0)
                total = len(st.session_state.sub_districts)
                
                for i, sub_district in enumerate(st.session_state.sub_districts):
                    # Update progress
                    progress_bar.progress((i + 1) / total)
                    
                    # Analysis would be done here
                    # In real implementation, you'd save these to files or display them
                
                st.success(f"Generated reports for all {total} sub-districts!")
    
    # TAB 3: COMPARISON MATRIX
    with tab3:
        st.header("Performance Comparison Matrix")
        
        # Metric selection for matrix
        matrix_metrics = st.multiselect(
            "Select Metrics to Compare",
            options=PERFORMANCE_METRICS,
            default=PERFORMANCE_METRICS[:3],
            format_func=lambda x: METRIC_DESCRIPTIONS[x]
        )
        
        if matrix_metrics:
            # Create comparison matrix
            matrix_fig = create_comparison_matrix(
                st.session_state.facility_summary,
                selected_districts if selected_districts else None,
                matrix_metrics
            )
            st.plotly_chart(matrix_fig, use_container_width=True)
            
            # Top performers
            st.markdown("### Top Performing Sub-Districts")
            
            avg_performance = st.session_state.facility_summary.groupby('sub_district')[matrix_metrics].mean()
            avg_performance['Total Score'] = avg_performance.mean(axis=1)
            top_performers = avg_performance.nlargest(10, 'Total Score')
            
            st.dataframe(
                top_performers.style.background_gradient(cmap='RdYlGn'),
                use_container_width=True
            )
        else:
            st.info("Select at least one metric to display the comparison matrix")
    
    # TAB 4: ALERTS & OUTPERFORMERS
    with tab4:
        st.header("⚠️ Alerts: HC/MHC Outperforming Hospitals")
        
        # Find all outperformers
        outperformers_df = identify_all_outperformers(st.session_state.facility_summary)
        
        if not outperformers_df.empty:
            # Summary metrics
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Alerts", len(outperformers_df))
            with col2:
                st.metric("Affected Sub-Districts", outperformers_df['Sub-District'].nunique())
            with col3:
                st.metric("Facilities Involved", outperformers_df['Facility'].nunique())
            
            # Filter options
            st.markdown("### Filter Alerts")
            col1, col2 = st.columns(2)
            
            with col1:
                filter_metric = st.selectbox(
                    "Filter by Metric",
                    options=['All'] + list(PERFORMANCE_METRICS),
                    format_func=lambda x: x if x == 'All' else METRIC_DESCRIPTIONS[x]
                )
            
            with col2:
                min_percentage = st.slider(
                    "Minimum % Above Hospital",
                    min_value=0,
                    max_value=100,
                    value=10,
                    step=5
                )
            
            # Apply filters
            filtered_outperformers = outperformers_df.copy()
            if filter_metric != 'All':
                filtered_outperformers = filtered_outperformers[
                    filtered_outperformers['Metric'] == filter_metric
                ]
            filtered_outperformers = filtered_outperformers[
                filtered_outperformers['Percentage Above'] >= min_percentage
            ]
            
            # Display filtered results
            st.markdown(f"### Showing {len(filtered_outperformers)} Alerts")
            
            if not filtered_outperformers.empty:
                # Create summary chart
                fig = px.bar(
                    filtered_outperformers.head(20),
                    x='Facility',
                    y='Percentage Above',
                    color='Metric',
                    title="Top 20 HC/MHC Outperforming Hospitals (%)",
                    template="plotly_dark",
                    hover_data=['Sub-District', 'Value', 'Min Hospital Value']
                )
                fig.update_layout(xaxis_tickangle=-45, height=400)
                st.plotly_chart(fig, use_container_width=True)
                
                # Detailed table
                st.markdown("### Detailed Alert List")
                display_df = filtered_outperformers[
                    ['Sub-District', 'Facility', 'Metric', 'Value', 
                     'Min Hospital Value', 'Percentage Above']
                ].copy()
                display_df['Percentage Above'] = display_df['Percentage Above'].round(1).astype(str) + '%'
                
                st.dataframe(
                    display_df.style.apply(
                        lambda x: ['background-color: rgba(255,0,0,0.3)' 
                                  if float(x['Percentage Above'].rstrip('%')) > 50 
                                  else '' for _ in x], axis=1
                    ),
                    use_container_width=True,
                    height=400
                )
            else:
                st.info("No alerts matching the selected criteria")
        else:
            st.success("✅ No HC/MHC are outperforming hospitals")
    
    # TAB 5: STATISTICS
    with tab5:
        st.header("📈 Statistical Analysis")
        
        # Overall statistics
        st.markdown("### Overall Performance Statistics")
        
        # Calculate statistics for all metrics
        stats_df = st.session_state.facility_summary[PERFORMANCE_METRICS].describe()
        st.dataframe(stats_df.round(1), use_container_width=True)
        
        # Distribution plots
        st.markdown("### Metric Distributions")
        
        col1, col2 = st.columns(2)
        
        with col1:
            metric1 = st.selectbox(
                "Select first metric",
                options=PERFORMANCE_METRICS,
                format_func=lambda x: METRIC_DESCRIPTIONS[x],
                key="stat_metric1"
            )
            
            fig1 = px.histogram(
                st.session_state.facility_summary,
                x=metric1,
                color='facility_category',
                title=f"Distribution of {METRIC_DESCRIPTIONS[metric1]}",
                template="plotly_dark",
                nbins=30
            )
            st.plotly_chart(fig1, use_container_width=True)
        
        with col2:
            metric2 = st.selectbox(
                "Select second metric",
                options=PERFORMANCE_METRICS,
                format_func=lambda x: METRIC_DESCRIPTIONS[x],
                key="stat_metric2",
                index=1
            )
            
            fig2 = px.box(
                st.session_state.facility_summary,
                y=metric2,
                x='facility_category',
                title=f"{METRIC_DESCRIPTIONS[metric2]} by Facility Type",
                template="plotly_dark"
            )
            st.plotly_chart(fig2, use_container_width=True)
        
        # Correlation analysis
        st.markdown("### Metric Correlations")
        
        corr_matrix = st.session_state.facility_summary[PERFORMANCE_METRICS].corr()
        
        fig_corr = px.imshow(
            corr_matrix,
            text_auto='.2f',
            color_continuous_scale='RdBu',
            title="Correlation Matrix of Performance Metrics",
            template="plotly_dark"
        )
        st.plotly_chart(fig_corr, use_container_width=True)
        
        # Insights
        st.markdown("### 💡 Key Insights")
        
        # Find strongest correlations
        corr_pairs = []
        for i in range(len(PERFORMANCE_METRICS)):
            for j in range(i+1, len(PERFORMANCE_METRICS)):
                corr_val = corr_matrix.iloc[i, j]
                if abs(corr_val) > 0.7:
                    corr_pairs.append({
                        'Metric 1': PERFORMANCE_METRICS[i],
                        'Metric 2': PERFORMANCE_METRICS[j],
                        'Correlation': corr_val
                    })
        
        if corr_pairs:
            st.write("**Strong Correlations Found:**")
            for pair in corr_pairs:
                if pair['Correlation'] > 0:
                    st.write(f"- {METRIC_DESCRIPTIONS[pair['Metric 1']]} and "
                           f"{METRIC_DESCRIPTIONS[pair['Metric 2']]} are strongly positively correlated "
                           f"({pair['Correlation']:.2f})")
                else:
                    st.write(f"- {METRIC_DESCRIPTIONS[pair['Metric 1']]} and "
                           f"{METRIC_DESCRIPTIONS[pair['Metric 2']]} are strongly negatively correlated "
                           f"({pair['Correlation']:.2f})")
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: gray; padding: 20px'>
        <p>Rwanda Healthcare Analytics Dashboard</p>
        <p style='font-size: 0.9em'>Comprehensive analysis of referral networks and facility performance</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()