# Rwanda Healthcare Analytics Dashboard

A comprehensive Streamlit dashboard for analyzing healthcare facility performance and referral networks across Rwanda's sub-districts.

## Features

- 📍 **Interactive Map**: Visualize healthcare referral network with Mapbox integration
- 📊 **Facility Performance Analysis**: Compare facility metrics across sub-districts
- ⚠️ **Smart Alerts**: Identify health centers outperforming hospitals
- 📈 **Statistical Overview**: Comprehensive metrics and comparisons
- 🔍 **Sub-District Filtering**: Focus on specific regions for detailed analysis
- 🏥 **Facility Categories**: Distinguish between Health Centers, Medicalized Health Centers, and Hospitals

## Key Metrics Tracked

- Antenatal Care (ANC) Visits
- Outpatient Department (OPD) Cases (New, Old, Total)
- Deliveries
- Labor Referrals
- Obstetric Complication Referrals

## Color Coding

- 🔵 **Blue**: Regular Health Centers
- 🟢 **Green**: Medicalized Health Centers
- 🟡 **Gold**: Hospitals
- 🔴 **Red**: HC/MHC outperforming hospitals

## Installation

1. Clone the repository:
```bash
git clone [repository-url]
cd [repository-name]
```

2. Install required packages:
```bash
pip install -r requirements.txt
```

3. Run the application:
```bash
streamlit run rwanda_dashboard_optimized_final.py
```

## Data Requirements

The dashboard requires the following data files:
- DHIS2 data export (CSV format)
- Facility GIS coordinates (Excel format)
- Shapefile data for roads and boundaries

## Usage

1. **Map Tab**: 
   - Select a sub-district to filter facilities
   - Search for specific facilities
   - Toggle facility types on/off
   - View referral connections

2. **Facility Performance Tab**:
   - Select sub-district and metric
   - View performance comparisons
   - Identify outperforming facilities

3. **Alerts Tab**:
   - Review facilities exceeding expected performance
   - Monitor critical metrics

4. **Statistics Tab**:
   - View overall statistics
   - Compare metrics across facilities

## Technologies Used

- Streamlit
- Plotly/Mapbox
- GeoPandas
- Pandas
- NumPy

## License

This project is licensed under the MIT License.

## Contact

For questions or support, please contact the MoH Leadership team.