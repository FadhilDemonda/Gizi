import pandas as pd
import json

with open(".streamlit/secrets.toml", "r") as f:
    import toml
    secrets = toml.load(f)

import gspread
gc = gspread.service_account_from_dict(secrets["gcp_service_account"])
sh = gc.open_by_url(secrets["google_sheets"]["url"])
ws = sh.worksheet("master_barang")
raw_data = ws.get_all_records(numericise_ignore=["all"])
df = pd.DataFrame(raw_data)
item_options = df['nama_barang'].tolist()

default_names = ["Roti", "Buah", "Telur", "Snack", "Le Mineral 600", "Kopi KA", "Kopi 3 in 1", "Pocari", "Buavita"]
valid_defaults = []

for d in default_names:
    match = None
    for item in item_options:
        if d.lower() == str(item).lower():
            match = item
            break
            
    if not match:
        for item in item_options:
            if str(item).lower().startswith(d.lower()):
                match = item
                break
                
    if not match:
        for item in item_options:
            if d.lower() in str(item).lower():
                match = item
                break
                
    if not match and "kopi" in d.lower():
        for item in item_options:
            if "kopi" in str(item).lower():
                if item not in valid_defaults:
                    match = item
                    break
                    
    if match and match not in valid_defaults:
        valid_defaults.append(match)
        print(f"'{d}' matched '{match}'")
    else:
        print(f"'{d}' matched NOTHING or DUPLICATE ({match})")
