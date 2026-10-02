"""
Re-export semua fungsi show_* agar app.py tidak perlu diubah.
Kode logika sudah dipecah ke:
  - pengeluaran_common.py  (show_toast, multi_select_dialog, render_form)
  - pengeluaran_dokter.py  (DOKTER_LIST, render_batch_dokter, show_pengeluaran_dokter)
  - pengeluaran_pasien.py  (render_batch_dapur, show_pengeluaran_pasien)
"""

import streamlit as st
import datetime
from data.sheets_repository import SHEET_PENGELUARAN_MANAJEMEN
from views.pengeluaran_common import render_form
from views.pengeluaran_pasien import show_pengeluaran_pasien
from views.pengeluaran_dokter import show_pengeluaran_dokter
from views.riwayat_pengeluaran import show_riwayat_pengeluaran
show_riwayat_pengeluaran_pasien = show_riwayat_pengeluaran

def show_pengeluaran_manajemen():
    col_title, col_date = st.columns([2.8, 1.4])
    with col_title:
        st.title("🏢 Pengeluaran Manajemen")
    with col_date:
        st.markdown('<span class="timestamp-blue-marker"></span>', unsafe_allow_html=True)
        tgl_transaksi = st.date_input("📅 Tanggal Transaksi", value=datetime.date.today(), key="tgl_trx_manajemen")
    render_form("Manajemen", SHEET_PENGELUARAN_MANAJEMEN, ["PT", "Rapat Direksi", "Tamu VIP", "Staff", "Event RS", "Skrining", "Scuba", "Lainnya"], tgl_transaksi=tgl_transaksi)
