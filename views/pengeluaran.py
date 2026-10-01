"""
Re-export semua fungsi show_* agar app.py tidak perlu diubah.
Kode logika sudah dipecah ke:
  - pengeluaran_common.py  (show_toast, multi_select_dialog, render_form)
  - pengeluaran_dokter.py  (DOKTER_LIST, render_batch_dokter, show_pengeluaran_dokter)
  - pengeluaran_pasien.py  (render_batch_dapur, show_pengeluaran_pasien)
"""

import streamlit as st
from data.sheets_repository import SHEET_PENGELUARAN_MANAJEMEN
from views.pengeluaran_common import render_form
from views.pengeluaran_pasien import show_pengeluaran_pasien
from views.pengeluaran_dokter import show_pengeluaran_dokter

def show_pengeluaran_manajemen():
    st.title("🏢 Pengeluaran Manajemen")
    render_form("Manajemen", SHEET_PENGELUARAN_MANAJEMEN, ["PT", "Rapat Direksi", "Tamu VIP", "Staff", "Event RS", "Skrining", "Scuba", "Lainnya"])
