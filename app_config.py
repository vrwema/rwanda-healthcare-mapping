"""
Configuration file for Rwanda Healthcare Dashboard
Update these paths based on your deployment environment
"""

import os

# Deployment mode: 'local' or 'cloud'
DEPLOYMENT_MODE = os.environ.get('DEPLOYMENT_MODE', 'local')

if DEPLOYMENT_MODE == 'local':
    # Local development paths
    BASE_PATH = "/Users/nhiclap001/Desktop/MoH Leadership/Health Facility Mapping"
    DATA_PATH = "/Users/nhiclap001/Desktop/MoH Leadership/Health Facility Mapping/Health Centers"
else:
    # Cloud deployment paths (relative to app directory)
    BASE_PATH = "."
    DATA_PATH = "."

# Data file paths
HMIS_DATA_PATH = os.path.join(DATA_PATH, "df_final_opd.csv")
FACILITY_GIS_PATH = os.path.join(BASE_PATH, "Health Facility", "Facility GIS_.xlsx")

# Shapefile paths
RWANDA_BOUNDARY_PATH = os.path.join(BASE_PATH, "Shapefiles", "Rwanda", "rwa_adm0_2006_NISR_WGS1984_20181002.shp")
DISTRICT_BOUNDARY_PATH = os.path.join(BASE_PATH, "Shapefiles", "Rwanda", "rwa_adm1_2006_NISR_WGS1984_20181002.shp")
HC_ROADS_PATH = os.path.join(BASE_PATH, "shapefiles", "HC_to_hospital", "Health_centers_to_Hospitals.gpkg")
HOSP_ROADS_PATH = os.path.join(BASE_PATH, "shapefiles", "Hospital_to_NTH", "Hospitals_to_NTH_1.gpkg")

# Alternative paths (if primary paths don't exist)
HC_ROADS_PATH_ALT = os.path.join(BASE_PATH, "Shapefiles", "HC_to_hospital", "Health_centers_to_Hospitals.gpkg")
HOSP_ROADS_PATH_ALT = os.path.join(BASE_PATH, "Shapefiles", "Hospital_to_NTH", "Hospitals_to_NTH_1.gpkg")

# Mapbox token (can be overridden by environment variable)
MAPBOX_TOKEN = os.environ.get('MAPBOX_TOKEN', 'your-mapbox-token-here')