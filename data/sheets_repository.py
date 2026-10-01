import pandas as pd
import gspread
from gspread_dataframe import set_with_dataframe
import streamlit as st
import logging

# Configure logger
logger = logging.getLogger(__name__)

# Constants for sheet names
SHEET_MASTER = "master_barang"
SHEET_STOK_MASUK = "stok_masuk"
SHEET_PENGELUARAN_PASIEN = "pengeluaran_pasien"
SHEET_PENGELUARAN_DOKTER = "pengeluaran_dokter"
SHEET_PENGELUARAN_MANAJEMEN = "pengeluaran_manajemen"
SHEET_MASTER_DOKTER = "master_dokter"

SHEET_LOG = "log"

# Backward compatibility aliases
MASTER_CSV = SHEET_MASTER
TRANSAKSI_CSV = SHEET_LOG

@st.cache_resource
def get_gspread_client():
    """Get authenticated gspread client (cached for session)"""
    return gspread.service_account_from_dict(st.secrets["gcp_service_account"])

@st.cache_data(ttl=60, show_spinner=False)
def get_sheet_data(sheet_name: str) -> pd.DataFrame:
    """
    Load data from a specific Google Sheet tab, cached for performance.
    """
    try:
        gc = get_gspread_client()
        sh = gc.open_by_url(st.secrets["google_sheets"]["url"])
        ws = sh.worksheet(sheet_name)
        df = pd.DataFrame(ws.get_all_records(numericise_ignore=["all"]))
        
        # Ensure common numeric columns are properly typed
        if not df.empty:
            numeric_cols = ['stok_sekarang', 'stok_minimal', 'stok_minimum', 'harga_master', 'qty', 'harga_real', 'total_harga']
            for col in numeric_cols:
                if col in df.columns:
                    if df[col].dtype == object:
                        df[col] = df[col].apply(lambda x: str(x).replace(',', '.') if isinstance(x, str) else x)
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
                    
        return df
    except Exception as e:
        logger.error(f"Failed to load data from sheet {sheet_name}: {e}", exc_info=True)
        st.error(f"⚠️ Gagal memuat data dari tab '{sheet_name}'. Ini biasanya karena koneksi terputus atau batas limit Google Sheets. Silakan klik tombol **🔄 Refresh Data** di menu sebelah kiri.")
        return pd.DataFrame()

def save_data(df: pd.DataFrame, sheet_name: str) -> None:
    """
    Save dataframe to Google Sheets and clear cache.
    """
    try:
        gc = get_gspread_client()
        sh = gc.open_by_url(st.secrets["google_sheets"]["url"])
        ws = sh.worksheet(sheet_name)
        
        # Clear existing content
        ws.clear()
        
        # Write new dataframe
        set_with_dataframe(ws, df)
        
        # Invalidate cache for this specific sheet
        get_sheet_data.clear()
        logger.info(f"Successfully saved data to {sheet_name} and cleared cache")
    except Exception as e:
        logger.error(f"Failed to save data to {sheet_name}: {e}", exc_info=True)
        st.error(f"Gagal menyimpan data ke Google Sheets ({sheet_name}): {e}")

@st.cache_data(ttl=60, show_spinner=False)
def load_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Backward compatibility function during migration to new schema"""
    master_df = get_sheet_data(SHEET_MASTER)
    transaksi_df = get_sheet_data(SHEET_LOG)
    return master_df, transaksi_df
