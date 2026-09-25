import streamlit as st
import pandas as pd
from datetime import datetime
from data.sheets_repository import load_data, save_data, MASTER_CSV, TRANSAKSI_CSV
from utils.state import set_tipe_trx
from utils.validators import validate_transaction
from services.transaction_service import validate_stock_out, compute_stok_akhir, build_transaction_record
from styles.theme import inject_transaction_button_css

def show_transaksi():
    active_type = st.session_state.get('tipe_trx', '+ Stok Masuk')
    inject_transaction_button_css(active_type)
    
    col1, col2 = st.columns([2, 1])
    with col1:
        st.header("📦 Input Transaksi Stok")
        st.caption("Catat penambahan atau pengurangan kuantitas inventaris barang secara akurat.")
    with col2:
        st.info(f"🔒 Timestamp Sistem TERKUNCI\n\n**{datetime.today().strftime('%d %B %Y • %H:%M')} WIB**")
        
    master_df, transaksi_df = load_data()
    
    with st.container(border=True):
        col1, col2 = st.columns(2)
        with col1:
            shift = st.selectbox("🕔 SHIFT OPERASIONAL", ["Shift Pagi (07:00 - 15:00)", "Shift Siang (15:00 - 23:00)", "Shift Malam (23:00 - 07:00)"])
        with col2:
            petugas = st.text_input("👤 NAMA PETUGAS GUDANG")
            
        st.markdown("<hr/>", unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        with col1:
            brg_options = master_df['kode_barang'] + " - " + master_df['nama_barang']
            brg_selected = st.selectbox("Pilih Barang *", brg_options)
            
            kode_brg_selected = brg_selected.split(" - ")[0]
            item_data = master_df[master_df['kode_barang'] == kode_brg_selected].iloc[0]
            stok_awal = item_data['stok_sekarang']
            satuan = item_data['satuan']
            
            st.info(f"📊 **STOK TERSEDIA SAAT INI:** \n### {stok_awal} {satuan}")
            
            keterangan = st.text_area("Keterangan Tambahan (Opsional)", placeholder="Contoh: Pembelian dari supplier XYZ...")
            
        with col2:
            st.markdown("<span style='font-weight: 600; margin-bottom: 5px; display: inline-block;'>Tipe Transaksi <span style='color: red;'>*</span></span>", unsafe_allow_html=True)
            
            t_col1, t_col2 = st.columns(2)
            with t_col1:
                st.button("+ Stok Masuk", 
                          type="primary" if st.session_state.tipe_trx == "+ Stok Masuk" else "secondary", 
                          use_container_width=True, 
                          on_click=set_tipe_trx, args=("+ Stok Masuk",))
            with t_col2:
                st.button("- Stok Keluar", 
                          type="primary" if st.session_state.tipe_trx == "- Stok Keluar" else "secondary", 
                          use_container_width=True, 
                          on_click=set_tipe_trx, args=("- Stok Keluar",))
                          
            tipe_trx = st.session_state.tipe_trx
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            st.markdown(f"""
                <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                    <span style="font-weight: 600;">Jumlah Perubahan <span style="color: red;">*</span></span>
                    <span style="color: gray; font-size: 0.9em;">Satuan: {satuan}</span>
                </div>
            """, unsafe_allow_html=True)
            
            reset_key = f"jumlah_input_{st.session_state.form_reset_count}"
            jumlah = st.number_input("Jumlah", min_value=0, step=1, key=reset_key, label_visibility="collapsed")
            
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("##### Kalkulasi Stok Otomatis")
        
        calc_col1, calc_col2, calc_col3 = st.columns(3)
        
        stok_akhir = compute_stok_akhir(stok_awal, jumlah, 'Masuk' if tipe_trx == '+ Stok Masuk' else 'Keluar')
        perubahan_str = f"+{jumlah}" if tipe_trx == '+ Stok Masuk' else f"-{jumlah}"
        
        with calc_col1:
            st.metric("Stok Sebelumnya", f"{stok_awal} {satuan}")
        with calc_col2:
            st.metric(f"Perubahan ({'Masuk' if tipe_trx == '+ Stok Masuk' else 'Keluar'})", f"{perubahan_str} {satuan}")
        with calc_col3:
            st.metric("Total Stok Akhir", f"{stok_akhir} {satuan}")
            
    can_save = True
    if tipe_trx == "- Stok Keluar":
        is_valid, _ = validate_stock_out(stok_awal, jumlah)
        if not is_valid:
            st.error(f"❌ Stok tidak cukup! Tidak bisa mengeluarkan {jumlah} {satuan}.")
            can_save = False

    btn_col1, btn_col2 = st.columns([4, 1])
    with btn_col2:
        simpan = st.button("✓ Simpan Transaksi Stok", type="primary", use_container_width=True, disabled=not can_save)
        
    if simpan:
        is_valid, error_msg = validate_transaction(petugas, jumlah)
        if not is_valid:
            st.error(error_msg)
        else:
            with st.spinner("Mencatat transaksi..."):
                jenis_db = "Masuk" if tipe_trx == "+ Stok Masuk" else "Keluar"
                shift_val = shift.split(" ")[1]
                
                new_record = build_transaction_record(
                    len(transaksi_df), jenis_db, kode_brg_selected, jumlah, petugas, shift_val, keterangan
                )
                
                transaksi_df = pd.concat([transaksi_df, pd.DataFrame([new_record])], ignore_index=True)
                save_data(transaksi_df, TRANSAKSI_CSV)
                
                idx = master_df[master_df['kode_barang'] == kode_brg_selected].index
                master_df.loc[idx, 'stok_sekarang'] = stok_akhir
                save_data(master_df, MASTER_CSV)
                
            st.success(f"Berhasil {'menambah' if jenis_db == 'Masuk' else 'mengeluarkan'} {jumlah} {satuan} {item_data['nama_barang']}!")
            st.session_state.form_reset_count += 1
            st.rerun()

    st.markdown("---")
    with st.expander("📜 Lihat Riwayat Seluruh Transaksi"):
        st.dataframe(transaksi_df, use_container_width=True, hide_index=True)
