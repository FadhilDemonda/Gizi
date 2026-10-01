import toml
import gspread
import pandas as pd

def test_read():
    secrets = toml.load(".streamlit/secrets.toml")
    gc = gspread.service_account_from_dict(secrets["gcp_service_account"])
    sh = gc.open_by_url(secrets["google_sheets"]["url"])
    ws = sh.worksheet("log")
    try:
        data = ws.get_all_records(numericise_ignore=["all"])
        print(f"Success! Read {len(data)} rows.")
    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    test_read()
