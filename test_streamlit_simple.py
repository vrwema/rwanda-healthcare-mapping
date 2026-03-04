"""
Test Streamlit App - Rwanda Healthcare Referral Network Map
Simplified version without geopandas dependency
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px

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
    
    # Add access gap severity based on travel time
    hc_df['access_gap_severity'] = pd.cut(
        hc_df['Travel_Time_RealTime_Hours'],
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
    
    # Sample health posts
    n_hp = 30
    hp_data = {
        'Facility Name': [f'Health Post {i+1}' for i in range(n_hp)],
        'latitude': np.random.uniform(-2.5, -1.0, n_hp),
        'longitude': np.random.uniform(28.8, 30.5, n_hp)
    }
    hp_df = pd.DataFrame(hp_data)
    
    return hc_df, hosp_df, hp_df

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

def create_map(hc_df, hosp_df, hp_df, show_access_gaps=False, filters=None):
    """Create the interactive map"""
    
    # Apply filters
    filtered_hc = hc_df.copy()
    if filters:
        if 'district' in filters and filters['district']:
            filtered_hc = filtered_hc[filtered_hc['District'].isin(filters['district'])]
        if 'max_travel_time' in filters:
            filtered_hc = filtered_hc[filtered_hc['Travel_Time_RealTime_Hours'] <= filters['max_travel_time']]
    
    # Initialize figure
    fig = go.Figure()
    
    # Add health posts (small gray markers)
    fig.add_trace(go.Scattermapbox(
        lat=hp_df['latitude'],
        lon=hp_df['longitude'],
        mode='markers',
        marker=dict(size=4, color='gray'),
        text=[f"Health Post: {name}" for name in hp_df['Facility Name']],
        hoverinfo='text',
        name='Health Posts',
        showlegend=True
    ))
    
    # Add health centers with color coding
    if show_access_gaps:
        # Color by access gap severity
        colors = [COLOR_SCHEMES['access_gaps'][severity] for severity in filtered_hc['access_gap_severity']]
        sizes = [12 if severity == 'critical' else 8 for severity in filtered_hc['access_gap_severity']]
    else:
        # Color by referral hospital
        colors = [COLOR_SCHEMES['hospitals'].get(hosp, COLOR_SCHEMES['hospitals']['default']) 
                 for hosp in filtered_hc['Hosp_name']]
        sizes = [8] * len(filtered_hc)
    
    hover_texts = []
    for _, row in filtered_hc.iterrows():
        hover_text = (
            f"<b>{row['HC_Name']}</b><br>"
            f"District: {row['District']}<br>"
            f"Referral Hospital: {row['Hosp_name']}<br>"
            f"Distance: {row['Dist_hosp']:.1f} km<br>"
            f"Travel Time: {row['Travel_Time_RealTime_Hours']:.2f} hours"
        )
        if show_access_gaps:
            hover_text += f"<br>Access Gap: <b>{row['access_gap_severity'].upper()}</b>"
        hover_texts.append(hover_text)
    
    fig.add_trace(go.Scattermapbox(
        lat=filtered_hc['latitude'],
        lon=filtered_hc['longitude'],
        mode='markers',
        marker=dict(size=sizes, color=colors),
        text=hover_texts,
        hoverinfo='text',
        name='Health Centers',
        showlegend=True
    ))
    
    # Add hospitals
    for _, row in hosp_df.iterrows():
        color = COLOR_SCHEMES['hospitals'].get(row['Hospital Name'], COLOR_SCHEMES['hospitals']['default'])
        
        hover_text = (
            f"<b>{row['Hospital Name']}</b><br>"
            f"Type: {'National Referral' if row['Refer to'] == 'National' else 'District Hospital'}<br>"
            f"Refers to: {row['Refer to']}"
        )
        
        fig.add_trace(go.Scattermapbox(
            lat=[row['latitude']],
            lon=[row['longitude']],
            mode='markers',
            marker=dict(size=15, color=color, symbol='hospital'),
            text=hover_text,
            hoverinfo='text',
            name=row['Hospital Name'],
            showlegend=True
        ))
    
    # Add referral lines (sample connections)
    if st.sidebar.checkbox("Show Referral Paths", value=False):
        for _, hc_row in filtered_hc.head(10).iterrows():  # Show first 10 for clarity
            hosp_row = hosp_df[hosp_df['Hospital Name'] == hc_row['Hosp_name']]
            if not hosp_row.empty:
                fig.add_trace(go.Scattermapbox(
                    lat=[hc_row['latitude'], hosp_row.iloc[0]['latitude']],
                    lon=[hc_row['longitude'], hosp_row.iloc[0]['longitude']],
                    mode='lines',
                    line=dict(width=1, color='rgba(150, 150, 150, 0.5)'),
                    hoverinfo='skip',
                    showlegend=False
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
        title="Rwanda Healthcare Referral Network" + (" - Access Gap Analysis" if show_access_gaps else ""),
        showlegend=True,
        legend=dict(
            yanchor="top",
            y=0.99,
            xanchor="left",
            x=0.01,
            bgcolor="rgba(255,255,255,0.8)",
            font=dict(size=10)
        )
    )
    
    return fig

def main():
    # Load sample data
    hc_df, hosp_df, hp_df = create_sample_data()
    
    # Sidebar filters
    st.sidebar.header("🔍 Filters")
    
    # District filter
    selected_districts = st.sidebar.multiselect(
        "Select Districts",
        options=sorted(hc_df['District'].unique()),
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
    show_access_gaps = st.sidebar.checkbox("Show Access Gaps", value=False, 
                                          help="Color-code facilities by travel time severity")
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
        filtered_hc = hc_df.copy()
        if filters['district']:
            filtered_hc = filtered_hc[filtered_hc['District'].isin(filters['district'])]
        filtered_hc = filtered_hc[filtered_hc['Travel_Time_RealTime_Hours'] <= filters['max_travel_time']]
        
        with col1:
            st.metric("🏥 Health Centers", len(filtered_hc))
        
        with col2:
            avg_travel = filtered_hc['Travel_Time_RealTime_Hours'].mean()
            st.metric("⏱️ Avg Travel Time", f"{avg_travel:.1f} hrs")
        
        with col3:
            critical = len(filtered_hc[filtered_hc['access_gap_severity'] == 'critical'])
            st.metric("🚨 Critical Gaps", critical, 
                     help="Facilities with >3 hours travel time")
        
        with col4:
            st.metric("🏨 Hospitals", len(hosp_df))
    
    # Create tabs
    tab1, tab2, tab3 = st.tabs(["📍 Map", "📊 Analysis", "📈 Statistics"])
    
    with tab1:
        # Create and display map
        with st.spinner("Generating map..."):
            fig = create_map(hc_df, hosp_df, hp_df, show_access_gaps, filters)
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
        analysis_df = hc_df.copy()
        if filters['district']:
            analysis_df = analysis_df[analysis_df['District'].isin(filters['district'])]
        analysis_df = analysis_df[analysis_df['Travel_Time_RealTime_Hours'] <= filters['max_travel_time']]
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Access gap distribution
            st.markdown("#### Distribution of Access Gaps")
            gap_counts = analysis_df['access_gap_severity'].value_counts()
            
            # Create a colored bar chart
            colors = [COLOR_SCHEMES['access_gaps'][level] for level in gap_counts.index]
            fig_bar = go.Figure(data=[
                go.Bar(x=gap_counts.index, y=gap_counts.values, 
                      marker_color=colors)
            ])
            fig_bar.update_layout(
                xaxis_title="Severity Level",
                yaxis_title="Number of Facilities",
                showlegend=False,
                height=300
            )
            st.plotly_chart(fig_bar, use_container_width=True)
            
        with col2:
            # Critical facilities table
            st.markdown("#### Critical Access Facilities")
            critical = analysis_df[analysis_df['access_gap_severity'] == 'critical'].copy()
            if not critical.empty:
                display_df = critical[['HC_Name', 'District', 'Travel_Time_RealTime_Hours', 'Dist_hosp']].copy()
                display_df.columns = ['Health Center', 'District', 'Travel (hrs)', 'Distance (km)']
                display_df['Travel (hrs)'] = display_df['Travel (hrs)'].round(2)
                display_df['Distance (km)'] = display_df['Distance (km)'].round(1)
                st.dataframe(display_df.head(10), hide_index=True)
            else:
                st.info("No critical access gaps found with current filters")
        
        # Upgrade recommendations
        st.markdown("### 🔄 Facility Upgrade Recommendations")
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### HC → MHC Candidates")
            # Identify candidates based on distance and travel time
            hc_upgrade = analysis_df[
                (analysis_df['Dist_hosp'] > 30) | 
                (analysis_df['Travel_Time_RealTime_Hours'] > 1.5)
            ].head(5)
            
            if not hc_upgrade.empty:
                st.write(f"Found {len(hc_upgrade)} candidates for upgrade to Medicalized Health Centers:")
                for _, row in hc_upgrade.iterrows():
                    st.write(f"• **{row['HC_Name']}** - {row['District']} "
                           f"({row['Dist_hosp']:.0f}km, {row['Travel_Time_RealTime_Hours']:.1f}hrs)")
            else:
                st.info("No upgrade candidates identified")
        
        with col2:
            st.markdown("#### MHC → Hospital Candidates")
            st.info("This analysis requires MHC-specific data. "
                   "Candidates would be identified based on population served and distance to nearest hospital.")
    
    with tab3:
        st.subheader("Network Statistics")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Travel time distribution
            fig_hist = px.histogram(
                hc_df,
                x='Travel_Time_RealTime_Hours',
                nbins=20,
                title="Travel Time Distribution",
                labels={'Travel_Time_RealTime_Hours': 'Travel Time (hours)', 'count': 'Number of Facilities'},
                color_discrete_sequence=['#3498db']
            )
            fig_hist.update_layout(height=350)
            st.plotly_chart(fig_hist, use_container_width=True)
        
        with col2:
            # Distance distribution
            fig_dist = px.histogram(
                hc_df,
                x='Dist_hosp',
                nbins=20,
                title="Distance Distribution",
                labels={'Dist_hosp': 'Distance to Hospital (km)', 'count': 'Number of Facilities'},
                color_discrete_sequence=['#2ecc71']
            )
            fig_dist.update_layout(height=350)
            st.plotly_chart(fig_dist, use_container_width=True)
        
        # Summary statistics
        st.markdown("### Summary Statistics")
        summary = hc_df[['Travel_Time_RealTime_Hours', 'Dist_hosp']].describe()
        summary.columns = ['Travel Time (hours)', 'Distance (km)']
        
        # Format the dataframe
        summary_display = summary.round(2).T
        st.dataframe(summary_display, use_container_width=True)
        
        # District comparison
        st.markdown("### Average Metrics by District")
        district_stats = hc_df.groupby('District').agg({
            'Travel_Time_RealTime_Hours': 'mean',
            'Dist_hosp': 'mean',
            'HC_Name': 'count'
        }).round(2)
        district_stats.columns = ['Avg Travel Time (hrs)', 'Avg Distance (km)', 'Facility Count']
        
        st.dataframe(district_stats, use_container_width=True)
        
        # Visual comparison
        fig_comparison = go.Figure()
        fig_comparison.add_trace(go.Bar(
            name='Avg Travel Time (hrs)',
            x=district_stats.index,
            y=district_stats['Avg Travel Time (hrs)'],
            marker_color='#3498db'
        ))
        fig_comparison.update_layout(
            title="Average Travel Time by District",
            xaxis_title="District",
            yaxis_title="Hours",
            height=350
        )
        st.plotly_chart(fig_comparison, use_container_width=True)
    
    # Footer with instructions
    st.markdown("---")
    with st.expander("📚 How to Connect Your Real Data"):
        st.markdown("""
        ### To use this map with your actual data from the notebook:
        
        1. **Export your data from the notebook:**
        ```python
        # Add this to your notebook
        hc_points.to_csv('hc_points.csv', index=False)
        hosp_points.to_csv('hosp_points.csv', index=False)
        hp_gdf.to_csv('hp_gdf.csv', index=False)
        ```
        
        2. **Update the data loading function:**
        ```python
        def load_real_data():
            hc_df = pd.read_csv('hc_points.csv')
            hosp_df = pd.read_csv('hosp_points.csv')
            hp_df = pd.read_csv('hp_gdf.csv')
            return hc_df, hosp_df, hp_df
        ```
        
        3. **Required columns:**
        - Health Centers: `HC_Name`, `District`, `Hosp_name`, `Dist_hosp`, `Travel_Time_RealTime_Hours`, `latitude`, `longitude`
        - Hospitals: `Hospital Name`, `Refer to`, `latitude`, `longitude`
        - Health Posts: `Facility Name`, `latitude`, `longitude`
        """)
    
    st.markdown("""
    <div style='text-align: center; color: gray; padding: 20px'>
        <p>Demo version with sample data | Connect your notebook data for full functionality</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()