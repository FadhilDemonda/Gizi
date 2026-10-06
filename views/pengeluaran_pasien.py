import streamlit as st
import datetime
import pandas as pd
from data.sheets_repository import (
    get_sheet_data, save_data, SHEET_MASTER, SHEET_PENGELUARAN_PASIEN, SHEET_STOK_MASUK, SHEET_LOG
)
from views.pengeluaran_common import show_toast, multi_select_dialog, get_item_suppliers
from views.transaksi import extract_unique_suppliers

def show_pengeluaran_pasien():
    col_title, col_date = st.columns([2.8, 1.4])
    with col_title:
        st.title("🛏️ Pengeluaran Masak / Pasien")
    with col_date:
        st.markdown('<span class="timestamp-blue-marker"></span>', unsafe_allow_html=True)
        tgl_transaksi = st.date_input("📅 Tanggal Transaksi", value=datetime.date.today(), key="tgl_trx_pasien")
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
    item_options = [str(x).strip() for x in master_df['nama_barang'].dropna().unique() if str(x).strip()]
    raw_suppliers = extract_unique_suppliers(master_df)
    supplier_options = ["-"] + raw_suppliers + [s for s in ["Kasir", "Lainnya"] if s not in raw_suppliers]
    
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
            if k.startswith((f"qty_{tab_name}", f"item_{tab_name}", f"sat_{tab_name}", f"ket_{tab_name}", f"sup_{tab_name}")):
                del st.session_state[k]
    
    with st.container(border=True):
        # HEADER KATEGORI & SHIFT
        c1, c2 = st.columns([1, 2])
        with c1:
            shift = st.selectbox("Keterangan Waktu *", ["Pagi (07:00-15:00)", "Siang (15:00-22:00)", "Malam (22:00-07:00)", "1 Hari"], key=f"shift_{tab_name}")
        with c2:
            kategori_options = ["VIP", "Kelas 1", "Kelas 2", "Kelas 3", "Maksi", "OK", "Dokter"]
            kategori_selected = st.multiselect("Pilih Kategori Kelas *", kategori_options, default=["VIP", "Kelas 1", "Kelas 2", "Kelas 3", "Maksi", "OK", "Dokter"], key=f"kat_{tab_name}")
            
        st.divider()
        st.markdown("##### 1. Jumlah Porsi / Pasien")
        st.caption("Masukkan estimasi porsi/jumlah orang untuk masing-masing kategori yang Anda pilih di atas.")
        
        distribusi = []
        total_pasien = 0
        
        if not kategori_selected:
            st.error("Silakan pilih minimal 1 kategori kelas di atas!")
        else:
            cols = st.columns(len(kategori_selected))
            for i, kat in enumerate(kategori_selected):
                jml = cols[i].number_input(f"Porsi {kat}", min_value=1, step=1, value=1, key=f"jml_pasien_{kat}_{rc}")
                distribusi.append((kat, jml))
                total_pasien += jml
                
            st.info(f"**Total Keseluruhan Porsi:** {total_pasien} porsi")
            
        st.divider()
        st.markdown("##### 2. Input Barang / Bahan Mentah")
        
        # Header
        h1, h_sup, h2, h_sat, h5, h6 = st.columns([2.5, 1.5, 1.1, 1.1, 1.8, 0.4])
        h1.caption("Pilih Barang")
        h_sup.caption("Pilih Supplier")
        h2.caption("Qty Total")
        h_sat.caption("Satuan")
        h5.caption("Keterangan Tambahan")
        h6.caption("")
        
        row_data = []
        
        for i, row_id in enumerate(st.session_state[state_items_key]):
            default_idx = None
            if state_defaults_key in st.session_state and i < len(st.session_state[state_defaults_key]):
                def_val = st.session_state[state_defaults_key][i]
                if def_val in item_options:
                    default_idx = item_options.index(def_val)
            
            c1, c_sup, c2, c_sat, c5, c6 = st.columns([2.5, 1.5, 1.1, 1.1, 1.8, 0.4])
            with c1:
                selected_item = st.selectbox(
                    "Barang", 
                    item_options, 
                    index=default_idx, 
                    placeholder="-- Pilih Barang --", 
                    key=f"item_{tab_name}_{rc}_{row_id}", 
                    label_visibility="collapsed"
                )
            
            if not selected_item:
                with c_sup:
                    st.text_input("Supplier", value="-", disabled=True, key=f"sup_dis_{tab_name}_{rc}_{row_id}", label_visibility="collapsed")
                with c2:
                    st.number_input("Qty", value=0.0, disabled=True, key=f"qty_dis_{tab_name}_{rc}_{row_id}", label_visibility="collapsed")
                with c_sat:
                    st.text_input("Satuan", value="-", disabled=True, key=f"sat_dis_{tab_name}_{rc}_{row_id}", label_visibility="collapsed")
                with c5:
                    st.text_input("Ket", placeholder="(Opsional)", disabled=True, key=f"ket_dis_{tab_name}_{rc}_{row_id}", label_visibility="collapsed")
                with c6:
                    st.button("🗑️", key=f"del_{tab_name}_{rc}_{row_id}", on_click=remove_row, args=(row_id,))
                continue
            
            matching_items = master_df[master_df['nama_barang'] == selected_item]
            if matching_items.empty:
                continue

            # Batasi hanya supplier yang memasok barang ini di master_df
            item_sups = get_item_suppliers(selected_item, master_df)
            row_supplier_options = item_sups if item_sups else ["-"]

            # Tentukan default supplier
            default_supp = item_sups[0] if item_sups else "-"

            sup_key = f"sup_{tab_name}_{rc}_{row_id}_{selected_item}"
            chosen_supp = st.session_state.get(sup_key, default_supp)
            if chosen_supp not in row_supplier_options:
                chosen_supp = default_supp if default_supp in row_supplier_options else row_supplier_options[0]

            chosen_idx = row_supplier_options.index(chosen_supp)

            with c_sup:
                sel_supp = st.selectbox(
                    "Supplier", 
                    row_supplier_options, 
                    index=chosen_idx, 
                    key=sup_key, 
                    label_visibility="collapsed"
                )

            # Cari data master spesifik supplier yang dipilih (jika ada barisnya)
            if sel_supp != "-":
                matched_by_sup = matching_items[matching_items['supplier'].astype(str).str.strip().str.lower() == sel_supp.strip().lower()]
                if not matched_by_sup.empty:
                    item_data = matched_by_sup.iloc[0]
                    stok_fisik = float(pd.to_numeric(item_data.get('stok_sekarang', 0), errors='coerce'))
                else:
                    item_data = matching_items.iloc[0]
                    stok_fisik = float(pd.to_numeric(matching_items['stok_sekarang'], errors='coerce').sum())
            else:
                item_data = matching_items.iloc[0]
                stok_fisik = float(pd.to_numeric(matching_items['stok_sekarang'], errors='coerce').sum())

            stok_fisik = max(0.0, stok_fisik)
            harga_master = float(item_data.get('harga_master', 0))
            harga_real_val = float(item_data.get('harga_real', 0))
            harga_real = harga_real_val if harga_real_val > 0 else harga_master
            satuan = str(item_data.get('satuan', '')).strip()

            supp_tag = f" ({sel_supp})" if sel_supp != "-" else ""
            with c1:
                st.markdown(f"<div style='font-size: 11px; margin-top: -10px; margin-bottom: 5px; padding-left: 2px; color: #047857;'>💰 Real Master{supp_tag}: <b>Rp {harga_real:,.0f}</b> / {satuan} <span style='color:gray;'>(Stok: {stok_fisik:g})</span></div>", unsafe_allow_html=True)

            with c2:
                qty = st.number_input("Qty", min_value=0.0, max_value=99999.0, value=1.0, step=0.05, format="%.2f", key=f"qty_{tab_name}_{rc}_{row_id}", label_visibility="collapsed")
            
            with c_sat:
                st.text_input("Satuan", value=satuan, disabled=True, key=f"sat_{tab_name}_{rc}_{row_id}_{selected_item}", label_visibility="collapsed")
                
            with c5:
                ket = st.text_input("Keterangan", placeholder="(Opsional)", key=f"ket_{tab_name}_{rc}_{row_id}", label_visibility="collapsed")
            
            with c6:
                st.button("🗑️", key=f"del_{tab_name}_{rc}_{row_id}", on_click=remove_row, args=(row_id,))
            
            # Peringatan stok jika qty melebihi stok fisik tercatat (hanya info peringatan, tidak memblokir simpan)
            is_unlimited = str(item_data.get('status', 'True')).upper() not in ['TRUE', '1', 'YES', 'T']
            if not is_unlimited and stok_fisik < qty:
                st.caption(f"<span style='color: #d97706;'>⚠️ Stok tercatat tersisa: {stok_fisik:g} {satuan}</span>", unsafe_allow_html=True)
                
            if qty > 0:
                row_data.append({
                    "nama_barang": selected_item,
                    "supplier": sel_supp,
                    "qty": qty,
                    "harga_master": harga_master,
                    "harga_real": harga_real,
                    "keterangan": ket.strip(),
                    "stok_fisik": stok_fisik,
                    "is_error": False
                })
        
        # Tombol tambah barang
        btn_col1, btn_col2, btn_col3, _ = st.columns([1.5, 1.5, 1.5, 0.5])
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
            st.markdown('<span class="btn-clear-target"></span>', unsafe_allow_html=True)
            st.button("🗑️ Bersihkan Semua", on_click=clear_all, key=f"clear_all_{tab_name}", use_container_width=True)
        
        st.divider()
        
        if total_pasien == 0 and row_data:
            st.error("⚠️ Total Pasien tidak boleh 0! Harap isi jumlah pasien di atas.")
        elif row_data and total_pasien > 0:
            total_nilai = sum(r['qty'] * r['harga_real'] for r in row_data)
            if len(distribusi) > 1:
                st.success(f"Terdapat **{len(row_data)} macam barang** (Total: Rp {total_nilai:,.0f} [Harga Real]) yang akan dipecah secara proporsional ke **{total_pasien} porsi** ({len(distribusi)} kelas).")
            else:
                st.success(f"Terdapat **{len(row_data)} macam barang** (Total: Rp {total_nilai:,.0f} [Harga Real]) yang akan dimasukkan ke **{distribusi[0][0]}**.")
                
        submit = st.button("✓ Proses & Simpan", type="primary", use_container_width=True, disabled=(not row_data or total_pasien == 0 or not kategori_selected))
        
        if submit:
            with st.spinner("Memproses transaksi pengeluaran pasien..."):
                try:
                    trx_df = get_sheet_data(sheet_name)
                    master_df_updated = master_df.copy()
                    
                    new_rows = []
                    timestamp = datetime.datetime.combine(tgl_transaksi, now.time()).strftime("%Y-%m-%d %H:%M:%S")
                    
                    for r in row_data:
                        item_name = r['nama_barang']
                        r_supplier = str(r.get('supplier', '-')).strip()
                        
                        # 1. Potong stok master
                        matching_indices = []
                        if r_supplier and r_supplier != "-":
                            matching_indices = master_df_updated.index[
                                (master_df_updated['nama_barang'].astype(str).str.strip().str.lower() == item_name.strip().lower()) &
                                (master_df_updated['supplier'].astype(str).str.strip().str.lower() == r_supplier.lower())
                            ].tolist()
                            
                        if not matching_indices:
                            matching_indices = master_df_updated.index[
                                master_df_updated['nama_barang'].astype(str).str.strip().str.lower() == item_name.strip().lower()
                            ].tolist()
                            
                        if matching_indices:
                            idx = matching_indices[0]
                            cur_stok_m = float(master_df_updated.at[idx, 'stok_sekarang']) if pd.notna(master_df_updated.at[idx, 'stok_sekarang']) else 0.0
                            master_df_updated.at[idx, 'stok_sekarang'] = max(0.0, cur_stok_m - r['qty'])
                                        
                        # 2. Pecah proporsional per kelas pasien
                        for kat, jml in distribusi:
                            if jml > 0 and total_pasien > 0:
                                porsi = jml / total_pasien
                                qty_proporsional = r['qty'] * porsi
                                
                                ket_final = r['keterangan']
                                if not ket_final:
                                    ket_final = "Distribusi Proporsional" if len(distribusi) > 1 else "Input Satuan"
                                    
                                new_rows.append({
                                    "tanggal": timestamp,
                                    "shift": shift,
                                    "kategori": kat,
                                    "kategori_freetext": "",
                                    "nama_barang": r['nama_barang'],
                                    "supplier": r.get('supplier', '-'),
                                    "qty": qty_proporsional,
                                    "harga_master": r['harga_master'],
                                    "harga_real": r['harga_real'],
                                    "total_harga": qty_proporsional * r['harga_real'],
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

def execute_koreksi_pengeluaran_pasien(items_to_process, master_df):
    """
    Menyimpan koreksi dan/atau penghapusan transaksi pengeluaran pasien:
    1. Mengupdate nilai di SHEET_PENGELUARAN_PASIEN (atau menghapus baris jika dicentang hapus).
    2. Menyesuaikan stok fisik di SHEET_MASTER (kembalikan stok jika dihapus/qty berkurang, potong stok jika qty bertambah).
    3. Menyesuaikan sisa_qty di SHEET_STOK_MASUK (FIFO) agar tetap sinkron.
    4. Mencatat riwayat audit log ke SHEET_LOG.
    """
    trx_pasien_current = get_sheet_data(SHEET_PENGELUARAN_PASIEN)
    master_current = get_sheet_data(SHEET_MASTER)
    stok_masuk_current = get_sheet_data(SHEET_STOK_MASUK)
    
    if trx_pasien_current.empty:
        st.error("Data transaksi pengeluaran pasien tidak ditemukan!")
        return

    if master_current.empty:
        master_current = master_df.copy()
        
    if not stok_masuk_current.empty:
        if 'sisa_qty' not in stok_masuk_current.columns:
            stok_masuk_current['sisa_qty'] = stok_masuk_current['qty'].copy() if 'qty' in stok_masuk_current.columns else 0.0
        else:
            stok_masuk_current['sisa_qty'] = pd.to_numeric(
                stok_masuk_current['sisa_qty'].apply(lambda x: str(x).replace(',', '.') if isinstance(x, str) else x),
                errors='coerce'
            ).fillna(0.0)

    log_entries = []
    indices_to_drop = []
    master_changed = False
    stok_masuk_changed = False
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for item in items_to_process:
        orig_idx = item['orig_idx']
        item_name = item['nama_barang']
        kat_val = item['kategori']
        old_q = float(item['old_qty'])
        old_p = float(item['old_price'])
        old_total = float(item['old_total'])
        old_pas = float(item['old_pasien'])
        
        item_supp = str(item.get('supplier', '-')).strip()
        # JIKA DIHAPUS
        if item.get('is_deleted', False):
            indices_to_drop.append(orig_idx)
            
            # Kembalikan stok fisik ke master pada baris supplier yang sesuai
            if item_supp and item_supp != "-":
                idx_m_list = master_current.index[
                    (master_current['nama_barang'].astype(str).str.strip().str.lower() == item_name.strip().lower()) & 
                    (master_current['supplier'].astype(str).str.strip().str.lower() == item_supp.lower())
                ].tolist()
            else:
                idx_m_list = []
            if not idx_m_list:
                idx_m_list = master_current.index[master_current['nama_barang'].astype(str).str.strip().str.lower() == item_name.strip().lower()].tolist()
                
            if idx_m_list and old_q > 0:
                m_idx = idx_m_list[0]
                cur_stok = float(master_current.at[m_idx, 'stok_sekarang']) if pd.notna(master_current.at[m_idx, 'stok_sekarang']) else 0.0
                master_current.at[m_idx, 'stok_sekarang'] = cur_stok + old_q
                master_changed = True
                
            # Kembalikan sisa_qty ke batch stok masuk (FIFO restore) berdasarkan supplier
            if not stok_masuk_current.empty and 'nama_barang' in stok_masuk_current.columns and old_q > 0:
                mask_f = (stok_masuk_current['nama_barang'].astype(str).str.strip().str.lower() == item_name.strip().lower())
                if item_supp and item_supp != "-":
                    m_fifo_s = stok_masuk_current[mask_f & (stok_masuk_current['supplier'].astype(str).str.strip().str.lower() == item_supp.lower())]
                    m_fifo = m_fifo_s if not m_fifo_s.empty else stok_masuk_current[mask_f]
                else:
                    m_fifo = stok_masuk_current[mask_f]
                    
                if not m_fifo.empty:
                    m_fifo_copy = m_fifo.copy()
                    m_fifo_copy['dt_temp'] = pd.to_datetime(m_fifo_copy['tanggal'], errors='coerce')
                    sorted_b_indices = m_fifo_copy.sort_values(by=['dt_temp'], ascending=False, na_position='first').index.tolist()
                    
                    rem_to_return = old_q
                    for b_idx in sorted_b_indices:
                        if rem_to_return <= 0:
                            break
                        orig_batch_qty = float(stok_masuk_current.at[b_idx, 'qty']) if pd.notna(stok_masuk_current.at[b_idx, 'qty']) else 999999.0
                        cur_batch_sisa = float(stok_masuk_current.at[b_idx, 'sisa_qty'])
                        can_add = max(0.0, orig_batch_qty - cur_batch_sisa)
                        add_amt = min(rem_to_return, can_add) if can_add > 0 else rem_to_return
                        stok_masuk_current.at[b_idx, 'sisa_qty'] = cur_batch_sisa + add_amt
                        rem_to_return -= add_amt
                        stok_masuk_changed = True
                        
                    if rem_to_return > 0 and sorted_b_indices:
                        latest_b = sorted_b_indices[0]
                        stok_masuk_current.at[latest_b, 'sisa_qty'] = float(stok_masuk_current.at[latest_b, 'sisa_qty']) + rem_to_return
                        stok_masuk_changed = True
                        
            log_entries.append({
                "tanggal": now_str,
                "aksi": "HAPUS_PENGELUARAN_PASIEN",
                "keterangan": f"Hapus pengeluaran {item_name} ({kat_val}) [{item_supp}]: Qty {old_q:g}, Biaya Rp {old_total:,.0f}"
            })
            continue

        # JIKA DIUBAH (EDIT)
        new_q = float(item['new_qty'])
        new_p = float(item['new_price'])
        new_pas = float(item['new_pasien'])
        new_ket = str(item['new_ket']).strip()
        new_tot = new_q * new_p
        qty_diff = new_q - old_q # > 0 konsumsi bertambah, < 0 konsumsi berkurang
        
        # 1. Update data di DataFrame transaksi pengeluaran pasien
        if orig_idx in trx_pasien_current.index:
            trx_pasien_current.at[orig_idx, 'qty'] = new_q
            trx_pasien_current.at[orig_idx, 'harga_real'] = new_p
            trx_pasien_current.at[orig_idx, 'total_harga'] = new_tot
            trx_pasien_current.at[orig_idx, 'jumlah_pasien'] = new_pas
            trx_pasien_current.at[orig_idx, 'keterangan'] = new_ket
        
        # 2. Update stok master jika Qty berubah (pada baris supplier yang tepat)
        if qty_diff != 0:
            if item_supp and item_supp != "-":
                idx_m_list = master_current.index[
                    (master_current['nama_barang'].astype(str).str.strip().str.lower() == item_name.strip().lower()) & 
                    (master_current['supplier'].astype(str).str.strip().str.lower() == item_supp.lower())
                ].tolist()
            else:
                idx_m_list = []
            if not idx_m_list:
                idx_m_list = master_current.index[master_current['nama_barang'].astype(str).str.strip().str.lower() == item_name.strip().lower()].tolist()
                
            if idx_m_list:
                m_idx = idx_m_list[0]
                cur_stok = float(master_current.at[m_idx, 'stok_sekarang']) if pd.notna(master_current.at[m_idx, 'stok_sekarang']) else 0.0
                master_current.at[m_idx, 'stok_sekarang'] = max(0.0, cur_stok - qty_diff)
                master_changed = True
                
            # 3. Update FIFO stok_masuk berdasarkan supplier
            if not stok_masuk_current.empty and 'nama_barang' in stok_masuk_current.columns:
                mask_f = (stok_masuk_current['nama_barang'].astype(str).str.strip().str.lower() == item_name.strip().lower())
                if item_supp and item_supp != "-":
                    m_fifo_s = stok_masuk_current[mask_f & (stok_masuk_current['supplier'].astype(str).str.strip().str.lower() == item_supp.lower())]
                    m_fifo = m_fifo_s if not m_fifo_s.empty else stok_masuk_current[mask_f]
                else:
                    m_fifo = stok_masuk_current[mask_f]
                if not m_fifo.empty:
                    m_fifo_copy = m_fifo.copy()
                    m_fifo_copy['dt_temp'] = pd.to_datetime(m_fifo_copy['tanggal'], errors='coerce')
                    
                    if qty_diff > 0:
                        # Konsumsi bertambah: potong batch terlama yang sisa_qty > 0
                        rem_deduct = qty_diff
                        sorted_oldest = m_fifo_copy.sort_values(by=['dt_temp'], ascending=True, na_position='last').index.tolist()
                        for b_idx in sorted_oldest:
                            if rem_deduct <= 0:
                                break
                            cur_sisa = float(stok_masuk_current.at[b_idx, 'sisa_qty'])
                            if cur_sisa > 0:
                                take = min(rem_deduct, cur_sisa)
                                stok_masuk_current.at[b_idx, 'sisa_qty'] = cur_sisa - take
                                rem_deduct -= take
                                stok_masuk_changed = True
                    else:
                        # Konsumsi berkurang: kembalikan ke batch terbaru
                        rem_return = abs(qty_diff)
                        sorted_newest = m_fifo_copy.sort_values(by=['dt_temp'], ascending=False, na_position='first').index.tolist()
                        for b_idx in sorted_newest:
                            if rem_return <= 0:
                                break
                            orig_b_qty = float(stok_masuk_current.at[b_idx, 'qty']) if pd.notna(stok_masuk_current.at[b_idx, 'qty']) else 999999.0
                            cur_b_sisa = float(stok_masuk_current.at[b_idx, 'sisa_qty'])
                            can_add = max(0.0, orig_b_qty - cur_b_sisa)
                            add_amt = min(rem_return, can_add) if can_add > 0 else rem_return
                            stok_masuk_current.at[b_idx, 'sisa_qty'] = cur_b_sisa + add_amt
                            rem_return -= add_amt
                            stok_masuk_changed = True
                            
                        if rem_return > 0 and sorted_newest:
                            latest_b = sorted_newest[0]
                            stok_masuk_current.at[latest_b, 'sisa_qty'] = float(stok_masuk_current.at[latest_b, 'sisa_qty']) + rem_return
                            stok_masuk_changed = True

        log_entries.append({
            "tanggal": now_str,
            "aksi": "KOREKSI_PENGELUARAN_PASIEN",
            "keterangan": f"Koreksi {item_name} ({kat_val}): Qty {old_q:g} -> {new_q:g}, Harga Rp {old_p:,.0f} -> Rp {new_p:,.0f}, Pasien {old_pas:g} -> {new_pas:g}"
        })

    # Hapus baris yang ditandai hapus
    if indices_to_drop:
        trx_pasien_current = trx_pasien_current.drop(index=indices_to_drop).reset_index(drop=True)

    save_data(trx_pasien_current, SHEET_PENGELUARAN_PASIEN)
    if master_changed:
        save_data(master_current, SHEET_MASTER)
    if stok_masuk_changed and not stok_masuk_current.empty:
        save_data(stok_masuk_current, SHEET_STOK_MASUK)
        
    if log_entries:
        crud_log_df = get_sheet_data(SHEET_LOG)
        new_log_df = pd.DataFrame(log_entries)
        crud_log_df = pd.concat([crud_log_df, new_log_df], ignore_index=True)
        save_data(crud_log_df, SHEET_LOG)
        
    # Bersihkan session state widget rwp_ agar ter-reset bersih
    for k in list(st.session_state.keys()):
        if k.startswith(("rwp_qty_", "rwp_price_", "rwp_tot_", "rwp_pas_", "rwp_ket_", "rwp_del_")):
            del st.session_state[k]
            
    count_saved = len(items_to_process)
    count_deleted = len(indices_to_drop)
    msg = f"Berhasil menyimpan perubahan ({count_saved} baris diproses"
    if count_deleted > 0:
        msg += f", {count_deleted} dihapus"
    msg += ")!"
    st.session_state['toast_msg_riwayat_pasien'] = msg
    st.rerun()

def show_riwayat_pengeluaran_pasien():
    st.title("🛏️ Input Riwayat Pengeluaran (Pasien)")
    st.caption("Pilih rentang tanggal dan filter kelas/shift untuk menampilkan riwayat pengeluaran pasien, lalu langsung lakukan koreksi Qty, Harga Satuan Real, Jumlah Pasien, Keterangan, atau Hapus transaksi di bawah:")

    toast_key = 'toast_msg_riwayat_pasien'
    if toast_key in st.session_state:
        show_toast(st.session_state.pop(toast_key))

    today = datetime.date.today()
    master_df = get_sheet_data(SHEET_MASTER)
    trx_pasien_df = get_sheet_data(SHEET_PENGELUARAN_PASIEN)

    with st.container(border=True):
        c_k_date, c_k_kat, c_k_shift, c_k_sup, c_k_search = st.columns([1.3, 1.1, 1.1, 1.2, 1.3])
        with c_k_date:
            date_range = st.date_input(
                "📅 Tanggal Pengeluaran:",
                value=(today, today),
                key="rwp_date_range"
            )
            if isinstance(date_range, (tuple, list)):
                if len(date_range) == 2:
                    k_start, k_end = date_range
                elif len(date_range) == 1:
                    k_start = date_range[0]
                    k_end = date_range[0]
                else:
                    k_start, k_end = today, today
            else:
                k_start, k_end = date_range, date_range

        raw_kats = [str(k).strip() for k in trx_pasien_df['kategori'].dropna().unique() if str(k).strip() and str(k).strip().lower() not in ['nan', 'none']] if not trx_pasien_df.empty and 'kategori' in trx_pasien_df.columns else []
        default_kats = ["VIP", "Kelas 1", "Kelas 2", "Kelas 3", "Maksi", "OK", "Dokter"]
        all_kats = list(dict.fromkeys(default_kats + raw_kats))
        with c_k_kat:
            selected_k_kat = st.selectbox("🛏️ Filter Kategori Kelas:", ["Semua Kelas"] + all_kats, key="rwp_filter_kat")

        raw_shifts = [str(s).strip() for s in trx_pasien_df['shift'].dropna().unique() if str(s).strip() and str(s).strip().lower() not in ['nan', 'none']] if not trx_pasien_df.empty and 'shift' in trx_pasien_df.columns else []
        default_shifts = ["Pagi (07:00-15:00)", "Siang (15:00-22:00)", "Malam (22:00-07:00)", "1 Hari"]
        all_shifts = list(dict.fromkeys(default_shifts + raw_shifts))
        with c_k_shift:
            selected_k_shift = st.selectbox("🕒 Filter Shift:", ["Semua Shift"] + all_shifts, key="rwp_filter_shift")

        raw_sups = [str(s).strip() for s in trx_pasien_df['supplier'].dropna().unique() if str(s).strip() and str(s).strip().lower() not in ['nan', 'none', '-']] if not trx_pasien_df.empty and 'supplier' in trx_pasien_df.columns else []
        raw_suppliers = extract_unique_suppliers(master_df)
        all_sups = ["Semua Supplier"] + sorted(list(set(raw_sups + raw_suppliers)))
        with c_k_sup:
            selected_k_sup = st.selectbox("🏢 Filter Supplier:", all_sups, key="rwp_filter_sup")

        with c_k_search:
            k_search = st.text_input("🔍 Cari Barang / Ket:", placeholder="Ketik nama barang atau catatan...", key="rwp_search_q")

    if trx_pasien_df.empty or 'tanggal' not in trx_pasien_df.columns:
        st.info("ℹ️ Belum ada data transaksi pengeluaran pasien yang tersimpan.")
        return

    df_trx = trx_pasien_df.copy()
    df_trx['_orig_idx'] = df_trx.index
    df_trx['parsed_date'] = pd.to_datetime(df_trx['tanggal'], errors='coerce').dt.date

    mask = (df_trx['parsed_date'] >= k_start) & (df_trx['parsed_date'] <= k_end)
    if selected_k_kat != "Semua Kelas":
        mask = mask & (df_trx['kategori'].astype(str).str.strip().str.lower() == selected_k_kat.strip().lower())
    if selected_k_shift != "Semua Shift":
        mask = mask & (df_trx['shift'].astype(str).str.strip().str.lower() == selected_k_shift.strip().lower())
    if selected_k_sup != "Semua Supplier" and 'supplier' in df_trx.columns:
        mask = mask & (df_trx['supplier'].astype(str).str.strip().str.lower() == selected_k_sup.strip().lower())
    if k_search:
        search_mask = (
            df_trx['nama_barang'].astype(str).str.contains(k_search, case=False, na=False) |
            df_trx['keterangan'].astype(str).str.contains(k_search, case=False, na=False)
        )
        mask = mask & search_mask

    filtered_trx = df_trx[mask].copy().sort_values(by='tanggal', ascending=False)

    if filtered_trx.empty:
        tgl_info = k_start.strftime('%d %b %Y') if k_start == k_end else f"{k_start.strftime('%d %b %Y')} s/d {k_end.strftime('%d %b %Y')}"
        st.info(f"ℹ️ Tidak ditemukan riwayat pengeluaran pasien pada periode **{tgl_info}** dengan filter yang dipilih.")
        return

    st.markdown("<br>", unsafe_allow_html=True)

    with st.container(border=True):
        st.markdown(f"#### 📋 Tabel Koreksi Pengeluaran Pasien ({len(filtered_trx)} Baris Transaksi)")
        st.caption("Semua transaksi pengeluaran pasien hasil filter telah dimuat otomatis di bawah. Silakan ubah **Qty Keluar**, **Harga Satuan**, **Jml Pasien**, **Keterangan**, atau centang **Hapus**:")
        
        # Header kolom
        h1, h2, h3, h4, h5, h6, h7, h8 = st.columns([2.3, 0.9, 1.2, 1.2, 0.9, 1.6, 1.0, 0.6])
        h1.caption("Nama Barang & Kelas")
        h2.caption("Qty Keluar")
        h3.caption("Harga Satuan")
        h4.caption("Total Biaya")
        h5.caption("Jml Pasien")
        h6.caption("Keterangan")
        h7.caption("Status")
        h8.caption("Hapus 🗑️")
        
        items_list = []
        grand_old_total = 0.0
        grand_new_total = 0.0

        for idx, (_, row) in enumerate(filtered_trx.iterrows()):
            orig_idx = int(row['_orig_idx'])
            item_name = str(row['nama_barang'])
            kat_val = str(row.get('kategori', '-'))
            shift_val = str(row.get('shift', '-'))
            shift_short = shift_val.split(' ')[0] if ' ' in shift_val else shift_val
            supp_val = str(row.get('supplier', '-'))
            tgl_val = str(row.get('tanggal', ''))[:10]
            
            try:
                old_qty = float(row['qty']) if pd.notna(row['qty']) else 0.0
            except:
                old_qty = 0.0
                
            try:
                old_price = float(row['harga_real']) if pd.notna(row['harga_real']) else 0.0
            except:
                old_price = 0.0
                
            try:
                old_pasien = float(row['jumlah_pasien']) if pd.notna(row.get('jumlah_pasien')) else 1.0
            except:
                old_pasien = 1.0

            old_total = float(row.get('total_harga', old_qty * old_price)) if pd.notna(row.get('total_harga')) else (old_qty * old_price)
            old_ket = str(row['keterangan']) if pd.notna(row.get('keterangan')) and str(row.get('keterangan')).strip() not in ['nan', 'None'] else ""

            # Satuan dari master
            matching_m = master_df[master_df['nama_barang'] == item_name] if not master_df.empty else pd.DataFrame()
            satuan = matching_m['satuan'].iloc[0] if not matching_m.empty and 'satuan' in matching_m.columns else "Pcs"

            c1, c2, c3, c4, c5, c6, c7, c8 = st.columns([2.3, 0.9, 1.2, 1.2, 0.9, 1.6, 1.0, 0.6])
            
            with c1:
                st.text_input("Barang", value=item_name, disabled=True, key=f"rwp_name_{orig_idx}", label_visibility="collapsed")
                st.markdown(f"<div style='font-size: 11px; color: #0284c7; margin-top: -10px; margin-bottom: 4px;'>🛏️ <b>{kat_val}</b> | {shift_short} | 🏢 {supp_val} <span style='color:gray;'>({tgl_val})</span></div>", unsafe_allow_html=True)
                
            with c2:
                edit_qty = st.number_input("Qty", min_value=0.0, value=old_qty, step=0.05, format="%.2f", key=f"rwp_qty_{orig_idx}", label_visibility="collapsed")
                st.markdown(f"<div style='font-size: 11px; color: gray; margin-top: -10px; margin-bottom: 4px;'>{satuan} (Semula: {old_qty:g})</div>", unsafe_allow_html=True)
                
            with c3:
                edit_price = st.number_input("Harga Satuan", min_value=0, value=int(old_price), step=100, format="%d", key=f"rwp_price_{orig_idx}", label_visibility="collapsed")
                st.markdown(f"<div style='font-size: 11px; color: gray; margin-top: -10px; margin-bottom: 4px;'>Semula: Rp {old_price:,.0f}</div>", unsafe_allow_html=True)
                
            new_total = edit_qty * edit_price
            with c4:
                st.text_input("Total Biaya", value=f"Rp {new_total:,.0f}", disabled=True, key=f"rwp_tot_{orig_idx}", label_visibility="collapsed")
                st.markdown(f"<div style='font-size: 11px; color: gray; margin-top: -10px; margin-bottom: 4px;'>Semula: Rp {old_total:,.0f}</div>", unsafe_allow_html=True)
                
            with c5:
                edit_pasien = st.number_input("Jml Pasien", min_value=1, value=max(1, int(old_pasien)), step=1, key=f"rwp_pas_{orig_idx}", label_visibility="collapsed")
                st.markdown(f"<div style='font-size: 11px; color: gray; margin-top: -10px; margin-bottom: 4px;'>Orang</div>", unsafe_allow_html=True)

            with c6:
                edit_ket = st.text_input("Ket", value=old_ket, placeholder="Catatan...", key=f"rwp_ket_{orig_idx}", label_visibility="collapsed")

            with c8:
                is_del = st.checkbox("Hapus", value=False, key=f"rwp_del_{orig_idx}", label_visibility="collapsed")
                st.markdown("<div style='font-size: 11px; color: #ef4444; margin-top: -10px; text-align: center; font-weight: 600;'>Hapus</div>", unsafe_allow_html=True)

            is_changed = (abs(edit_qty - old_qty) > 1e-4) or (abs(edit_price - old_price) > 1e-4) or (int(old_pasien) != int(edit_pasien)) or (edit_ket.strip() != old_ket.strip())

            with c7:
                if is_del:
                    badge_html = "<div style='background-color: #fee2e2; border: 1px solid #ef4444; color: #b91c1c; padding: 7px 4px; border-radius: 8px; text-align: center; font-size: 11px; font-weight: 700; height: 38px; display: flex; align-items: center; justify-content: center;'>🗑️ Dihapus</div>"
                elif is_changed:
                    badge_html = "<div style='background-color: #fef3c7; border: 1px solid #f59e0b; color: #b45309; padding: 7px 4px; border-radius: 8px; text-align: center; font-size: 11px; font-weight: 700; height: 38px; display: flex; align-items: center; justify-content: center;'>✏️ Diubah</div>"
                else:
                    badge_html = "<div style='background-color: #f3f4f6; border: 1px solid #d1d5db; color: #4b5563; padding: 7px 4px; border-radius: 8px; text-align: center; font-size: 11px; font-weight: 700; height: 38px; display: flex; align-items: center; justify-content: center;'>⚖️ Tetap</div>"
                st.markdown(badge_html, unsafe_allow_html=True)

            items_list.append({
                'orig_idx': orig_idx,
                'nama_barang': item_name,
                'supplier': supp_val,
                'kategori': kat_val,
                'shift': shift_val,
                'tanggal': tgl_val,
                'old_qty': old_qty,
                'new_qty': edit_qty,
                'old_price': old_price,
                'new_price': edit_price,
                'old_total': old_total,
                'new_total': new_total,
                'old_pasien': old_pasien,
                'new_pasien': edit_pasien,
                'old_ket': old_ket,
                'new_ket': edit_ket.strip(),
                'is_deleted': is_del,
                'is_changed': is_changed
            })
            grand_old_total += old_total
            if not is_del:
                grand_new_total += new_total

        st.divider()

        # Bottom Summary & Save Controls
        col_calc, col_sub = st.columns([3, 1.4])
        
        changed_count = sum(1 for it in items_list if it['is_changed'] or it['is_deleted'])
        deleted_count = sum(1 for it in items_list if it['is_deleted'])
        modified_count = sum(1 for it in items_list if it['is_changed'] and not it['is_deleted'])
        diff_total = grand_new_total - grand_old_total
        
        with col_calc:
            if diff_total < 0:
                diff_tag = f"🟩 Berkurang Rp {abs(diff_total):,.0f}"
            elif diff_total > 0:
                diff_tag = f"🟥 Bertambah +Rp {diff_total:,.0f}"
            else:
                diff_tag = "⚖️ Tetap"
                
            detail_changes = []
            if modified_count > 0:
                detail_changes.append(f"{modified_count} diubah")
            if deleted_count > 0:
                detail_changes.append(f"{deleted_count} dihapus")
            change_label = ", ".join(detail_changes) if detail_changes else "Belum ada perubahan"
            
            st.info(f"**Total Biaya Semula:** Rp {grand_old_total:,.0f} ➡️ **Total Biaya Baru:** Rp {grand_new_total:,.0f} &nbsp;|&nbsp; **{diff_tag}** ({change_label})")
            
        with col_sub:
            btn_save = st.button("💾 Simpan Perubahan", type="primary", use_container_width=True, key="btn_save_riwayat_pasien", disabled=(changed_count == 0))

        if btn_save:
            items_to_process = [it for it in items_list if it['is_changed'] or it['is_deleted']]
            with st.spinner(f"Menyimpan pembaruan untuk {len(items_to_process)} transaksi pengeluaran pasien..."):
                try:
                    execute_koreksi_pengeluaran_pasien(items_to_process, master_df)
                except Exception as e:
                    st.error(f"Gagal menyimpan: {e}")

    # Tabel Riwayat Lengkap & Ekspor CSV
    st.markdown("<br>", unsafe_allow_html=True)
    with st.expander("🔍 Lihat Tabel Lengkap Riwayat Pengeluaran Pasien (Data Mentah)", expanded=False):
        cols_available = [c for c in ['tanggal', 'shift', 'kategori', 'supplier', 'nama_barang', 'qty', 'harga_master', 'harga_real', 'total_harga', 'jumlah_pasien', 'keterangan'] if c in filtered_trx.columns]
        t_disp = filtered_trx[cols_available].copy()
        for col_rp in ['harga_master', 'harga_real', 'total_harga']:
            if col_rp in t_disp.columns:
                t_disp[col_rp] = t_disp[col_rp].apply(lambda x: f"Rp {float(x):,.0f}" if pd.notna(x) else "-")
        
        rename_map = {
            'tanggal': 'Tanggal',
            'shift': 'Shift',
            'kategori': 'Kelas',
            'supplier': 'Supplier',
            'nama_barang': 'Nama Barang',
            'qty': 'Qty Keluar',
            'harga_master': 'HPP Master',
            'harga_real': 'Harga Real',
            'total_harga': 'Total Biaya',
            'jumlah_pasien': 'Jml Pasien',
            'keterangan': 'Keterangan'
        }
        t_disp = t_disp.rename(columns={k: v for k, v in rename_map.items() if k in t_disp.columns})
        
        st.dataframe(t_disp, use_container_width=True, hide_index=True)
        
        csv_bytes = filtered_trx.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Export Riwayat Pengeluaran Pasien ke CSV",
            data=csv_bytes,
            file_name=f"Riwayat_Pengeluaran_Pasien_{k_start}_sd_{k_end}.csv",
            mime="text/csv",
            key="dl_csv_riwayat_pengeluaran_pasien"
        )

