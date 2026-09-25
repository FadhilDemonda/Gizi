import streamlit as st
import os
import logging
from styles.theme import inject_custom_css
from utils.state import init_session_state
from views.dashboard import show_dashboard
from views.master_barang import show_master_barang
from views.transaksi import show_transaksi
from views.laporan_harian import show_laporan_harian
from views.analisis_stok import show_analisis_stok
from views.sinkronisasi import show_sinkronisasi

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s - %(message)s")

# Global Configuration
st.set_page_config(page_title="Stok-Gizi App", page_icon="📦", layout="wide")
inject_custom_css()
init_session_state()

def main():
    st.sidebar.title("📦 Stok-Gizi")
    st.sidebar.markdown("Aplikasi Manajemen Stok Makanan")
    
    menu = st.sidebar.radio(
        "Menu Navigasi", 
        ["📊 Dashboard", "📥 Input Transaksi Stok","📅 Laporan Harian", "📈 Analisis Stok", "📦 Master Barang", ]
    )
    
    st.sidebar.markdown("---")
    st.sidebar.caption("Versi 2.1 - Modular Cloud Database")
    
    # Routing
    if menu == "📊 Dashboard":
        show_dashboard()
    elif menu == "📥 Input Transaksi Stok":
        show_transaksi()
    elif menu == "📅 Laporan Harian":
        show_laporan_harian()
    elif menu == "📈 Analisis Stok":
        show_analisis_stok()
    elif menu == "📦 Master Barang":
        show_master_barang()
    # elif menu == "🔄 Sinkronisasi":
    #     show_sinkronisasi()

if __name__ == "__main__":
    os.makedirs("data", exist_ok=True)
    main()
