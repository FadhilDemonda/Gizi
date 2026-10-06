import streamlit as st
import datetime
from data.sheets_repository import SHEET_PENGELUARAN_KARYAWAN
from views.pengeluaran_common import render_form

def show_pengeluaran_karyawan():
    col_title, col_date = st.columns([2.8, 1.4])
    with col_title:
        st.title("🧑‍💼 Pengeluaran Karyawan")
    with col_date:
        st.markdown('<span class="timestamp-blue-marker"></span>', unsafe_allow_html=True)
        tgl_transaksi = st.date_input("📅 Tanggal Transaksi", value=datetime.date.today(), key="tgl_trx_karyawan")
        
    karyawan_categories = [
        "Perina", "VK", "OK", "ICU", "RPK", "RPA", "VIP", "RPU", 
        "Supervisor", "DR. RUANGAN", "DR. UMUM", "RPB", "Radiologi", 
        "UGD", "PENDAFTARAN", "AMBULANCE", "Kasir Rajal", "Farmasi", 
        "LAB", "ESWL/ciarm", "maintenance"
    ]
    render_form("Karyawan", SHEET_PENGELUARAN_KARYAWAN, karyawan_categories, tgl_transaksi=tgl_transaksi)
