import streamlit as st
import os
import logging
from styles.theme import inject_custom_css
from utils.state import init_session_state
from views.dashboard import show_dashboard
from views.master_barang import show_master_barang
from views.master_dokter import show_master_dokter
from views.transaksi import show_transaksi, show_riwayat_harga
from views.pengeluaran import (
    show_pengeluaran_pasien, 
    show_pengeluaran_dokter, 
    show_pengeluaran_manajemen,
    show_pengeluaran_karyawan,
    show_riwayat_pengeluaran
)
from views.laporan_harian import show_laporan_harian
from views.analisis_stok import show_analisis_stok

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s - %(message)s")

# Logo Configuration
LOGO_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "styles", "Rumah_Sakit_Annisa_Tangerang-removebg-preview.png")

logger = logging.getLogger(__name__)

# Global Configuration
if os.path.exists(LOGO_PATH):
    st.set_page_config(page_title="Stok Gizi RS An-Nisa", page_icon=LOGO_PATH, layout="wide")
else:
    st.set_page_config(page_title="Stok-Gizi App", page_icon="📦", layout="wide")

inject_custom_css()
init_session_state()

def render_page_safely(view_fn, page_name: str):
    """
    Global Error Boundary untuk membungkus setiap halaman aplikasi
    agar tidak crash atau memunculkan traceback merah ke pengguna biasa.
    """
    try:
        view_fn()
    except Exception as e:
        logger.error(f"Error rendering {page_name}: {e}", exc_info=True)
        st.markdown(
            f"""
            <div style="background-color: #fef2f2; border: 1px solid #fca5a5; border-left: 6px solid #ef4444; border-radius: 12px; padding: 22px; margin-top: 15px; box-shadow: 0 4px 12px rgba(239, 68, 68, 0.08);">
                <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 8px;">
                    <span style="font-size: 26px;">⚠️</span>
                    <h3 style="color: #991b1b; margin: 0; font-size: 1.25rem; font-weight: 700;">
                        Terjadi Kendala pada Halaman {page_name}
                    </h3>
                </div>
                <p style="color: #4b5563; font-size: 14.5px; line-height: 1.5; margin: 8px 0 14px 0;">
                    Aplikasi mendeteksi gangguan saat memuat atau memproses data dari server. Jangan khawatir, data Anda tetap aman di cloud.
                </p>
                <div style="background: #ffffff; padding: 14px 18px; border-radius: 8px; border: 1px dashed #f87171;">
                    <span style="font-weight: 600; color: #1f2937; font-size: 14px;">Langkah Penanganan Cepat:</span>
                    <ul style="margin: 6px 0 0 0; padding-left: 20px; color: #4b5563; font-size: 13.5px; line-height: 1.6;">
                        <li>Klik tombol <b>🔄 Refresh Data</b> pada menu di sidebar sebelah kiri.</li>
                        <li>Pastikan koneksi internet stabil (bisa muat ulang halaman dengan menekan <code>F5</code>).</li>
                        <li>Jika kendala terus berlanjut, silakan segera <b>hubungi Tim DTO</b>.</li>
                    </ul>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
        with st.expander("🛠️ Detail Diagnostik (Khusus Tim DTO / IT)", expanded=False):
            st.error(f"**Tipe Kesalahan:** {type(e).__name__}")
            st.code(str(e), language="text")
            import traceback
            st.code(traceback.format_exc(), language="text")

def main():
    if os.path.exists(LOGO_PATH):
        col_logo, col_txt = st.sidebar.columns([1, 3.2])
        with col_logo:
            st.image(LOGO_PATH, use_container_width=True)
        with col_txt:
            st.markdown(
                "<div style='margin-left: -4px;'>"
                "<h2 style='margin: 0; font-size: 1.35rem; font-weight: 700; line-height: 1.15;'>Stok Gizi</h2>"
                "<span style='font-size: 0.8rem; opacity: 0.75;'>RS An-Nisa Tangerang</span>"
                "</div>",
                unsafe_allow_html=True
            )
        st.sidebar.markdown("<div style='margin-bottom: 10px;'></div>", unsafe_allow_html=True)
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
        menu = st.sidebar.radio("Halaman:", [
            "Input Stok Masuk", 
            "Pengeluaran Pasien", 
            "Pengeluaran Dokter", 
            "Pengeluaran Manajemen",
            "Pengeluaran Karyawan"
        ])
    elif kategori_menu == "⚙️ Pengaturan Data":
        menu = st.sidebar.radio("Halaman:", [
            "Master Barang", 
            "Master Dokter",
            "Riwayat Pengeluaran & Harga"
        ])
    
    st.sidebar.markdown("---")
    
    # Deteksi perpindahan halaman: Refresh data hanya saat pindah halaman (bukan per menit)
    active_page = f"{kategori_menu} > {menu}"
    if "last_active_page" not in st.session_state:
        st.session_state["last_active_page"] = active_page
    elif st.session_state["last_active_page"] != active_page:
        st.session_state["last_active_page"] = active_page
        if hasattr(st, 'cache_data'):
            st.cache_data.clear()
        logger.info(f"Pindah halaman ke '{active_page}': Cache data dibersihkan untuk memuat data terbaru.")
    
    if st.sidebar.button("🔄 Refresh Data", use_container_width=True):
        if hasattr(st, 'cache_data'):
            st.cache_data.clear()
        if hasattr(st, 'rerun'):
            st.rerun()
        else:
            st.experimental_rerun()
            
    st.sidebar.caption("Versi 2.2 - Protected by Tim DTO")
    
    # Routing terlindungi dengan Global Error Boundary
    if menu == "Dashboard Utama":
        render_page_safely(show_dashboard, "Dashboard Utama")
    elif menu == "Analisis Stok":
        render_page_safely(show_analisis_stok, "Analisis Stok")
    elif menu == "Input Stok Masuk":
        render_page_safely(show_transaksi, "Input Stok Masuk")
    elif menu in ["Riwayat Pengeluaran & Harga", "Input Riwayat Pengeluaran", "Input Riwayat Harga", "Riwayat Pengeluaran"]:
        render_page_safely(show_riwayat_pengeluaran, "Riwayat Pengeluaran & Harga")
    elif menu == "Pengeluaran Pasien":
        render_page_safely(show_pengeluaran_pasien, "Pengeluaran Pasien")
    elif menu == "Pengeluaran Dokter":
        render_page_safely(show_pengeluaran_dokter, "Pengeluaran Dokter")
    elif menu == "Pengeluaran Manajemen":
        render_page_safely(show_pengeluaran_manajemen, "Pengeluaran Manajemen")
    elif menu == "Pengeluaran Karyawan":
        render_page_safely(show_pengeluaran_karyawan, "Pengeluaran Karyawan")
    elif menu == "Laporan Harian":
        render_page_safely(show_laporan_harian, "Laporan Harian")
    elif menu == "Master Barang":
        render_page_safely(show_master_barang, "Master Barang")
    elif menu == "Master Dokter":
        render_page_safely(show_master_dokter, "Master Dokter")

if __name__ == "__main__":
    os.makedirs("data", exist_ok=True)
    main()
