import requests
import pandas as pd
import json
import numpy as np
import openpyxl

pd.set_option('display.max_columns', None)


def extract_dhis2_data(credential_file, data_element_file, start_date="2024-07-01", 
                       end_date="2025-06-30", org_unit="Hjw70Lodtf2"):
    """
    Extract and process DHIS2 maternal health data.
    
    Parameters:
    -----------
    credential_file : str
        Path to DHIS2_credential.json file
    data_element_file : str
        Path to data element Excel or CSV file (should have 'data_element_id' column)
    start_date : str
        Start date for data extraction (default: "2024-07-01")
    end_date : str
        End date for data extraction (default: "2025-06-30")
    org_unit : str
        Organization unit ID (default: "Hjw70Lodtf2")
    
    Returns:
    --------
    pd.DataFrame
        Processed dataframe with facility categories, period, and all relevant mappings
    """
    
    # ==================== LOAD CREDENTIALS ====================
    with open(credential_file, 'r') as f:
        config = json.load(f)
    
    username = config["username"]
    password = config["password"]
    national_id = config["national_id"]
    
    # ==================== LOAD DATA ELEMENTS ====================
    if data_element_file.endswith('.xlsx'):
        df_ele = pd.read_excel(data_element_file)
    else:  # CSV
        df_ele = pd.read_csv(data_element_file)
    
    # ==================== RETRIEVE DATA VALUES ====================
    url = "https://aggregate.moh.gov.rw/api/dataValueSets"
    auth = (username, password)
    
    de_ids = df_ele['data_element_id'].dropna().astype(str).tolist()
    
    all_records = []
    
    for de in de_ids:
        print(f"Fetching DE {de} for {start_date} → {end_date}...")
        params = {
            "dataElement": de,
            "startDate": start_date,
            "endDate": end_date,
            "orgUnit": org_unit,
            "children": "true"
        }
        
        resp = requests.get(url, params=params, auth=auth)
        if resp.status_code == 200:
            rows = resp.json().get("dataValues", [])
            if rows:
                all_records.extend(rows)
        else:
            print(f"Error {resp.status_code}: {resp.text[:300]}")
    
    df = pd.DataFrame(all_records)
    print(f"Total rows fetched: {len(df)}")
    
    # ==================== RETRIEVE CATEGORY OPTIONS ====================
    url = "https://aggregate.moh.gov.rw/api/categoryOptionCombos?paging=false"
    response = requests.get(url, auth=(username, password))
    
    if response.status_code == 200:
        data = response.json()
        data_1 = data.get("categoryOptionCombos", [])
        df_cat = pd.DataFrame(data_1)
    else:
        print(f"Failed to fetch category options: {response.status_code}, {response.text}")
        df_cat = pd.DataFrame()
    
    # ==================== RETRIEVE ORGANIZATION UNITS ====================
    url = "https://aggregate.moh.gov.rw/api/organisationUnits"
    params = {
        "paging": "false",
        "fields": "id,name,level,parent[id,name],path,ancestors[id,name,level],children[id,name]"
    }
    
    response = requests.get(url, params=params, auth=(username, password))
    
    if response.status_code == 200:
        data = response.json()
        units = data.get("organisationUnits", [])
        df_org = pd.json_normalize(units)
        
        df_org["province"] = df_org["ancestors"].apply(lambda x: x[1]["name"] if len(x) > 1 else None)
        df_org["district"] = df_org["ancestors"].apply(lambda x: x[2]["name"] if len(x) > 2 else None)
        df_org["sub_district"] = df_org["ancestors"].apply(lambda x: x[3]["name"] if len(x) > 3 else None)
        df_org["sector"] = df_org["ancestors"].apply(lambda x: x[4]["name"] if len(x) > 4 else None)
    else:
        print("Request failed:", response.status_code, response.text)
        df_org = pd.DataFrame()
    
    # ==================== MAP CATEGORY OPTIONS ====================
    id_to_name = dict(zip(df_cat['id'], df_cat['displayName']))
    df['category_option'] = df['categoryOptionCombo'].map(id_to_name)
    
    # ==================== MERGE WITH DATA ELEMENTS ====================
    df = pd.merge(df, df_ele, left_on='dataElement', 
                  right_on='data_element_id', how='left').drop(columns='data_element_id')
    
    df['value'] = pd.to_numeric(df['value'], errors='coerce').fillna(0)

    
    
    # ==================== MERGE WITH ORGANIZATIONS ====================
    df = pd.merge(
        df,
        df_org[['id', 'name', 'province', 'district', 'sub_district', 'sector']],
        left_on='orgUnit',
        right_on='id',
        how='left'
    )
    
    df = df.drop(columns=['id', 'storedBy', 'comment', 'followup'], errors='ignore')
    
    
    # ==================== CATEGORIZE FACILITIES ====================
    def categorize_facility(facility_name):
        """Categorize facilities based on facility name patterns"""
        if pd.isna(facility_name):
            return "Unknown"
        
        facility_name = str(facility_name).upper()
        
        if " DH" in facility_name:
            return "District Hospital"
        elif " L2TH" in facility_name:
            return "L2TH"
        elif " RH" in facility_name:
            return "Referral Hospital"
        elif " PH" in facility_name:
            return "Provincial Hospital"
        elif any(keyword in facility_name for keyword in [" CS", " HC", " HEALTH CENTER", " CENTRE DE SANTE"]):
            return "Health Center"
        elif " MHC" in facility_name:
            return "Medicalized Health Center"
        elif any(keyword in facility_name for keyword in ["CHUK", "CHK", "KING FAISAL","CHU","CHUB","UNR" ,"RWANDA MILITARY"]):
            return "Teaching Hospital"
        elif any(keyword in facility_name for keyword in [" HP",")HP", " POSTE DE SANTE", " HEALTH POST"," PS"," SGHP"," 2nd GHP",
                                                          " Post secondaire",' Poste secondaire',"Poste","Post", "POST"," 2nd GHP",
                                                          "GHP","secondaire"]):
            return "Health Post"
        else:
            return "Private Clinic and Hospital"
    
    df['facility_category'] = df['name'].apply(categorize_facility)
    df["period"] = pd.to_datetime(df["period"], format="%Y%m")
    
    return df