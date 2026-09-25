import streamlit as st
import pandas as pd
from datetime import datetime
from data.sheets_repository import load_data, save_data, MASTER_CSV, TRANSAKSI_CSV
from utils.validators import validate_editor_changes, validate_new_item
from services.transaction_service import build_transaction_record

def show_master_barang():
    st.header("📦 Master Barang")
    
    master_df, _ = load_data()
    
    col_head, col_exp = st.columns([3, 1])
    with col_head:
        st.subheader("Daftar Barang (CRUD)")
    with col_exp:
        csv_data = master_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Export ke CSV",
            data=csv_data,
            file_name=f"master_barang_{datetime.today().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            use_container_width=True
        )
        
    st.info("💡 **Tips CRUD:** Anda bisa mengubah isi langsung di dalam sel tabel. Untuk menghapus baris, klik kolom paling kiri dari baris tersebut dan tekan tombol `Delete` di *keyboard* Anda. Anda juga bisa menambah baris di bagian paling bawah tabel.")
    
    edited_df = st.data_editor(
        master_df, 
        use_container_width=True,
        hide_index=True,
        num_rows="dynamic",
        key="master_editor"
    )
    
    if not master_df.equals(edited_df):
        if st.button("💾 Simpan Perubahan ke Database", type="primary"):
            is_valid, error_msg = validate_editor_changes(edited_df)
            if not is_valid:
                st.error(error_msg)
            else:
                with st.spinner("Menyimpan dan mensinkronisasi data ke Cloud..."):
                    _, transaksi_df = load_data()
                    new_trx_list = []
                    
                    for _, row in edited_df.iterrows():
                        kode = row['kode_barang']
                        if kode in master_df['kode_barang'].values:
                            old_row = master_df[master_df['kode_barang'] == kode].iloc[0]
                            if row['stok_sekarang'] != old_row['stok_sekarang']:
                                diff = abs(row['stok_sekarang'] - old_row['stok_sekarang'])
                                new_record = build_transaction_record(
                                    len(transaksi_df) + len(new_trx_list),
                                    'Edit', kode, diff, 'Admin', 'Admin',
                                    f"CRUD Update: Stok manual diubah dari {old_row['stok_sekarang']} menjadi {row['stok_sekarang']}"
                                )
                                new_trx_list.append(new_record)
                        else:
                            new_record = build_transaction_record(
                                len(transaksi_df) + len(new_trx_list),
                                'Edit', kode, row['stok_sekarang'], 'Admin', 'Admin',
                                "CRUD Insert: Barang baru ditambahkan"
                            )
                            new_trx_list.append(new_record)
                            
                    for _, old_row in master_df.iterrows():
                        if old_row['kode_barang'] not in edited_df['kode_barang'].values:
                            new_record = build_transaction_record(
                                len(transaksi_df) + len(new_trx_list),
                                'Edit', old_row['kode_barang'], old_row['stok_sekarang'], 'Admin', 'Admin',
                                "CRUD Delete: Barang dihapus dari sistem"
                            )
                            new_trx_list.append(new_record)
                            
                    if new_trx_list:
                        new_trx_df = pd.DataFrame(new_trx_list)
                        transaksi_df = pd.concat([transaksi_df, new_trx_df], ignore_index=True)
                        save_data(transaksi_df, TRANSAKSI_CSV)
                        
                    save_data(edited_df, MASTER_CSV)
                
                st.success("✅ Perubahan berhasil disimpan dan log transaksi tercatat!")
                st.rerun()
    
    st.markdown("---")
    
    st.subheader("➕ Tambah Barang Baru")
    
    unique_satuan = master_df['satuan'].dropna().unique().tolist()
    if not unique_satuan:
        unique_satuan = ["Kg", "Liter", "Pack", "Sak"]
        
    with st.form("form_tambah_barang", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            kode_brg = st.text_input("Kode Barang *", placeholder="Misal: B004")
            nama_brg = st.text_input("Nama Barang *")
            sat_brg = st.radio("Satuan Pengukuran (UoM) *", unique_satuan, horizontal=True)
            
        with col2:
            stok_min = st.number_input("Ambang Batas Minimum (Safety Stock) *", min_value=0, value=10, step=1)
            st.caption("Sistem otomatis menerbitkan sinyal waspada bila stok di bawah batas ini.")
            st.markdown("<br>", unsafe_allow_html=True)
            stok_skrg = st.number_input("Saldo Awal Fisik (Stok Sekarang)", min_value=0, value=0, step=1)
        
        submitted = st.form_submit_button("Simpan Barang", type="primary")
        if submitted:
            is_valid, error_msg = validate_new_item(kode_brg, nama_brg, master_df)
            if not is_valid:
                st.error(error_msg)
            else:
                with st.spinner("Menyimpan data..."):
                    new_row = pd.DataFrame([{
                        'kode_barang': kode_brg, 'nama_barang': nama_brg, 
                        'satuan': sat_brg, 'stok_minimum': stok_min, 'stok_sekarang': stok_skrg
                    }])
                    master_df = pd.concat([master_df, new_row], ignore_index=True)
                    save_data(master_df, MASTER_CSV)
                st.success(f"Barang {nama_brg} berhasil ditambahkan!")
                st.rerun()
