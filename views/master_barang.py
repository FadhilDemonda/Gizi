import streamlit as st
from utils.validators import validate_editor_changes, validate_new_item
import pandas as pd
from datetime import datetime
import time
from data.sheets_repository import load_data, save_data, MASTER_CSV, TRANSAKSI_CSV, SHEET_MASTER_DOKTER, get_sheet_data

def safe_float(val):
    try:
        if pd.isna(val) or val == "":
            return 0.0
        return float(val)
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
    
    if 'status' not in master_df.columns:
        master_df['status'] = True
    else:
        # Normalize to boolean for the editor
        master_df['status'] = master_df['status'].astype(str).str.upper().isin(['TRUE', '1', 'YES', 'T'])
        
    # Filter Kategori / Filter Cepat (Mirip Dashboard Utama)
    if 'kategori' in master_df.columns:
        categories = master_df['kategori'].dropna().unique().tolist()
        categories = [c for c in categories if str(c).strip() != '']
    else:
        categories = []

    available_items = master_df['nama_barang'].tolist() if 'nama_barang' in master_df.columns else []
    cat_options = [f"Semua ({len(master_df)})", "Khusus Dokter", "Khusus Manajemen"]
    for c in categories:
        count = len(master_df[master_df['kategori'] == c])
        cat_options.append(f"{c} ({count})")

    selected_cat = st.pills("KATEGORI / FILTER CEPAT:", cat_options, default=cat_options[0], key="master_cat_pills")

    if selected_cat == "Khusus Dokter":
        target_items = ["Roti", "Buah (Dokter)", "Telur Rebus", "Snack (Dokter)", "Le Minerale 600 ml", "Kopi KA", "Kopi 3 in 1", "Pocari", "Buavita", "Teh", "Oxy", "Buah (Dr Edi)", "Snack (Dr Edi)", "tempe goreng", "gula DM", "Teh (ok)", "pop mie"]
        valid_items = find_matching_items(available_items, target_items)
        df_to_edit = master_df[master_df['nama_barang'].isin(valid_items)].copy()
    elif selected_cat == "Khusus Manajemen":
        target_items = ["Le Mineral 330", "Snack", "Roti", "Jus", "Cleo", "Buah (Dokter)"]
        valid_items = find_matching_items(available_items, target_items)
        df_to_edit = master_df[master_df['nama_barang'].isin(valid_items)].copy()
    elif selected_cat and not selected_cat.startswith("Semua"):
        real_cat = selected_cat.split(" (")[0]
        df_to_edit = master_df[master_df['kategori'] == real_cat].copy()
    else:
        df_to_edit = master_df.copy()

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
        
    st.info("💡 **Tips CRUD:** Anda bisa mengubah isi langsung di dalam sel tabel. Untuk menghapus baris, klik kolom paling kiri dari baris tersebut dan tekan tombol `Delete` di *keyboard* Anda. Anda juga bisa menambah baris di bagian paling bawah tabel.")
    
    edited_df = st.data_editor(
        df_to_edit, 
        use_container_width=True,
        hide_index=True,
        num_rows="dynamic",
        key=f"master_editor_{selected_cat}",
        column_config={
            "kategori": st.column_config.SelectboxColumn(
                "Kategori",
                options=["Bahan Basah", "Bahan Kering", "Alat"],
                required=True,
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
                    
                    for _, row in edited_df.iterrows():
                        kode = row['kode_barang']
                        if kode in full_master_df['kode_barang'].values:
                            old_row = full_master_df[full_master_df['kode_barang'] == kode].iloc[0]
                            
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
                                    "nama_barang": row['nama_barang'],
                                    "keterangan": f"CRUD Update: {' | '.join(changes)}"
                                })
                            # Update existing row in full_master_df
                            idx = full_master_df.index[full_master_df['kode_barang'] == kode][0]
                            for col in edited_df.columns:
                                if col in full_master_df.columns:
                                    full_master_df.at[idx, col] = row[col]
                        else:
                            new_trx_list.append({
                                "tanggal": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                "kategori": "Insert Master",
                                "kategori_freetext": "Admin",
                                "nama_barang": row['nama_barang'],
                                "keterangan": "CRUD Insert: Barang baru ditambahkan"
                            })
                            full_master_df = pd.concat([full_master_df, pd.DataFrame([row])], ignore_index=True)
                            
                    # Check deletions ONLY within the items that were in df_to_edit
                    deleted_kodes = []
                    for _, old_row in df_to_edit.iterrows():
                        if old_row['kode_barang'] not in edited_df['kode_barang'].values:
                            deleted_kodes.append(old_row['kode_barang'])
                            new_trx_list.append({
                                "tanggal": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                "kategori": "Delete Master",
                                "kategori_freetext": "Admin",
                                "nama_barang": old_row['nama_barang'],
                                "keterangan": "CRUD Delete: Barang dihapus dari sistem"
                            })
                    if deleted_kodes:
                        full_master_df = full_master_df[~full_master_df['kode_barang'].isin(deleted_kodes)]
                            
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
        
        h1, h2, h3, hcat, h4, h5, h6, h7 = st.columns([1, 2, 1, 1.5, 1.5, 1, 1, 0.5])
        h1.caption("Kode *")
        h2.caption("Nama Barang *")
        h3.caption("Satuan *")
        hcat.caption("Kategori *")
        h4.caption("Harga (Rp) *")
        h5.caption("Min Stok *")
        h6.caption("Stok Awal")
        
        row_data = []
        for row_id in st.session_state[st_key]:
            c1, c2, c3, ccat, c4, c5, c6, c7 = st.columns([1, 2, 1, 1.5, 1.5, 1, 1, 0.5])
            
            with c1:
                kode_brg = st.text_input("Kode", key=f"kode_{row_id}", label_visibility="collapsed")
            with c2:
                nama_brg = st.text_input("Nama", key=f"nama_{row_id}", label_visibility="collapsed")
            with c3:
                sat_brg = st.selectbox("Satuan", unique_satuan, key=f"sat_{row_id}", label_visibility="collapsed")
            with ccat:
                kat_brg = st.selectbox("Kategori", ["Bahan Basah", "Bahan Kering", "Alat"], key=f"kat_{row_id}", label_visibility="collapsed")
            with c4:
                harga_brg = st.number_input("Harga", min_value=0.0, step=100.0, key=f"harga_{row_id}", label_visibility="collapsed")
            with c5:
                stok_min = st.number_input("Min", min_value=0.0, value=10.0, step=1.0, format="%.2f", key=f"min_{row_id}", label_visibility="collapsed")
            with c6:
                stok_skrg = st.number_input("Awal", min_value=0.0, value=0.0, step=1.0, format="%.2f", key=f"awal_{row_id}", label_visibility="collapsed")
            with c7:
                st.button("🗑️", key=f"del_master_{row_id}", on_click=remove_master_row, args=(row_id,))
                
            row_data.append({
                'kode_barang': kode_brg, 'nama_barang': nama_brg, 
                'kategori': kat_brg, 'satuan': sat_brg, 
                'harga_master': harga_brg, 'stok_minimum': stok_min, 
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
                is_valid, error_msg = validate_new_item(r['kode_barang'], r['nama_barang'], master_df)
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
