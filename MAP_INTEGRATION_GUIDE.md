# Rwanda Healthcare Referral Network Map - Integration Guide

## Overview
This is a refactored, modular version of your existing Plotly + Mapbox referral network map, optimized for Streamlit integration with enhanced decision-making features.

## Key Features Preserved from Original
✅ **All your existing functionality:**
- Real-time travel time calculation (Mapbox API with OSRM fallback)
- Rich hover information (distance, travel time, referral links)
- Dark theme map styling
- Referral relationships (HC → Hospital → NTH)
- Color-coded facilities by referral hospital
- Administrative boundaries

## New Enhancements Added
🆕 **Decision-support features:**
- **Access Gap Visualization**: Highlights facilities with poor access (color-coded by severity)
- **Upgrade Candidates**: Identifies facilities suitable for upgrade (HC→MHC, MHC→Hospital)
- **Interactive Filters**: District, sub-district, travel time, distance thresholds
- **Layer Toggles**: Show/hide specific facility types and road networks
- **Performance Optimization**: Caching for API calls, optional data sampling
- **Streamlit Integration**: Ready-to-use components with sidebar controls

## File Structure
```
streamlit_referral_map.py     # Main map module with all functions
streamlit_app_example.py       # Example Streamlit application
MAP_INTEGRATION_GUIDE.md       # This guide
```

## Quick Integration with Your Notebook

### Step 1: Extract your data to pickle/parquet files
```python
# In your notebook, save the processed dataframes:
hp_gdf.to_pickle('data/hp_gdf.pkl')
hc_points.to_pickle('data/hc_points.pkl')
hosp_points.to_pickle('data/hosp_points.pkl')
nrh_gdf.to_pickle('data/nrh_gdf.pkl')
hc_road.to_pickle('data/hc_roads.pkl')
hosp_roads.to_pickle('data/hosp_roads.pkl')
district.to_pickle('data/district.pkl')
rwanda.to_pickle('data/rwanda.pkl')
```

### Step 2: Update the data loading in streamlit_app_example.py
```python
@st.cache_data
def load_data():
    return {
        'rwanda': pd.read_pickle('data/rwanda.pkl'),
        'district': pd.read_pickle('data/district.pkl'),
        'hp_gdf': pd.read_pickle('data/hp_gdf.pkl'),
        'hc_points': pd.read_pickle('data/hc_points.pkl'),
        'hosp_points': pd.read_pickle('data/hosp_points.pkl'),
        'nrh_gdf': pd.read_pickle('data/nrh_gdf.pkl'),
        'hc_roads': pd.read_pickle('data/hc_roads.pkl'),
        'hosp_roads': pd.read_pickle('data/hosp_roads.pkl')
    }
```

### Step 3: Add your Mapbox token
```python
# Create .streamlit/secrets.toml
MAPBOX_TOKEN = "your_mapbox_token_here"
```

### Step 4: Run the app
```bash
streamlit run streamlit_app_example.py
```

## Using the Map in Your Existing Code

### Simple Usage (minimal changes to your code)
```python
from streamlit_referral_map import create_referral_map

# Use your existing dataframes
fig = create_referral_map(
    hp_gdf=hp_gdf,
    hc_points=hc_points,
    hosp_points=hosp_points,
    nrh_gdf=nrh_gdf,
    hc_roads=hc_road,
    hosp_roads=hosp_roads,
    district_gdf=district,
    rwanda_gdf=rwanda,
    mapbox_token=mapbox_token,
    show_access_gaps=True,  # New feature
    show_upgrade_candidates=False  # New feature
)

# Display in Streamlit
st.plotly_chart(fig, use_container_width=True)
```

### Advanced Usage (with filters and controls)
```python
from streamlit_referral_map import (
    create_referral_map,
    create_streamlit_filters,
    display_map_metrics
)

# Create filters in sidebar
filters, show_layers, show_gaps, show_upgrades, sample, size = \
    create_streamlit_filters(hp_gdf, hc_points, hosp_points)

# Display metrics
display_map_metrics(hc_points, hosp_points, filters)

# Create map with all options
fig = create_referral_map(
    # Your data
    hp_gdf=hp_gdf, hc_points=hc_points, # etc...
    
    # User selections
    filters=filters,
    show_access_gaps=show_gaps,
    show_upgrade_candidates=show_upgrades,
    
    # Performance
    sample_facilities=sample,
    sample_size=size
)

st.plotly_chart(fig, use_container_width=True)
```

## Access Gap Severity Levels
- **Critical** (Red): Travel time > 3 hours
- **High** (Orange): Travel time 2-3 hours  
- **Moderate** (Yellow): Travel time 1.5-2 hours
- **Low** (Green): Travel time < 1.5 hours

## Upgrade Candidate Criteria
Default criteria (customizable via filters):
- **HC → MHC**: Distance > 30km OR travel time > 1.5 hours to hospital
- **MHC → Hospital**: Serves multiple HCs, distance > 50km to NTH

## Performance Tips
1. **Enable caching**: Already implemented with `@st.cache_data`
2. **Use sampling**: For large datasets, enable "Sample Facilities" option
3. **Batch API calls**: The code already batches travel time calculations
4. **Limit real-time calculations**: Consider pre-calculating travel times

## API Rate Limits
- Mapbox: 100,000 requests/month (free tier)
- OSRM: Unlimited but slower (used as fallback)

## Customization Examples

### Change color schemes
```python
from streamlit_referral_map import COLOR_SCHEMES

# Modify colors
COLOR_SCHEMES['hospitals']['CHUK'] = '#ff0000'  # Bright red
COLOR_SCHEMES['access_gaps']['critical'] = '#8b0000'  # Dark red
```

### Add custom filters
```python
# In create_streamlit_filters function
filters['population_threshold'] = st.slider(
    "Minimum Population Served",
    min_value=10000,
    max_value=200000,
    value=50000
)
```

### Add new metrics
```python
def display_custom_metrics(df):
    # Calculate your metrics
    avg_population = df['population'].mean()
    st.metric("Avg Population Served", f"{avg_population:,.0f}")
```

## Troubleshooting

### Map not displaying
- Check Mapbox token is valid
- Ensure all GeoDataFrames have valid geometries
- Verify CRS is EPSG:4326

### Slow performance
- Enable facility sampling
- Reduce number of real-time API calls
- Pre-calculate travel times where possible

### Missing data in hover
- Check column names match expected format
- Ensure data types are correct (numeric for distances/times)

## Required Dependencies
```
streamlit
plotly
geopandas
pandas
numpy
requests
shapely
```

## Support
For questions about the original map functionality, refer to your notebook.
For Streamlit-specific features, check the Streamlit documentation.