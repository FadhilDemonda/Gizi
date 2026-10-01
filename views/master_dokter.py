import streamlit as st
import pandas as pd
import time
from data.sheets_repository import get_sheet_data, save_data, SHEET_MASTER_DOKTER

def show_master_dokter():
    st.header("👨‍⚕️ Master Dokter")
    
    st.subheader("Kelola Data Dokter & Spesialis")
    st.caption("Penting: Jika Spesialis diisi 'UMUM', otomatis akan masuk kategori **Dokter Jaga**. Selain UMUM akan masuk **Dokter Praktek**.")
    
    master_dokter_df = get_sheet_data(SHEET_MASTER_DOKTER)
    
    if master_dokter_df.empty:
        master_dokter_df = pd.DataFrame(columns=["spesialis", "dokter"])
    
    edited_doc_df = st.data_editor(
        master_dokter_df, 
        use_container_width=True,
        hide_index=True,
        num_rows="dynamic",
        key="master_dokter_editor",
        column_config={
            "spesialis": st.column_config.TextColumn("Spesialis (Ketik 'UMUM' untuk Jaga)", required=True),
            "dokter": st.column_config.TextColumn("Nama Dokter", required=True)
        }
    )
    
    if not master_dokter_df.equals(edited_doc_df):
        if st.button("💾 Simpan Data Dokter", type="primary", key="save_master_dokter"):
            with st.spinner("Menyimpan daftar dokter..."):
                # Clean up empty rows
                edited_doc_df = edited_doc_df[edited_doc_df['dokter'].astype(str).str.strip() != ""]
                save_data(edited_doc_df, SHEET_MASTER_DOKTER)
            st.success("✅ Master Dokter berhasil diperbarui!")
            time.sleep(1)
            st.rerun()
