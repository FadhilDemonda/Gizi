import streamlit as st
import pandas as pd
import datetime
from data.sheets_repository import get_sheet_data, save_data, SHEET_MASTER

def generate_kode_barang(kategori, existing_kodes):
    """
    Generate kode barang unik otomatis sesuai kategori.
    Bahan Basah -> BB-XXX
    Bahan Kering -> BK-XXX
    Alat -> AL-XXX
    Lainnya -> BRG-XXX
    """
    prefix_map = {
        "Bahan Basah": "BB",
        "Bahan Kering": "BK",
        "Alat": "AL"
    }
    pref = prefix_map.get(kategori, "BRG")
    max_num = 0
    for k in existing_kodes:
        k_str = str(k).strip()
        if k_str.startswith(f"{pref}-"):
            try:
                num = int(k_str.split("-")[1])
                if num > max_num:
                    max_num = num
            except:
                pass
    next_num = max_num + 1
    candidate = f"{pref}-{next_num:03d}"
    while candidate in existing_kodes:
        next_num += 1
        candidate = f"{pref}-{next_num:03d}"
    return candidate

@st.dialog("📦 Tambah Barang Baru ke Master", width="large")
def dialog_tambah_barang(state_items_key, state_defaults_key, toast_key=None):
    """
    Dialog form CRUD ringkas untuk menambahkan satu atau lebih barang baru ke Master Barang
    dan langsung memasukkannya ke form transaksi aktif.
    """
    st.markdown("Masukkan data barang yang belum ada di database Master Barang. Anda bisa mengisi **lebih dari 1 barang** sekaligus.")
    st.caption("💡 *Tips:* Klik baris kosong di tabel untuk mulai mengisi. Klik tanda **+** di bawah tabel jika ingin menambah baris lagi.")
    
    # Template awal dengan 2 baris kosong siap isi
    df_template = pd.DataFrame([
        {
            "nama_barang": "",
            "kategori": "Bahan Basah",
            "satuan": "kg",
            "harga_master": 0.0,
            "stok_awal": 0.0,
            "stok_minimum": 0.0,
            "status": True
        },
        {
            "nama_barang": "",
            "kategori": "Bahan Basah",
            "satuan": "kg",
            "harga_master": 0.0,
            "stok_awal": 0.0,
            "stok_minimum": 0.0,
            "status": True
        }
    ])
    
    edited_df = st.data_editor(
        df_template,
        use_container_width=True,
        hide_index=True,
        num_rows="dynamic",
        key="editor_dialog_tambah_barang",
        column_config={
            "nama_barang": st.column_config.TextColumn(
                "Nama Barang *",
                help="Contoh: Semangka Kuning",
                required=True,
                width="large"
            ),
            "kategori": st.column_config.SelectboxColumn(
                "Kategori *",
                options=["Bahan Basah", "Bahan Kering", "Alat"],
                default="Bahan Basah",
                required=True,
                width="medium"
            ),
            "satuan": st.column_config.TextColumn(
                "Satuan *",
                help="Contoh: kg, pcs, bks, ikat, dll",
                default="kg",
                required=True,
                width="small"
            ),
            "harga_master": st.column_config.NumberColumn(
                "Harga Master (Rp) *",
                min_value=0.0,
                step=500.0,
                default=0.0,
                format="Rp %d",
                width="medium"
            ),
            "stok_awal": st.column_config.NumberColumn(
                "Stok Awal Gudang",
                min_value=0.0,
                step=1.0,
                default=0.0,
                format="%.2f",
                width="small"
            ),
            "stok_minimum": st.column_config.NumberColumn(
                "Stok Minimum",
                min_value=0.0,
                step=1.0,
                default=0.0,
                format="%.2f",
                width="small"
            ),
            "status": st.column_config.CheckboxColumn(
                "Pantau Stok",
                help="Jika dicentang, stok dipantau pada peringatan kritis.",
                default=True,
                width="small"
            )
        }
    )
    
    c_save, c_cancel = st.columns([2, 1])
    with c_save:
        save_btn = st.button("💾 Simpan ke Master & Masukkan ke Form", type="primary", use_container_width=True)
        
    if save_btn:
        valid_rows = edited_df[edited_df['nama_barang'].astype(str).str.strip() != ""].copy()
        if valid_rows.empty:
            st.error("⚠️ Silakan isi minimal 1 Nama Barang sebelum menyimpan!")
            return
            
        # Validasi duplikat dalam form
        input_names = [str(x).strip().title() for x in valid_rows['nama_barang']]
        lower_names = [n.lower() for n in input_names]
        if len(lower_names) != len(set(lower_names)):
            st.error("⚠️ Terdapat nama barang yang duplikat dalam tabel yang Anda masukkan!")
            return
            
        # Validasi duplikat dengan Master Barang yang sudah ada
        master_df = get_sheet_data(SHEET_MASTER)
        existing_names_lower = master_df['nama_barang'].dropna().astype(str).str.strip().str.lower().tolist()
        
        duplicates_existing = [name for name in input_names if name.lower() in existing_names_lower]
        if duplicates_existing:
            st.error(f"⚠️ Barang berikut sudah terdaftar di Master Barang: **{', '.join(duplicates_existing)}**")
            return
            
        with st.spinner("Menyimpan barang baru ke Master Data..."):
            existing_kodes = master_df['kode_barang'].dropna().astype(str).tolist()
            new_rows_for_master = []
            new_item_names = []
            
            for _, r in valid_rows.iterrows():
                nama = str(r['nama_barang']).strip().title()
                kat = str(r.get('kategori', 'Bahan Basah')).strip()
                sat = str(r.get('satuan', 'kg')).strip() if str(r.get('satuan', '')).strip() else "kg"
                hrg = float(r.get('harga_master', 0.0))
                stok_awal = float(r.get('stok_awal', 0.0))
                stok_min = float(r.get('stok_minimum', 0.0))
                stat = bool(r.get('status', True))
                
                kode = generate_kode_barang(kat, existing_kodes)
                existing_kodes.append(kode)
                
                new_rows_for_master.append({
                    "kode_barang": kode,
                    "nama_barang": nama,
                    "kategori": kat,
                    "golongan": "",
                    "satuan": sat,
                    "status": stat,
                    "stok_minimum": stok_min,
                    "stok_sekarang": stok_awal,
                    "harga_master": hrg,
                    "Sumber HPP": "Input Form Langsung"
                })
                new_item_names.append(nama)
                
            # Update master_df dan simpan ke sheet
            master_df_updated = pd.concat([master_df, pd.DataFrame(new_rows_for_master)], ignore_index=True)
            save_data(master_df_updated, SHEET_MASTER)
            
            # Tambahkan barang baru ke form caller saat ini
            if state_items_key not in st.session_state:
                st.session_state[state_items_key] = []
            if state_defaults_key not in st.session_state:
                st.session_state[state_defaults_key] = []
                
            while len(st.session_state[state_defaults_key]) < len(st.session_state[state_items_key]):
                st.session_state[state_defaults_key].append(None)
                
            for item_name in new_item_names:
                # Bila baris pertama masih kosong/default, ganti baris pertama
                if len(st.session_state[state_items_key]) == 1 and (len(st.session_state[state_defaults_key]) == 0 or st.session_state[state_defaults_key][0] is None):
                    st.session_state[state_defaults_key] = [item_name]
                else:
                    new_id = max(st.session_state[state_items_key]) + 1 if st.session_state[state_items_key] else 0
                    st.session_state[state_items_key].append(new_id)
                    st.session_state[state_defaults_key].append(item_name)
                    
            if toast_key:
                st.session_state[toast_key] = f"Berhasil mendaftarkan {len(new_item_names)} barang baru ke Master & form!"
                
            st.rerun()
