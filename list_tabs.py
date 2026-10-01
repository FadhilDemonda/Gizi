import streamlit as st
import gspread
import toml

def list_sheets():
    secrets = toml.load(".streamlit/secrets.toml")
    gc = gspread.service_account_from_dict(secrets["gcp_service_account"])
    sh = gc.open_by_url(secrets["google_sheets"]["url"])
    worksheets = sh.worksheets()
    for ws in worksheets:
        print(f"Tab: {ws.title}")

if __name__ == "__main__":
    list_sheets()
