"""
Configuration file for Rwanda Healthcare Dashboard
Update these paths based on your deployment environment
"""

import os

# Get the directory where this script is located
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Data file paths (relative to the app directory)
HMIS_DATA_PATH = os.path.join(BASE_DIR, "df_final_opd.csv")
FACILITY_GIS_PATH = os.path.join(BASE_DIR, "Health Facility", "Facility GIS_.xlsx")

# Shapefile paths (relative to the app directory)
RWANDA_BOUNDARY_PATH = os.path.join(BASE_DIR, "Shapefiles", "Rwanda", "rwa_adm0_2006_NISR_WGS1984_20181002.shp")
DISTRICT_BOUNDARY_PATH = os.path.join(BASE_DIR, "Shapefiles", "Rwanda", "rwa_adm1_2006_NISR_WGS1984_20181002.shp")
HC_ROADS_PATH = os.path.join(BASE_DIR, "shapefiles", "HC_to_hospital", "Health_centers_to_Hospitals.gpkg")
HOSP_ROADS_PATH = os.path.join(BASE_DIR, "shapefiles", "Hospital_to_NTH", "Hospitals_to_NTH_1.gpkg")

# Alternative paths (if primary paths don't exist)
HC_ROADS_PATH_ALT = os.path.join(BASE_DIR, "Shapefiles", "HC_to_hospital", "Health_centers_to_Hospitals.gpkg")
HOSP_ROADS_PATH_ALT = os.path.join(BASE_DIR, "Shapefiles", "Hospital_to_NTH", "Hospitals_to_NTH_1.gpkg")

# Mapbox token (can be overridden by environment variable)
MAPBOX_TOKEN = os.environ.get('MAPBOX_TOKEN', 'your-mapbox-token-here')