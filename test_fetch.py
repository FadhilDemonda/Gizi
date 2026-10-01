import gspread
import pandas as pd
import json

with open(".streamlit/secrets.toml", "r") as f:
    import toml
    secrets = toml.load(f)

gc = gspread.service_account_from_dict(secrets["gcp_service_account"])
sh = gc.open_by_url(secrets["google_sheets"]["url"])
ws = sh.worksheet("master_barang")
raw_data = ws.get_all_records(numericise_ignore=["all"])

df = pd.DataFrame(raw_data)
print("Raw Stok Sekarang data types (numericise_ignore=['all']):")
for val in df['stok_sekarang'].head(5):
    print(repr(val), type(val))
