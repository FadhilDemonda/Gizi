import streamlit as st
import os
import logging
from styles.theme import inject_custom_css
from utils.state import init_session_state
from views.dashboard import show_dashboard
from views.master_barang import show_master_barang
from views.master_dokter import show_master_dokter
from views.transaksi import show_transaksi
from views.pengeluaran import show_pengeluaran_pasien, show_pengeluaran_dokter, show_pengeluaran_manajemen
from views.laporan_harian import show_laporan_harian
from views.analisis_stok import show_analisis_stok

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s - %(message)s")

# Logo Configuration
LOGO_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "styles", "Rumah_Sakit_Annisa_Tangerang-removebg-preview.png")

# Global Configuration
if os.path.exists(LOGO_PATH):
    st.set_page_config(page_title="Stok Gizi RS An-Nisa", page_icon=LOGO_PATH, layout="wide")
else:
    st.set_page_config(page_title="Stok-Gizi App", page_icon="📦", layout="wide")

inject_custom_css()
init_session_state()

def main():
    if os.path.exists(LOGO_PATH):
        c_l1, c_l2, c_l3 = st.sidebar.columns([1, 2, 1])
        with c_l2:
            st.image(LOGO_PATH, use_container_width=True)
        st.sidebar.markdown(
            "<div style='text-align: center; margin-top: -6px; margin-bottom: 14px;'>"
            "<h2 style='margin: 0; font-size: 1.35rem; font-weight: 700;'>Stok Gizi</h2>"
            "<span style='font-size: 0.82rem; opacity: 0.8;'>RS An-Nisa Tangerang</span>"
            "</div>",
            unsafe_allow_html=True
        )
    else:
        st.sidebar.title("📦 Stok-Gizi")
        st.sidebar.markdown("Aplikasi Manajemen Stok Makanan")
    
    # 2-Level Menu System
    kategori_menu = st.sidebar.selectbox(
        "📂 KATEGORI MENU", 
        ["📊 Analitik & Laporan", "📦 Input & Transaksi", "⚙️ Pengaturan Data"]
    )
    
    st.sidebar.markdown("---")
    
    # Sub-menu mapping
    if kategori_menu == "📊 Analitik & Laporan":
        menu = st.sidebar.radio("Halaman:", ["Dashboard Utama", "Analisis Stok", "Laporan Harian"])
    elif kategori_menu == "📦 Input & Transaksi":
        menu = st.sidebar.radio("Halaman:", ["Input Stok Masuk", "Pengeluaran Pasien", "Pengeluaran Dokter", "Pengeluaran Manajemen"])
    elif kategori_menu == "⚙️ Pengaturan Data":
        menu = st.sidebar.radio("Halaman:", ["Master Barang", "Master Dokter"])
    
    st.sidebar.markdown("---")
    
    if st.sidebar.button("🔄 Refresh Data", use_container_width=True):
        if hasattr(st, 'cache_data'):
            st.cache_data.clear()
        if hasattr(st, 'rerun'):
            st.rerun()
        else:
            st.experimental_rerun()
            
    st.sidebar.caption("Versi 2.1 - Modular Cloud Database")
    
    # Routing
    if menu == "Dashboard Utama":
        show_dashboard()
    elif menu == "Analisis Stok":
        show_analisis_stok()
    elif menu == "Input Stok Masuk":
        show_transaksi()
    elif menu == "Pengeluaran Pasien":
        show_pengeluaran_pasien()
    elif menu == "Pengeluaran Dokter":
        show_pengeluaran_dokter()
    elif menu == "Pengeluaran Manajemen":
        show_pengeluaran_manajemen()
    elif menu == "Laporan Harian":
        show_laporan_harian()
    elif menu == "Master Barang":
        show_master_barang()
    elif menu == "Master Dokter":
        show_master_dokter()

if __name__ == "__main__":
    os.makedirs("data", exist_ok=True)
    main()
