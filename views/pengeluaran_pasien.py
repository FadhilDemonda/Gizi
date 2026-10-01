import streamlit as st
import datetime
import pandas as pd
from data.sheets_repository import (
    get_sheet_data, save_data, SHEET_MASTER, SHEET_PENGELUARAN_PASIEN
)
from views.pengeluaran_common import show_toast, multi_select_dialog
from views.dialog_tambah_barang import dialog_tambah_barang

def show_pengeluaran_pasien():
    st.title("🛏️ Pengeluaran Pasien")
    # st.info("💡 **Petunjuk:** Anda bisa memilih lebih dari satu kelas sekaligus. Jika memilih banyak kelas, pengeluaran bahan akan dibagi secara otomatis & proporsional berdasarkan jumlah pasien per kelas.")
    
    sheet_name = SHEET_PENGELUARAN_PASIEN
    toast_key = 'toast_msg_Pasien'
    if toast_key in st.session_state:
        show_toast(st.session_state.pop(toast_key))
        
    master_df = get_sheet_data(SHEET_MASTER)
    if master_df.empty:
        st.warning("Data Master Barang kosong!")
        return

    now = datetime.datetime.now()
    item_options = master_df['nama_barang'].tolist()
    
    # Session state keys untuk dynamic rows
    tab_name = "Pasien"
    state_items_key = f"dyn_items_{tab_name}"
    state_defaults_key = f"dyn_defaults_{tab_name}"
    reset_counter_key = f"reset_ctr_{tab_name}"
    
    if reset_counter_key not in st.session_state:
        st.session_state[reset_counter_key] = 0
    rc = st.session_state[reset_counter_key]
    
    if state_items_key not in st.session_state:
        st.session_state[state_items_key] = [0]
        st.session_state[state_defaults_key] = []
    
    def add_row():
        if len(st.session_state[state_items_key]) > 0:
            new_id = max(st.session_state[state_items_key]) + 1
        else:
            new_id = 0
        st.session_state[state_items_key].append(new_id)
        
    def remove_row(row_id):
        st.session_state[state_items_key].remove(row_id)
        
    def clear_all():
        st.session_state[state_items_key] = [0]
        st.session_state[state_defaults_key] = []
        for k in list(st.session_state.keys()):
            if k.startswith((f"qty_{tab_name}", f"item_{tab_name}", f"sat_{tab_name}", f"ket_{tab_name}")):
                del st.session_state[k]
    
    with st.container(border=True):
        # HEADER KATEGORI & SHIFT
        c1, c2 = st.columns([1, 2])
        with c1:
            shift = st.selectbox("Keterangan Waktu \*", ["Pagi (07:00-15:00)", "Siang (15:00-22:00)", "Malam (22:00-07:00)", "1 Hari"], key=f"shift_{tab_name}")
        with c2:
            kategori_options = ["VIP", "Kelas 1", "Kelas 2", "Kelas 3"]
            kategori_selected = st.multiselect("Pilih Kategori Kelas \*", kategori_options, default=["VIP", "Kelas 1", "Kelas 2", "Kelas 3"], key=f"kat_{tab_name}")
            
        st.divider()
        st.markdown("##### 1. Jumlah Pasien")
        st.caption("Masukkan jumlah pasien untuk masing-masing kelas yang Anda pilih di atas.")
        
        distribusi = []
        total_pasien = 0
        
        if not kategori_selected:
            st.error("Silakan pilih minimal 1 kategori kelas di atas!")
        else:
            cols = st.columns(len(kategori_selected))
            for i, kat in enumerate(kategori_selected):
                jml = cols[i].number_input(f"Jml Pasien {kat}", min_value=1, step=1, value=1, key=f"jml_pasien_{kat}_{rc}")
                distribusi.append((kat, jml))
                total_pasien += jml
                
            st.info(f"**Total Keseluruhan Pasien:** {total_pasien} orang")
            
        st.divider()
        st.markdown("##### 2. Input Barang / Bahan Mentah")
        
        # Header
        h1, h2, h_sat, h5, h6 = st.columns([3, 1.5, 1.5, 2, 0.5])
        h1.caption("Pilih Barang")
        h2.caption("Qty Total")
        h_sat.caption("Satuan")
        h5.caption("Keterangan Tambahan")
        h6.caption("")
        
        row_data = []
        
        for i, row_id in enumerate(st.session_state[state_items_key]):
            default_idx = 0
            if state_defaults_key in st.session_state and i < len(st.session_state[state_defaults_key]):
                def_val = st.session_state[state_defaults_key][i]
                if def_val in item_options:
                    default_idx = item_options.index(def_val)
            
            c1, c2, c_sat, c5, c6 = st.columns([3, 1.5, 1.5, 2, 0.5])
            with c1:
                selected_item = st.selectbox("Barang", item_options, index=default_idx, key=f"item_{tab_name}_{rc}_{row_id}", label_visibility="collapsed")
            
            item_data = master_df[master_df['nama_barang'] == selected_item].iloc[0]
            stok_fisik = float(item_data.get('stok_sekarang', 0))
            harga_master = float(item_data.get('harga_master', 0))
            satuan = item_data.get('satuan', '')
            is_unlimited = float(item_data.get('stok_minimal', 0)) == 0
            max_qty = 99999.0 if is_unlimited else max(1.0, float(stok_fisik))
            
            with c2:
                qty = st.number_input("Qty", min_value=0.0, max_value=max_qty, value=1.0, step=1.0, format="%.2f", key=f"qty_{tab_name}_{rc}_{row_id}", label_visibility="collapsed")
            
            with c_sat:
                st.text_input("Satuan", value=satuan, disabled=True, key=f"sat_{tab_name}_{rc}_{row_id}_{selected_item}", label_visibility="collapsed")
                
            with c5:
                ket = st.text_input("Keterangan", placeholder="(Opsional)", key=f"ket_{tab_name}_{rc}_{row_id}", label_visibility="collapsed")
            
            with c6:
                st.button("🗑️", key=f"del_{tab_name}_{rc}_{row_id}", on_click=remove_row, args=(row_id,))
            
            # Validations
            error_stok = (stok_fisik < qty) and not is_unlimited
            if error_stok:
                st.error(f"Stok {selected_item} tidak cukup! (Tersisa: {stok_fisik})")
                
            if qty > 0:
                row_data.append({
                    "nama_barang": selected_item,
                    "qty": qty,
                    "harga_master": harga_master,
                    "keterangan": ket.strip(),
                    "stok_fisik": stok_fisik,
                    "is_error": error_stok
                })
        
        # Tombol tambah barang
        btn_col1, btn_col2, btn_col3, btn_col4 = st.columns([1.3, 1.4, 1.4, 1.1])
        with btn_col1:
            st.button("➕ Tambah 1 Baris Kosong", on_click=add_row, key=f"add_{tab_name}", use_container_width=True)
        with btn_col2:
            if st.button("🔍 Pilih Banyak Barang Sekaligus", key=f"multi_add_{tab_name}", use_container_width=True):
                current_items_in_form = []
                for idx, r_id in enumerate(st.session_state[state_items_key]):
                    item_val = st.session_state.get(f"item_{tab_name}_{rc}_{r_id}")
                    if not item_val and idx < len(st.session_state.get(state_defaults_key, [])):
                        item_val = st.session_state[state_defaults_key][idx]
                    if item_val:
                        current_items_in_form.append(item_val)
                multi_select_dialog(master_df, state_items_key, state_defaults_key, current_items_in_form)
        with btn_col3:
            if st.button("📦 Tambah Barang Baru", key=f"new_item_{tab_name}", use_container_width=True):
                dialog_tambah_barang(state_items_key, state_defaults_key, toast_key=toast_key)
        with btn_col4:
            st.markdown('<span class="btn-clear-target"></span>', unsafe_allow_html=True)
            st.button("🗑️ Bersihkan Semua", on_click=clear_all, key=f"clear_all_{tab_name}", use_container_width=True)
        
        st.divider()
        
        has_error = any(r['is_error'] for r in row_data)
                
        if total_pasien == 0 and row_data:
            st.error("⚠️ Total Pasien tidak boleh 0! Harap isi jumlah pasien di atas.")
        elif row_data and total_pasien > 0:
            total_nilai = sum(r['qty'] * r['harga_master'] for r in row_data)
            if len(distribusi) > 1:
                st.success(f"Terdapat **{len(row_data)} macam barang** (Total: Rp {total_nilai:,.0f}) yang akan dipecah secara proporsional ke **{total_pasien} porsi** ({len(distribusi)} kelas).")
            else:
                st.success(f"Terdapat **{len(row_data)} macam barang** (Total: Rp {total_nilai:,.0f}) yang akan dimasukkan ke **{distribusi[0][0]}**.")
                
            if has_error:
                st.error("⚠️ Peringatan: Ada barang yang stok fisiknya tidak cukup.")
                
        submit = st.button("✓ Proses & Simpan", type="primary", use_container_width=True, disabled=(not row_data or total_pasien == 0 or not kategori_selected))
        
        if submit:
            if has_error:
                st.error("Silakan perbaiki stok barang yang merah terlebih dahulu!")
                return
                
            with st.spinner("Memproses transaksi..."):
                try:
                    trx_df = get_sheet_data(sheet_name)
                    new_rows = []
                    master_df_updated = master_df.copy()
                    
                    timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
                    
                    for r in row_data:
                        # Potong stok master
                        idx = master_df_updated.index[master_df_updated['nama_barang'] == r['nama_barang']].tolist()[0]
                        master_df_updated.at[idx, 'stok_sekarang'] = master_df_updated.at[idx, 'stok_sekarang'] - r['qty']
                        
                        # Pecah proporsional
                        for kat, jml in distribusi:
                            if jml > 0:
                                porsi = jml / total_pasien
                                qty_proporsional = r['qty'] * porsi
                                
                                # Jika user gak nulis keterangan, set default aja biar rapi
                                ket_final = r['keterangan']
                                if not ket_final:
                                    ket_final = "Distribusi Proporsional" if len(distribusi) > 1 else "Input Satuan"
                                    
                                new_rows.append({
                                    "tanggal": timestamp,
                                    "shift": shift,
                                    "kategori": kat,
                                    "kategori_freetext": "",
                                    "nama_barang": r['nama_barang'],
                                    "qty": qty_proporsional,
                                    "harga_master": r['harga_master'],
                                    "harga_real": r['harga_master'],
                                    "total_harga": qty_proporsional * r['harga_master'],
                                    "keterangan": ket_final,
                                    "jumlah_pasien": jml
                                })
                                
                    save_data(master_df_updated, SHEET_MASTER)
                    trx_df = pd.concat([trx_df, pd.DataFrame(new_rows)], ignore_index=True)
                    save_data(trx_df, sheet_name)
                    
                    # Reset input
                    if state_items_key in st.session_state:
                        del st.session_state[state_items_key]
                    if state_defaults_key in st.session_state:
                        del st.session_state[state_defaults_key]
                    st.session_state[reset_counter_key] += 1
                    
                    if len(distribusi) > 1:
                        st.session_state[toast_key] = f"Berhasil menyimpan & memecah {len(row_data)} barang ke {total_pasien} porsi pasien!"
                    else:
                        st.session_state[toast_key] = f"Berhasil menyimpan {len(row_data)} barang ke {distribusi[0][0]}!"
                    st.rerun()
                except Exception as e:
                    st.error(f"Gagal menyimpan: {e}")
