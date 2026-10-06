import streamlit as st
from utils.validators import validate_editor_changes, validate_new_item
import pandas as pd
from datetime import datetime
import time
from data.sheets_repository import load_data, save_data, MASTER_CSV, TRANSAKSI_CSV, SHEET_MASTER_DOKTER, get_sheet_data
from views.transaksi import extract_unique_suppliers, match_supplier

def safe_float(val):
    try:
        if pd.isna(val) or val == "":
            return 0.0
        if isinstance(val, (int, float)):
            return float(val)
        val_str = str(val).strip().replace(',', '.')
        if '/' in val_str:
            num, den = val_str.split('/')
            return float(num) / float(den)
        return float(val_str)
    except:
        return 0.0

def safe_str(val):
    if pd.isna(val):
        return ""
    return str(val).strip()

def find_matching_items(available_items, target_items):
    valid_items = []
    for ti in target_items:
        ti_clean = ti.lower().strip()
        match = None
        for item in available_items:
            if str(item).lower().strip() == ti_clean:
                match = item
                break
        if not match:
            for item in available_items:
                if str(item).lower().strip().startswith(ti_clean):
                    match = item
                    break
        if not match:
            for item in available_items:
                if ti_clean in str(item).lower().strip():
                    match = item
                    break
        if match and match not in valid_items:
            valid_items.append(match)
    return valid_items

def show_master_barang():
    st.header("📦 Master Barang")
    
    master_df, _ = load_data()
    
    if 'harga_real' not in master_df.columns:
        master_df['harga_real'] = master_df['harga_master'].copy() if 'harga_master' in master_df.columns else 0.0
        
    if 'status' not in master_df.columns:
        master_df['status'] = True
    else:
        # Normalize to boolean for the editor
        master_df['status'] = master_df['status'].astype(str).str.upper().isin(['TRUE', '1', 'YES', 'T'])
        
    # 1. Filter Supplier & Filter Pencarian
    col_sup, col_search = st.columns([1.5, 2.5])
    with col_sup:
        supp_list = extract_unique_suppliers(master_df)
        sup_options = ["Semua Supplier"] + supp_list
        selected_sup = st.selectbox("🏢 Filter Supplier:", sup_options, index=0, key="master_sup_filter")
    with col_search:
        search_q = st.text_input("🔍 Cari Nama / Kode Barang:", placeholder="Ketik nama atau kode barang...", key="master_search_input")
        
    if selected_sup != "Semua Supplier" and 'supplier' in master_df.columns:
        df_by_sup = master_df[master_df['supplier'].apply(lambda x: match_supplier(x, selected_sup))].copy()
    else:
        df_by_sup = master_df.copy()
        
    # 2. Filter Kategori / Filter Cepat (Mirip Dashboard Utama)
    if 'kategori' in master_df.columns:
        categories = master_df['kategori'].dropna().unique().tolist()
        categories = [c for c in categories if str(c).strip() != '']
    else:
        categories = []

    available_items = df_by_sup['nama_barang'].tolist() if 'nama_barang' in df_by_sup.columns else []
    
    # Format terbaru: hiraukan paket virtual (Snack, Buah, Roti), fokus pada barang fisik riil
    target_dokter = [
        "Telur Rebus", "Le Minerale 600 ml", "Le Minerale 330 ml", 
        "Kopi KA", "Kopi 3 In 1", "Pocari", "Buavita", 
        "Teh", "Teh (ok)", "Oxy", "Bear Brand", "Yakult", 
        "Puding", "Susu Ultra Mini", "Tempe Goreng", "Gula DM", "Pop Mie"
    ]
    target_manajemen = [
        "Le Minerale 330 ml", "Le Mineral 330", "Jus", "Cleo 220 ml", "Cleo 240 ml", "Cleo"
    ]

    def is_snack_buah_roti(name):
        nl = str(name).lower().strip()
        return any(x in nl for x in ['snack', 'buah', 'roti'])

    valid_dokter = [it for it in find_matching_items(available_items, target_dokter) if not is_snack_buah_roti(it)]
    valid_manajemen = [it for it in find_matching_items(available_items, target_manajemen) if not is_snack_buah_roti(it)]

    count_doc = len(df_by_sup[df_by_sup['nama_barang'].isin(valid_dokter)])
    count_man = len(df_by_sup[df_by_sup['nama_barang'].isin(valid_manajemen)])

    cat_options = [
        f"Semua ({len(df_by_sup)})", 
        f"Khusus Dokter ({count_doc})", 
        f"Khusus Manajemen ({count_man})"
    ]
    for c in categories:
        count = len(df_by_sup[df_by_sup['kategori'] == c])
        cat_options.append(f"{c} ({count})")

    selected_cat = st.pills("KATEGORI / FILTER CEPAT:", cat_options, default=cat_options[0], key=f"master_cat_pills_{selected_sup}")

    if selected_cat and selected_cat.startswith("Khusus Dokter"):
        df_to_edit = df_by_sup[df_by_sup['nama_barang'].isin(valid_dokter)].copy()
    elif selected_cat and selected_cat.startswith("Khusus Manajemen"):
        df_to_edit = df_by_sup[df_by_sup['nama_barang'].isin(valid_manajemen)].copy()
    elif selected_cat and not selected_cat.startswith("Semua"):
        real_cat = selected_cat.split(" (")[0]
        df_to_edit = df_by_sup[df_by_sup['kategori'] == real_cat].copy()
    else:
        df_to_edit = df_by_sup.copy()

    if search_q and not df_to_edit.empty:
        search_mask = (
            df_to_edit['nama_barang'].astype(str).str.contains(search_q, case=False, na=False) |
            df_to_edit['kode_barang'].astype(str).str.contains(search_q, case=False, na=False)
        )
        df_to_edit = df_to_edit[search_mask].copy()

    col_head, col_exp = st.columns([3, 1])
    with col_head:
        st.subheader("Daftar Barang (CRUD)")
    with col_exp:
        csv_data = df_to_edit.to_csv(index=False).encode('utf-8')
        export_label = f"📥 Export ke CSV ({len(df_to_edit)})" if len(df_to_edit) != len(master_df) else "📥 Export ke CSV"
        st.download_button(
            label=export_label,
            data=csv_data,
            file_name=f"master_barang_{datetime.today().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            use_container_width=True
        )
        
    # st.info("💡 **Tips CRUD:** Anda bisa mengubah isi langsung di dalam sel tabel. Untuk menghapus baris, klik kolom paling kiri dari baris tersebut dan tekan tombol `Delete` di *keyboard* Anda. Anda juga bisa menambah baris di bagian paling bawah tabel.")
    
    edited_df = st.data_editor(
        df_to_edit, 
        use_container_width=True,
        hide_index=True,
        num_rows="dynamic",
        key=f"master_editor_{selected_sup}_{selected_cat}",
        column_order=[
            "kode_barang", "nama_barang", "kategori", "supplier", 
            "satuan", "status", "stok_minimum", "stok_sekarang", 
            "harga_master", "harga_real", "Sumber HPP"
        ],
        column_config={
            "supplier": st.column_config.TextColumn(
                "Supplier",
                help="Nama supplier / vendor penyedia barang ini (bisa dipisah titik koma ';')"
            ),
            "kategori": st.column_config.SelectboxColumn(
                "Kategori",
                options=["Bahan Basah", "Bahan Kering", "Alat"],
                required=True,
            ),
            "harga_master": st.column_config.NumberColumn(
                "HPP Master (Rp)",
                help="Harga pokok acuan/standar master",
                format="Rp %d"
            ),
            "harga_real": st.column_config.NumberColumn(
                "Harga Real Terakhir (Rp)",
                help="Harga beli riil dari stok masuk terakhir (digunakan untuk pengeluaran pasien)",
                format="Rp %d"
            ),
            "stok_sekarang": st.column_config.NumberColumn(
                "Stok Sekarang",
                min_value=0.0,
                step=0.05,
                format="%.2f"
            ),
            "stok_minimum": st.column_config.NumberColumn(
                "Stok Minimum",
                min_value=0.0,
                step=0.05,
                format="%.2f"
            ),
            "status": st.column_config.CheckboxColumn(
                "Status (Pantau Stok)",
                help="Jika dicentang, stok barang ini akan dipantau dan masuk peringatan Kritis. Jika tidak dicentang, dianggap Bahan Bebas.",
                default=True
            )
        }
    )
    
    if not df_to_edit.equals(edited_df):
        if st.button("💾 Simpan Perubahan ke Database", type="primary", key="save_master_barang"):
            is_valid, error_msg = validate_editor_changes(edited_df)
            if not is_valid:
                st.error(error_msg)
            else:
                with st.spinner("Menyimpan dan mensinkronisasi data ke Cloud..."):
                    full_master_df, _ = load_data()
                    _, transaksi_df = load_data()
                    
                    if 'status' not in full_master_df.columns:
                        full_master_df['status'] = True
                    else:
                        full_master_df['status'] = full_master_df['status'].astype(str).str.upper().isin(['TRUE', '1', 'YES', 'T'])
                        
                    new_trx_list = []
                    used_indices = set()
                    
                    for _, row in edited_df.iterrows():
                        kode = str(row.get('kode_barang', '')).strip()
                        sup = str(row.get('supplier', '')).strip().lower()
                        nama = str(row.get('nama_barang', '')).strip().lower()
                        
                        # Cocokkan baris yang sesuai di full_master_df berdasarkan kode & supplier
                        match_candidates = []
                        if sup and 'supplier' in full_master_df.columns:
                            match_candidates = full_master_df.index[
                                (full_master_df['kode_barang'].astype(str).str.strip() == kode) &
                                (full_master_df['supplier'].astype(str).str.strip().str.lower() == sup)
                            ].tolist()
                            if not match_candidates:
                                match_candidates = full_master_df.index[
                                    (full_master_df['nama_barang'].astype(str).str.strip().str.lower() == nama) &
                                    (full_master_df['supplier'].astype(str).str.strip().str.lower() == sup)
                                ].tolist()
                        
                        if not match_candidates:
                            match_candidates = [
                                i for i in full_master_df.index[
                                    full_master_df['kode_barang'].astype(str).str.strip() == kode
                                ].tolist() if i not in used_indices
                            ]
                            
                        valid_matches = [i for i in match_candidates if i not in used_indices]
                        if not valid_matches and match_candidates:
                            valid_matches = match_candidates

                        if valid_matches:
                            idx = valid_matches[0]
                            used_indices.add(idx)
                            old_row = full_master_df.loc[idx]
                            
                            stok_new = safe_float(row.get('stok_sekarang', 0))
                            stok_old = safe_float(old_row.get('stok_sekarang', 0))
                            harga_new = safe_float(row.get('harga_master', 0))
                            harga_old = safe_float(old_row.get('harga_master', 0))
                            nama_new = safe_str(row.get('nama_barang', ''))
                            nama_old = safe_str(old_row.get('nama_barang', ''))
                            min_new = safe_float(row.get('stok_minimum', 0))
                            min_old = safe_float(old_row.get('stok_minimum', 0))
                            status_new = str(row.get('status', True))
                            status_old = str(old_row.get('status', True))
                            
                            changes = []
                            if stok_new != stok_old:
                                changes.append(f"Stok: {stok_old} -> {stok_new}")
                            if harga_new != harga_old:
                                changes.append(f"Harga: {harga_old} -> {harga_new}")
                            if nama_new != nama_old:
                                changes.append(f"Nama: {nama_old} -> {nama_new}")
                            if min_new != min_old:
                                changes.append(f"Min Stok: {min_old} -> {min_new}")
                            if status_new != status_old:
                                changes.append(f"Pantau Stok: {status_old} -> {status_new}")
                            
                            if changes:
                                new_trx_list.append({
                                    "tanggal": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                    "kategori": "Update Master",
                                    "kategori_freetext": "Admin",
                                    "nama_barang": row.get('nama_barang', ''),
                                    "keterangan": f"CRUD Update: {' | '.join(changes)}"
                                })
                            # Update existing row in full_master_df
                            for col in edited_df.columns:
                                if col in full_master_df.columns:
                                    full_master_df.at[idx, col] = row[col]
                        else:
                            new_trx_list.append({
                                "tanggal": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                "kategori": "Insert Master",
                                "kategori_freetext": "Admin",
                                "nama_barang": row.get('nama_barang', ''),
                                "keterangan": "CRUD Insert: Barang baru ditambahkan"
                            })
                            full_master_df = pd.concat([full_master_df, pd.DataFrame([row])], ignore_index=True)
                            
                    # Check deletions ONLY within the items that were in df_to_edit
                    deleted_indices = []
                    edited_signatures = set()
                    for _, erow in edited_df.iterrows():
                        e_k = str(erow.get('kode_barang', '')).strip()
                        e_s = str(erow.get('supplier', '')).strip().lower()
                        e_n = str(erow.get('nama_barang', '')).strip().lower()
                        edited_signatures.add((e_k, e_s))
                        edited_signatures.add((e_n, e_s))
                        if not e_s:
                            edited_signatures.add(e_k)

                    for _, old_row in df_to_edit.iterrows():
                        o_k = str(old_row.get('kode_barang', '')).strip()
                        o_s = str(old_row.get('supplier', '')).strip().lower()
                        o_n = str(old_row.get('nama_barang', '')).strip().lower()
                        
                        is_present = (
                            (o_k, o_s) in edited_signatures or
                            (o_n, o_s) in edited_signatures or
                            (not o_s and o_k in edited_signatures)
                        )
                        if not is_present:
                            match_to_del = full_master_df.index[
                                (full_master_df['kode_barang'].astype(str).str.strip() == o_k) &
                                (full_master_df['supplier'].astype(str).str.strip().str.lower() == o_s)
                            ].tolist()
                            if not match_to_del:
                                match_to_del = full_master_df.index[
                                    (full_master_df['nama_barang'].astype(str).str.strip().str.lower() == o_n) &
                                    (full_master_df['supplier'].astype(str).str.strip().str.lower() == o_s)
                                ].tolist()
                            if not match_to_del and not o_s:
                                match_to_del = full_master_df.index[
                                    full_master_df['kode_barang'].astype(str).str.strip() == o_k
                                ].tolist()
                            if match_to_del:
                                deleted_indices.extend(match_to_del)
                                new_trx_list.append({
                                    "tanggal": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                    "kategori": "Delete Master",
                                    "kategori_freetext": "Admin",
                                    "nama_barang": old_row.get('nama_barang', ''),
                                    "keterangan": f"CRUD Delete: Barang dihapus ({old_row.get('supplier', '-')})"
                                })
                    if deleted_indices:
                        full_master_df = full_master_df.drop(index=list(set(deleted_indices))).reset_index(drop=True)
                            
                    if new_trx_list:
                        new_trx_df = pd.DataFrame(new_trx_list)
                        transaksi_df = pd.concat([transaksi_df, new_trx_df], ignore_index=True)
                        save_data(transaksi_df, TRANSAKSI_CSV)
                        
                    save_data(full_master_df, MASTER_CSV)
                
                st.success("✅ Perubahan berhasil disimpan dan log transaksi tercatat!")
                time.sleep(1)
                st.rerun()
    
    st.markdown("---")
    
    st.subheader("➕ Tambah Barang Baru")
    
    unique_satuan = master_df['satuan'].dropna().unique().tolist()
    if not unique_satuan:
        unique_satuan = ["Kg", "Liter", "Pack", "Sak"]
        
    supp_list = extract_unique_suppliers(master_df)
    unique_suppliers = ["-"] + [s for s in supp_list if s and s != "-"] + ["Lainnya (Ketik)"]
        
    st_key = "dyn_items_master"
    if st_key not in st.session_state:
        st.session_state[st_key] = [0]
        
    def add_master_row():
        new_id = max(st.session_state[st_key]) + 1 if st.session_state[st_key] else 0
        st.session_state[st_key].append(new_id)
        
    def remove_master_row(row_id):
        st.session_state[st_key].remove(row_id)
        
    with st.container(border=True):
        st.caption("Gunakan formulir ini untuk menambah beberapa barang sekaligus.")
        
        h1, h2, hsup, h3, hcat, h4, h5, h6, h7 = st.columns([1, 1.8, 1.3, 0.9, 1.2, 1.2, 0.8, 0.8, 0.4])
        h1.caption("Kode *")
        h2.caption("Nama Barang *")
        hsup.caption("Supplier")
        h3.caption("Satuan *")
        hcat.caption("Kategori *")
        h4.caption("Harga (Rp) *")
        h5.caption("Min Stok *")
        h6.caption("Stok Awal")
        
        row_data = []
        for row_id in st.session_state[st_key]:
            c1, c2, csup, c3, ccat, c4, c5, c6, c7 = st.columns([1, 1.8, 1.3, 0.9, 1.2, 1.2, 0.8, 0.8, 0.4])
            
            with c1:
                kode_brg = st.text_input("Kode", key=f"kode_{row_id}", label_visibility="collapsed")
            with c2:
                nama_brg = st.text_input("Nama", key=f"nama_{row_id}", label_visibility="collapsed")
            with csup:
                def_sup_idx = 0
                if selected_sup != "Semua Supplier" and selected_sup in unique_suppliers:
                    def_sup_idx = unique_suppliers.index(selected_sup)
                sel_sup = st.selectbox("Supplier", unique_suppliers, index=def_sup_idx, key=f"sup_opt_{row_id}", label_visibility="collapsed")
                if sel_sup == "Lainnya (Ketik)":
                    sup_brg = st.text_input("Ketik Supplier", key=f"sup_custom_{row_id}", placeholder="Ketik nama supplier...", label_visibility="collapsed")
                else:
                    sup_brg = sel_sup
            with c3:
                sat_brg = st.selectbox("Satuan", unique_satuan, key=f"sat_{row_id}", label_visibility="collapsed")
            with ccat:
                kat_brg = st.selectbox("Kategori", ["Bahan Basah", "Bahan Kering", "Alat"], key=f"kat_{row_id}", label_visibility="collapsed")
            with c4:
                harga_brg = st.number_input("Harga", min_value=0.0, step=100.0, key=f"harga_{row_id}", label_visibility="collapsed")
            with c5:
                stok_min = st.number_input("Min", min_value=0.0, value=10.0, step=0.05, format="%.2f", key=f"min_{row_id}", label_visibility="collapsed")
            with c6:
                stok_skrg = st.number_input("Awal", min_value=0.0, value=0.0, step=0.05, format="%.2f", key=f"awal_{row_id}", label_visibility="collapsed")
            with c7:
                st.button("🗑️", key=f"del_master_{row_id}", on_click=remove_master_row, args=(row_id,))
                
            row_data.append({
                'kode_barang': kode_brg, 'nama_barang': nama_brg, 
                'supplier': sup_brg,
                'kategori': kat_brg, 'satuan': sat_brg, 
                'harga_master': harga_brg,
                'harga_real': harga_brg,
                'stok_minimum': stok_min, 
                'stok_sekarang': stok_skrg,
                'status': True
            })
            
        st.button("➕ Tambah Baris", on_click=add_master_row, key="add_master_row_btn")
        st.divider()
        
        submit = st.button("💾 Simpan Semua Barang Baru", type="primary", use_container_width=True, key="save_new_master_barang")
        if submit:
            if len(row_data) == 0:
                st.error("Tidak ada data barang yang akan disimpan.")
                return
                
            valid_rows = []
            errors = []
            for idx, r in enumerate(row_data):
                if not r['kode_barang'] or not r['nama_barang']:
                    errors.append(f"Baris ke-{idx+1}: Kode dan Nama Barang harus diisi.")
                    continue
                is_valid, error_msg = validate_new_item(r['kode_barang'], r['nama_barang'], master_df, r.get('supplier', ''))
                if not is_valid:
                    errors.append(f"Baris ke-{idx+1}: {error_msg}")
                    continue
                valid_rows.append(r)
                
            if errors:
                for err in errors:
                    st.error(err)
            elif valid_rows:
                with st.spinner("Menyimpan data..."):
                    new_df = pd.DataFrame(valid_rows)
                    master_df = pd.concat([master_df, new_df], ignore_index=True)
                    save_data(master_df, MASTER_CSV)
                    
                    _, trx_df = load_data()
                    new_trx_list = []
                    for r in valid_rows:
                        new_trx_list.append({
                            "tanggal": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "kategori": "Insert Master",
                            "kategori_freetext": "Admin",
                            "nama_barang": r['nama_barang'],
                            "keterangan": "CRUD Insert: Barang baru ditambahkan (via Form)"
                        })
                    trx_df = pd.concat([trx_df, pd.DataFrame(new_trx_list)], ignore_index=True)
                    save_data(trx_df, TRANSAKSI_CSV)
                    
                st.session_state[st_key] = [0]
                st.success(f"✅ {len(valid_rows)} barang baru berhasil ditambahkan!")
                time.sleep(1)
                st.rerun()
