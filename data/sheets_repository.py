import pandas as pd
import gspread
from gspread_dataframe import set_with_dataframe
import streamlit as st
import logging

# Configure logger
logger = logging.getLogger(__name__)

MASTER_CSV = "master_barang"
TRANSAKSI_CSV = "transaksi"

@st.cache_data(ttl=60)
def load_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Load data from Google Sheets, cached for performance.
    
    Returns:
        tuple[pd.DataFrame, pd.DataFrame]: A tuple containing master_df and transaksi_df.
    """
    try:
        gc = gspread.service_account_from_dict(st.secrets["gcp_service_account"])
        sh = gc.open_by_url(st.secrets["google_sheets"]["url"])
        
        ws_master = sh.worksheet(MASTER_CSV)
        ws_transaksi = sh.worksheet(TRANSAKSI_CSV)
        
        master_df = pd.DataFrame(ws_master.get_all_records())
        transaksi_df = pd.DataFrame(ws_transaksi.get_all_records())
        
        # Pastikan kolom numerik terbaca sebagai angka (bukan string)
        if not master_df.empty:
            master_df['stok_sekarang'] = pd.to_numeric(master_df['stok_sekarang'], errors='coerce').fillna(0)
            master_df['stok_minimum'] = pd.to_numeric(master_df['stok_minimum'], errors='coerce').fillna(0)
            
        if not transaksi_df.empty and 'jumlah' in transaksi_df.columns:
            transaksi_df['jumlah'] = pd.to_numeric(transaksi_df['jumlah'], errors='coerce').fillna(0)
        
        return master_df, transaksi_df
    except Exception as e:
        logger.error(f"Failed to load data from Google Sheets: {e}", exc_info=True)
        st.error(f"Gagal memuat data dari Google Sheets: {e}")
        st.info("Pastikan kredensial dan URL Spreadsheet di .streamlit/secrets.toml sudah benar!")
        st.stop()
        return pd.DataFrame(), pd.DataFrame()

def save_data(df: pd.DataFrame, sheet_name: str) -> None:
    """
    Save dataframe to Google Sheets and clear cache.
    
    Args:
        df (pd.DataFrame): The dataframe to save.
        sheet_name (str): The name of the worksheet tab.
    """
    try:
        gc = gspread.service_account_from_dict(st.secrets["gcp_service_account"])
        sh = gc.open_by_url(st.secrets["google_sheets"]["url"])
        ws = sh.worksheet(sheet_name)
        
        ws.clear() # Clear existing data
        set_with_dataframe(ws, df) # Write new data
        
        st.cache_data.clear()
        logger.info(f"Successfully saved data to sheet: {sheet_name}")
    except Exception as e:
        logger.error(f"Failed to save data to Google Sheets ({sheet_name}): {e}", exc_info=True)
        st.error(f"Gagal menyimpan ke Google Sheets: {e}")
