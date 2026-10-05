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

@st.cache_resource
def get_spreadsheet():
    """Get open spreadsheet instance (cached for session)"""
    gc = get_gspread_client()
    return gc.open_by_url(st.secrets["google_sheets"]["url"])

@st.cache_data(show_spinner="⏳ Memuat data dari server cloud...")
def get_sheet_data(sheet_name: str) -> pd.DataFrame:
    """
    Load data from a specific Google Sheet tab, cached for performance.
    Data is refreshed only upon page change or explicit submit/refresh.
    """
    try:
        sh = get_spreadsheet()
        ws = sh.worksheet(sheet_name)
        df = pd.DataFrame(ws.get_all_records(numericise_ignore=["all"]))
        
        # Ensure common numeric columns are properly typed
        if not df.empty:
            if sheet_name == SHEET_MASTER and 'harga_real' not in df.columns:
                df['harga_real'] = df['harga_master'].copy() if 'harga_master' in df.columns else 0.0
                
            if sheet_name == SHEET_STOK_MASUK:
                if 'sisa_qty' not in df.columns:
                    df['sisa_qty'] = df['qty'].copy() if 'qty' in df.columns else 0.0
                else:
                    df['sisa_qty'] = pd.to_numeric(df['sisa_qty'].apply(lambda x: str(x).replace(',', '.') if isinstance(x, str) else x), errors='coerce')
                    if 'qty' in df.columns:
                        df['sisa_qty'] = df['sisa_qty'].fillna(df['qty'])
                    else:
                        df['sisa_qty'] = df['sisa_qty'].fillna(0.0)
                
            numeric_cols = ['stok_sekarang', 'stok_minimal', 'stok_minimum', 'harga_master', 'qty', 'harga_real', 'total_harga', 'sisa_qty']
            for col in numeric_cols:
                if col in df.columns:
                    if df[col].dtype == object:
                        df[col] = df[col].apply(lambda x: str(x).replace(',', '.') if isinstance(x, str) else x)
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
                    
        return df
    except Exception as e:
        logger.error(f"Failed to load data from sheet {sheet_name}: {e}", exc_info=True)
        st.error(f"⚠️ Gagal memuat data dari tab '{sheet_name}'. Ini biasanya karena koneksi terputus atau batas limit Google Sheets. Silakan klik tombol **🔄 Refresh Data** di menu sebelah kiri atau hubungi **Tim DTO**.")
        return pd.DataFrame()

def save_data(df: pd.DataFrame, sheet_name: str) -> None:
    """
    Save dataframe to Google Sheets and immediately clear cache so fresh data is loaded.
    """
    try:
        sh = get_spreadsheet()
        ws = sh.worksheet(sheet_name)
        
        # Clear existing content
        ws.clear()
        
        # Write new dataframe
        set_with_dataframe(ws, df)
        
        # Invalidate cache completely so submitted data is instantly live
        get_sheet_data.clear()
        load_data.clear()
        if hasattr(st, 'cache_data'):
            st.cache_data.clear()
        logger.info(f"Successfully saved data to {sheet_name} and cleared cache")
    except Exception as e:
        logger.error(f"Failed to save data to {sheet_name}: {e}", exc_info=True)
        st.error(f"⚠️ Gagal menyimpan data ke tab '{sheet_name}'. Silakan coba beberapa saat lagi atau hubungi **Tim DTO**. (Detail: {e})")

@st.cache_data(show_spinner=False)
def load_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Backward compatibility function during migration to new schema"""
    master_df = get_sheet_data(SHEET_MASTER)
    transaksi_df = get_sheet_data(SHEET_LOG)
    return master_df, transaksi_df
