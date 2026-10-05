import streamlit as st
import datetime
import pandas as pd
from data.sheets_repository import (
    get_sheet_data, save_data, SHEET_MASTER, SHEET_PENGELUARAN_DOKTER, SHEET_MASTER_DOKTER
)
from views.pengeluaran_common import (
    show_toast, multi_select_dialog, get_item_suppliers,
    get_prioritized_options, format_pkg_summary, render_pkg_config_column,
    get_pkg_qty, get_pkg_sup, resolve_pkg_supplier, parse_qty
)
from views.transaksi import extract_unique_suppliers

@st.dialog("Konfirmasi Penyimpanan Massal 📦")
def confirm_batch_save_dialog(valid_rows_to_save, sheet_name, shift, kategori, master_df, toast_key, tgl_transaksi=None):
    jml_barang = sum(r['qty'] for r in valid_rows_to_save)
    dokters = set(r['kategori_freetext'] for r in valid_rows_to_save)
    jml_dokter = len(dokters)
    
    st.markdown(f"Anda akan menyimpan total **{jml_barang:,.0f} item barang** untuk **{jml_dokter} dokter/kelompok**.")
    
    with st.expander("📝 Lihat Detail Dokter & Barang", expanded=True):
        dokter_list_str = ", ".join(sorted(list(dokters)))
        st.markdown(f"**👨‍⚕️ Daftar Dokter:**<br><span style='font-size:0.9em; color:gray;'>{dokter_list_str}</span>", unsafe_allow_html=True)
        
        item_totals = {}
        for r in valid_rows_to_save:
            item = r['nama_barang']
            qty = r['qty']
            item_totals[item] = item_totals.get(item, 0) + qty
            
        item_list_str = ", ".join([f"**{qty:,.0f}** {item}" for item, qty in item_totals.items()])
        st.markdown(f"<br>**📦 Ringkasan Barang:**<br><span style='font-size:0.9em; color:gray;'>{item_list_str}</span>", unsafe_allow_html=True)

    st.warning("Apakah Anda yakin data yang diinput sudah benar?")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Batal", use_container_width=True):
            st.rerun()
    with col2:
        if st.button("Ya, Simpan Semua!", type="primary", use_container_width=True):
            with st.spinner("Menyimpan..."):
                try:
                    now = datetime.datetime.now()
                    timestamp = datetime.datetime.combine(tgl_transaksi, now.time()).strftime("%Y-%m-%d %H:%M:%S") if tgl_transaksi else now.strftime("%Y-%m-%d %H:%M:%S")
                    trx_df = get_sheet_data(sheet_name)
                    new_rows = []
                    master_df_updated = master_df.copy()
                    
                    for r in valid_rows_to_save:
                        r_name = r['nama_barang']
                        r_sup = r.get('supplier', '-')
                        matching_indices = []
                        if r_sup and r_sup != "-":
                            matching_indices = master_df_updated.index[
                                (master_df_updated['nama_barang'].astype(str).str.strip().str.lower() == r_name.strip().lower()) &
                                (master_df_updated['supplier'].astype(str).str.strip().str.lower() == r_sup.strip().lower())
                            ].tolist()
                        if not matching_indices:
                            matching_indices = master_df_updated.index[master_df_updated['nama_barang'] == r_name].tolist()
                            
                        if matching_indices:
                            idx = matching_indices[0]
                            cur_stk = float(master_df_updated.at[idx, 'stok_sekarang']) if pd.notna(master_df_updated.at[idx, 'stok_sekarang']) else 0.0
                            master_df_updated.at[idx, 'stok_sekarang'] = max(0.0, cur_stk - r['qty'])
                        
                        new_rows.append({
                            "tanggal": timestamp,
                            "shift": shift,
                            "kategori": kategori,
                            "kategori_freetext": r['kategori_freetext'],
                            "nama_barang": r['nama_barang'],
                            "supplier": r.get('supplier', '-'),
                            "qty": r['qty'],
                            "harga_master": r['harga_master'],
                            "harga_real": r['harga_real'],
                            "total_harga": r['qty'] * r['harga_real'],
                            "keterangan": r['keterangan']
                        })
                        
                    save_data(master_df_updated, SHEET_MASTER)
                    trx_df = pd.concat([trx_df, pd.DataFrame(new_rows)], ignore_index=True)
                    save_data(trx_df, sheet_name)
                        
                    st.session_state[toast_key] = f"Berhasil menyimpan {jml_barang:,.0f} barang untuk {jml_dokter} dokter/kategori!"
                    
                    # Clear dynamic grid state
                    for k in list(st.session_state.keys()):
                        if k.startswith("editor_batch_doc_"):
                            del st.session_state[k]
                    
                    st.rerun()
                except Exception as e:
                    st.error(f"Gagal menyimpan: {e}")

@st.dialog("Pilih Dokter yang Dinas 👨‍⚕️")
def pilih_dokter_dialog(df_docs, state_doc_key, kategori):
    st.write("Centang dokter yang sedang dinas:")
    
    if kategori == "Dokter Praktek" and not df_docs.empty and 'spesialis' in df_docs.columns:
        spesialis_list = sorted(list(set([str(s).strip().title() for s in df_docs['spesialis'].dropna().tolist() if str(s).strip()])))
        selected_spes = st.multiselect(
            "Filter Spesialis:", 
            options=spesialis_list, 
            default=[], 
            placeholder="Semua Spesialis (atau pilih beberapa spesialis)...", 
            label_visibility="collapsed"
        )
        
        if selected_spes:
            filtered_df = df_docs[df_docs['spesialis'].astype(str).str.strip().str.title().isin(selected_spes)]
        else:
            filtered_df = df_docs
    else:
        filtered_df = df_docs
        
    filtered_docs_list = sorted(list(set([str(d).strip() for d in filtered_df['dokter'].dropna().tolist() if str(d).strip()])))
    
    search_q = st.text_input("🔍 Cari Dokter:", placeholder="Ketik nama dokter...", label_visibility="collapsed").lower()
    docs_to_show = [d for d in filtered_docs_list if search_q in d.lower()]
    
    if state_doc_key not in st.session_state:
        st.session_state[state_doc_key] = []
        
    temp_key = f"temp_set_{state_doc_key}"
    if temp_key not in st.session_state:
        st.session_state[temp_key] = set(st.session_state[state_doc_key])
        
    st.caption(f"Total terpilih: {len(st.session_state[temp_key])} dokter secara keseluruhan")
    
    ver_key = f"ver_{temp_key}"
    if ver_key not in st.session_state:
        st.session_state[ver_key] = 0
    doc_ver = st.session_state[ver_key]

    c_btn1, c_btn2 = st.columns(2)
    with c_btn1:
        if st.button("☑️ Pilih Semua", use_container_width=True):
            st.session_state[temp_key].update(docs_to_show)
            for k in list(st.session_state.keys()):
                if k.startswith("chk_doc_"):
                    del st.session_state[k]
            st.session_state[ver_key] = doc_ver + 1
            st.rerun()
    with c_btn2:
        if st.button("🔲 Kosongkan", use_container_width=True):
            st.session_state[temp_key].clear()
            for k in list(st.session_state.keys()):
                if k.startswith("chk_doc_"):
                    del st.session_state[k]
            st.session_state[ver_key] = doc_ver + 1
            st.rerun()
            
    new_dialog_set = set([x for x in st.session_state[temp_key] if x not in docs_to_show])
    
    with st.container(height=350, border=True):
        if not docs_to_show:
            st.info("Tidak ada dokter yang cocok.")
            
        cols = st.columns(2)
        for i, d in enumerate(docs_to_show):
            with cols[i % 2]:
                is_checked = st.checkbox(d, value=(d in st.session_state[temp_key]), key=f"chk_doc_{doc_ver}_{i}_{d}")
                if is_checked:
                    new_dialog_set.add(d)
                    
    st.session_state[temp_key] = new_dialog_set
    
    if st.button("➕ Terapkan Pilihan", type="primary", use_container_width=True):
        st.session_state[state_doc_key] = list(st.session_state[temp_key])
        for k in list(st.session_state.keys()):
            if k.startswith("chk_doc_"):
                del st.session_state[k]
        del st.session_state[temp_key]
        st.rerun()

def show_pengeluaran_dokter():
    st.markdown("""
        <style>
        /* Styling khusus dropdown Atur Isi Paket bernuansa Biru */
        div[data-testid="stExpander"] {
            border-radius: 10px !important;
            border: 1.5px solid #93c5fd !important;
            background-color: #f0f7ff !important;
            box-shadow: 0 2px 8px rgba(37, 99, 235, 0.08) !important;
            overflow: hidden !important;
            margin-top: 6px !important;
            margin-bottom: 6px !important;
            transition: all 0.2s ease !important;
        }
        div[data-testid="stExpander"]:hover {
            border-color: #60a5fa !important;
            box-shadow: 0 4px 12px rgba(37, 99, 235, 0.15) !important;
        }
        div[data-testid="stExpander"] details {
            border: none !important;
            background: transparent !important;
        }
        div[data-testid="stExpander"] summary {
            background: linear-gradient(90deg, #eff6ff 0%, #dbeafe 100%) !important;
            padding: 10px 14px !important;
            border-radius: 8px !important;
            transition: background 0.2s ease !important;
        }
        div[data-testid="stExpander"] summary:hover {
            background: linear-gradient(90deg, #dbeafe 0%, #bfdbfe 100%) !important;
        }
        div[data-testid="stExpander"] summary p,
        div[data-testid="stExpander"] summary span,
        div[data-testid="stExpander"] summary strong {
            color: #1e40af !important;
            font-weight: 700 !important;
            font-size: 0.92rem !important;
        }
        div[data-testid="stExpander"] summary svg {
            color: #2563eb !important;
            fill: #2563eb !important;
        }
        div[data-testid="stExpanderDetails"] {
            background-color: #ffffff !important;
            border-top: 1px dashed #93c5fd !important;
            padding: 14px 16px !important;
            border-radius: 0 0 8px 8px !important;
        }

        /* Styling tombol dropdown Isi Paket bernuansa Biru */
        div[data-testid="stPopover"] {
            width: 100% !important;
        }
        div[data-testid="stPopover"] > button {
            background: linear-gradient(90deg, #eff6ff 0%, #dbeafe 100%) !important;
            border: 1.5px solid #93c5fd !important;
            color: #1e40af !important;
            font-weight: 700 !important;
            border-radius: 8px !important;
            height: 38px !important;
            padding: 0 10px !important;
            width: 100% !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            box-shadow: 0 1px 3px rgba(37, 99, 235, 0.08) !important;
            transition: all 0.2s ease !important;
        }
        div[data-testid="stPopover"] > button:hover {
            background: linear-gradient(90deg, #dbeafe 0%, #bfdbfe 100%) !important;
            border-color: #3b82f6 !important;
            box-shadow: 0 3px 8px rgba(37, 99, 235, 0.2) !important;
        }
        div[data-testid="stPopover"] > button p,
        div[data-testid="stPopover"] > button span {
            color: #1e40af !important;
            font-weight: 700 !important;
            font-size: 0.92rem !important;
        }
        div[data-testid="stPopover"] > button svg {
            color: #2563eb !important;
            fill: #2563eb !important;
        }
        div[data-testid="stPopoverBody"] {
            min-width: 420px !important;
            max-width: 520px !important;
            background-color: #ffffff !important;
            border: 1.5px solid #93c5fd !important;
            border-radius: 12px !important;
            box-shadow: 0 10px 25px rgba(37, 99, 235, 0.18) !important;
            padding: 16px !important;
        }
        </style>
    """, unsafe_allow_html=True)
    
    col_title, col_date = st.columns([2.8, 1.4])
    with col_title:
        st.title("🩺 Pengeluaran Dokter")
    with col_date:
        st.markdown('<span class="timestamp-blue-marker"></span>', unsafe_allow_html=True)
        tgl_transaksi = st.date_input("📅 Tanggal Transaksi", value=datetime.date.today(), key="tgl_trx_dokter")
    
    master_df = get_sheet_data(SHEET_MASTER)
    if master_df.empty:
        st.warning("Data Master Barang kosong!")
        return
        
    master_dokter_df = get_sheet_data(SHEET_MASTER_DOKTER)
    item_options = list(dict.fromkeys([str(x).strip() for x in master_df['nama_barang'].dropna().tolist() if str(x).strip() and str(x).strip().lower() != 'nan']))
    raw_suppliers = extract_unique_suppliers(master_df)
    supplier_options = ["-"] + raw_suppliers + [s for s in ["Kasir", "Lainnya"] if s not in raw_suppliers]
    
    master_dict_by_name_sup = {}
    master_dict_by_name = {}
    for _, r in master_df.iterrows():
        master_dict_by_name_sup[(r['nama_barang'], r['supplier'])] = r.to_dict()
        if r['nama_barang'] not in master_dict_by_name:
            master_dict_by_name[r['nama_barang']] = r.to_dict()
    
    toast_key = 'toast_msg_BatchDokter'
    if toast_key in st.session_state:
        show_toast(st.session_state.pop(toast_key))
        
    with st.container(border=True):
        c1, c2, c3 = st.columns([1, 1.5, 1.5])
        with c1:
            shift = st.selectbox("Keterangan Waktu \*", ["Pagi (07:00-15:00)", "Siang (15:00-22:00)", "Malam (22:00-07:00)", "1 Hari"], key="shift_dokter_unified")
        with c2:
            kategori = st.selectbox("Kategori Dokter \*", ["Dr. Edi", "Dokter Praktek", "Dokter Jaga", "OK Makanan", "OK Snack", "Lainnya"], key="kat_dokter_unified")
            
        state_doc_key = f"selected_docs_{kategori}"
        if state_doc_key not in st.session_state:
            st.session_state[state_doc_key] = []
            
        with c3:
            if kategori in ["Dokter Praktek", "Dokter Jaga"]:
                st.markdown("<div style='margin-top: 27px;'></div>", unsafe_allow_html=True)
                
                # Filter docs
                if master_dokter_df.empty or 'spesialis' not in master_dokter_df.columns:
                    df_docs = pd.DataFrame(columns=['dokter', 'spesialis'])
                else:
                    master_dokter_df['spesialis_clean'] = master_dokter_df['spesialis'].astype(str).str.strip().str.upper()
                    if kategori == "Dokter Jaga":
                        df_docs = master_dokter_df[master_dokter_df['spesialis_clean'] == 'UMUM']
                    else:
                        df_docs = master_dokter_df[master_dokter_df['spesialis_clean'] != 'UMUM']
                
                btn1, btn2 = st.columns(2)
                with btn1:
                    if st.button("🔍 Pilih Dokter", use_container_width=True):
                        temp_key = f"temp_{state_doc_key}"
                        if temp_key in st.session_state:
                            del st.session_state[temp_key]
                        pilih_dokter_dialog(df_docs, state_doc_key, kategori)
                with btn2:
                    if st.button("🗑️ Reset", use_container_width=True):
                        st.session_state[state_doc_key] = []
                        st.rerun()
            else:
                st.markdown("<div style='margin-top: 27px;'></div>", unsafe_allow_html=True)
                freetext_val = st.text_input("Keterangan (Opsional)", placeholder="Nama Dokter / Tujuan...", key="free_dokter_unified", label_visibility="collapsed")
                
        st.divider()
        
        if kategori in ["Dokter Praktek", "Dokter Jaga"]:
            selected_docs = st.session_state[state_doc_key]
            if not selected_docs:
                st.info("👆 Silakan tekan tombol 'Pilih Dokter' di atas untuk menampilkan tabel input massal.")
                return
                
            st.success(f"Telah memilih **{len(selected_docs)}** dokter: {', '.join(selected_docs)}")
            
            # --- PENGATURAN KOMPOSISI PAKET SHIFT INI (SNACK, BUAH & ROTI) ---
            pkg_snack_key = f"pkg_snack_items_{kategori}"
            pkg_buah_key = f"pkg_buah_items_{kategori}"
            pkg_roti_key = f"pkg_roti_items_{kategori}"
            pkg_toggle_key = f"toggle_pkg_{kategori}"
            
            selected_snack_items = st.session_state.get(pkg_snack_key, [])
            selected_buah_items = st.session_state.get(pkg_buah_key, [])
            selected_roti_items = st.session_state.get(pkg_roti_key, [])
            
            snack_summary = format_pkg_summary(selected_snack_items, "pkg_snack", "Snack (Dokter)", kategori, master_dict_by_name)
            buah_summary = format_pkg_summary(selected_buah_items, "pkg_buah", "Buah (Dokter)", kategori, master_dict_by_name)
            roti_summary = format_pkg_summary(selected_roti_items, "pkg_roti", "Roti", kategori, master_dict_by_name)
            
            snack_options = get_prioritized_options(['pastel', 'lemper', 'risol', 'kue', 'sus', 'pie', 'bolu', 'puding', 'bapel', 'snack'], item_options)
            buah_options = get_prioritized_options(['pisang', 'jeruk', 'apel', 'semangka', 'melon', 'naga', 'buah'], item_options)
            roti_options = get_prioritized_options(['roti', 'bread'], item_options)
            
            with st.expander(f"⚙️ **Atur Isi Paket ({kategori})** — Klik untuk Buka/Tutup Form", expanded=False):
                st.markdown("""
                <div style="background-color: #fff5f5; border: 1px solid #fecaca; border-radius: 8px; padding: 10px 14px; margin-bottom: 12px;">
                    <h5 style="margin: 0; color: #991b1b;">🍱 Atur Komposisi Barang Fisik & Supplier Shift Ini</h5>
                    <p style="margin: 4px 0 0 0; color: #7f1d1d; font-size: 0.88em;">Pilih barang fisik, lalu atur <b>Qty</b> dan <b>Supplier</b> masing-masing secara berdampingan di bawah ini:</p>
                </div>
                """, unsafe_allow_html=True)
                
                c_snk, c_buh, c_rot = st.columns(3)
                with c_snk:
                    render_pkg_config_column("Paket Snack", "🥐", snack_options, selected_snack_items, pkg_snack_key, "pkg_snack", "Snack (Dokter)", kategori, master_df, raw_suppliers, "Pilih kue/snack...")
                with c_buh:
                    render_pkg_config_column("Paket Buah", "🍎", buah_options, selected_buah_items, pkg_buah_key, "pkg_buah", "Buah (Dokter)", kategori, master_df, raw_suppliers, "Pilih buah...")
                with c_rot:
                    render_pkg_config_column("Pilihan Roti", "🍞", roti_options, selected_roti_items, pkg_roti_key, "pkg_roti", "Roti", kategori, master_df, raw_suppliers, "Pilih jenis roti...")
                        
                selected_snack_items = st.session_state.get(pkg_snack_key, [])
                selected_buah_items = st.session_state.get(pkg_buah_key, [])
                selected_roti_items = st.session_state.get(pkg_roti_key, [])
                snack_summary = format_pkg_summary(selected_snack_items, "pkg_snack", "Snack (Dokter)", kategori, master_dict_by_name)
                buah_summary = format_pkg_summary(selected_buah_items, "pkg_buah", "Buah (Dokter)", kategori, master_dict_by_name)
                roti_summary = format_pkg_summary(selected_roti_items, "pkg_roti", "Roti", kategori, master_dict_by_name)
            
            st.markdown(f"""
            <div style="background-color: #fff5f5; border: 1px solid #fecaca; border-radius: 8px; padding: 7px 12px; font-size: 0.88em; line-height: 1.4; margin-top: 6px; margin-bottom: 8px;">
                <b style="color: #991b1b;">🍱 Paket Aktif Shift Ini:</b> &nbsp;
                <span>🥐 <b>Snack:</b> <span style="color: #0f766e;">{snack_summary}</span></span> &nbsp;|&nbsp; 
                <span>🍎 <b>Buah:</b> <span style="color: #b45309;">{buah_summary}</span></span> &nbsp;|&nbsp; 
                <span>🍞 <b>Roti:</b> <span style="color: #4338ca;">{roti_summary}</span></span>
            </div>
            """, unsafe_allow_html=True)
            
            # EXCEL GRID UI
            target_items = ["Roti", "Buah (Dokter)", "Telur Rebus", "Snack (Dokter)", "Le Minerale 600 ml", "Kopi KA", "Kopi 3 in 1", "Pocari", "Buavita", "Teh", "Oxy"]
            valid_items = []
            for ti in target_items:
                match = None
                # Priority 1: Exact match
                for item in item_options:
                    if str(item).lower().strip() == ti.lower().strip():
                        match = item; break
                # Priority 2: Starts with
                if not match:
                    for item in item_options:
                        if str(item).lower().strip().startswith(ti.lower().strip()):
                            match = item; break
                # Priority 3: Contains substring
                if not match:
                    for item in item_options:
                        if ti.lower().strip() in str(item).lower().strip():
                            match = item; break
                if match and match not in valid_items:
                    valid_items.append(match)
                    
            data = []
            for d in selected_docs:
                row = {"Nama Dokter": d}
                for vi in valid_items:
                    row[vi] = 0
                data.append(row)
                
            df_init = pd.DataFrame(data)
            
            config = {
                "Nama Dokter": st.column_config.TextColumn("👨‍⚕️ Nama Dokter", disabled=True, width="medium")
            }
            for vi in valid_items:
                vi_lower = vi.lower()
                if "snack" in vi_lower:
                    is_cfg = bool(selected_snack_items)
                    label = "🍱 Snack (Paket)"
                    help_txt = f"1 Paket = {snack_summary}" if is_cfg else "⚠️ Wajib atur isi paket di atas terlebih dahulu!"
                elif "buah" in vi_lower:
                    is_cfg = bool(selected_buah_items)
                    label = "🍎 Buah (Paket)"
                    help_txt = f"1 Paket = {buah_summary}" if is_cfg else "⚠️ Wajib atur isi paket di atas terlebih dahulu!"
                elif vi_lower == "roti" or "roti" in vi_lower:
                    is_cfg = bool(selected_roti_items)
                    label = "🍞 Roti"
                    help_txt = f"1 Porsi = {roti_summary}" if is_cfg else "⚠️ Wajib atur isi paket di atas terlebih dahulu!"
                else:
                    is_cfg = True
                    label = vi
                    help_txt = None
                    
                config[vi] = st.column_config.NumberColumn(
                    label, 
                    help=help_txt,
                    min_value=0.0, 
                    step=0.05, 
                    default=0.0,
                    format="%.2f",
                    disabled=not is_cfg
                )
                
            # st.info(f"💡 **Tips:** Ketik qty paket untuk dokter. Saat disimpan: **Snack** diurai menjadi *{snack_summary}*, **Buah** menjadi *{buah_summary}*, **Roti** menjadi *{roti_summary}*.")
            edited_df = st.data_editor(
                df_init, 
                column_config=config, 
                num_rows="fixed",
                use_container_width=True,
                hide_index=True,
                key=f"editor_batch_doc_{shift}_{kategori}"
            )
            
            st.divider()
            col_calc, col_sub = st.columns([3, 1])
            
            total_real = 0
            total_items_qty = 0
            valid_rows_to_save = []
            missing_pkg_errors = []
            
            master_dict_by_name_sup = {}
            master_dict_by_name = {}
            for _, r in master_df.iterrows():
                master_dict_by_name_sup[(r['nama_barang'], r['supplier'])] = r.to_dict()
                if r['nama_barang'] not in master_dict_by_name:
                    master_dict_by_name[r['nama_barang']] = r.to_dict()
            
            for index, row in edited_df.iterrows():
                nama_dokter = str(row.get('Nama Dokter', '')).strip()
                if not nama_dokter: continue
                    
                for col_item in valid_items:
                    qty = parse_qty(row.get(col_item, 0), 0.0)
                    if qty > 0:
                        
                        col_lower = col_item.lower()
                        items_to_add = []
                        
                        if "snack" in col_lower:
                            if not selected_snack_items:
                                missing_pkg_errors.append("Snack")
                                continue
                            for sit in selected_snack_items:
                                q_unit = get_pkg_qty("pkg_snack", kategori, sit, 1.0)
                                s_chosen = get_pkg_sup("pkg_snack", kategori, sit)
                                items_to_add.append((sit, qty * q_unit, f"Paket Snack ({qty:g} pkt)", s_chosen))
                        elif "buah" in col_lower:
                            if not selected_buah_items:
                                missing_pkg_errors.append("Buah")
                                continue
                            for bit in selected_buah_items:
                                q_unit = get_pkg_qty("pkg_buah", kategori, bit, 1.0)
                                s_chosen = get_pkg_sup("pkg_buah", kategori, bit)
                                items_to_add.append((bit, qty * q_unit, f"Paket Buah ({qty:g} pkt)", s_chosen))
                        elif (col_lower == "roti" or "roti" in col_lower):
                            if not selected_roti_items:
                                missing_pkg_errors.append("Roti")
                                continue
                            for rit in selected_roti_items:
                                q_unit = get_pkg_qty("pkg_roti", kategori, rit, 1.0)
                                s_chosen = get_pkg_sup("pkg_roti", kategori, rit)
                                items_to_add.append((rit, qty * q_unit, f"Roti ({qty:g} porsi)", s_chosen))
                        else:
                            it_sups = get_item_suppliers(col_item, master_df)
                            def_s = it_sups[0] if it_sups else "-"
                            items_to_add.append((col_item, qty, "Batch Input", def_s))
                            
                        for item_name, item_qty, item_ket, item_chosen_sup in items_to_add:
                            if item_name in master_dict_by_name:
                                final_item_sup = resolve_pkg_supplier(item_name, item_chosen_sup, master_dict_by_name)
                                if not final_item_sup or final_item_sup in ["None", "nan", ""]:
                                    final_item_sup = "-"
                                m_info = master_dict_by_name_sup.get((item_name, final_item_sup), master_dict_by_name.get(item_name, {}))
                                harga_master = float(m_info.get('harga_master', 0))
                                stok_fisik = max(0.0, float(m_info.get('stok_sekarang', 0)))
                                
                                total_real += (item_qty * harga_master)
                                total_items_qty += item_qty
                                
                                valid_rows_to_save.append({
                                    "nama_barang": item_name,
                                    "supplier": final_item_sup,
                                    "qty": item_qty,
                                    "harga_master": harga_master,
                                    "harga_real": harga_master,
                                    "keterangan": item_ket,
                                    "kategori_freetext": nama_dokter,
                                    "stok_fisik": stok_fisik,
                                    "is_error": False
                                })

            # Validasi Stok Agregat
            total_needed_per_item_sup = {}
            for r in valid_rows_to_save:
                total_needed_per_item_sup[(r['nama_barang'], r['supplier'])] = total_needed_per_item_sup.get((r['nama_barang'], r['supplier']), 0) + r['qty']
                
            insufficient_stock_errors = []
            error_items = set()
            for (item_name, sup_name), needed_qty in total_needed_per_item_sup.items():
                if (item_name, sup_name) in master_dict_by_name_sup:
                    m_info = master_dict_by_name_sup[(item_name, sup_name)]
                    stok_fisik = max(0.0, float(m_info.get('stok_sekarang', 0)))
                else:
                    m_info = master_dict_by_name.get(item_name, {})
                    matching_m = master_df[master_df['nama_barang'] == item_name]
                    stok_fisik = max(0.0, float(pd.to_numeric(matching_m['stok_sekarang'], errors='coerce').sum())) if not matching_m.empty else max(0.0, float(m_info.get('stok_sekarang', 0)))
                if m_info:
                    is_unlimited = str(m_info.get('status', 'True')).upper() not in ['TRUE', '1', 'YES', 'T'] or float(m_info.get('stok_minimal', 0)) == 0
                    if not is_unlimited and stok_fisik < needed_qty:
                        supp_str = f" ({sup_name})" if sup_name and sup_name != "-" else ""
                        insufficient_stock_errors.append(f"• **{item_name}**{supp_str} (dibutuhkan: {needed_qty:g}, stok tersisa: {stok_fisik:g})")
                        error_items.add(item_name)
                        
            for r in valid_rows_to_save:
                if r['nama_barang'] in error_items:
                    r['is_error'] = True

            if valid_rows_to_save:
                col_calc.success(f"**Terdapat {total_items_qty:,.0f} item fisik untuk {len(set([r['kategori_freetext'] for r in valid_rows_to_save]))} dokter!** | Total Nilai: Rp {total_real:,.0f}")
                if insufficient_stock_errors:
                    col_calc.error("⚠️ **Peringatan Stok Kurang:**<br>" + "<br>".join(insufficient_stock_errors), icon="🚨")
            else:
                col_calc.info("Tabel masih kosong atau semua qty 0.")
                
            with col_sub:
                submit = st.button("✓ Simpan Transaksi", type="primary", use_container_width=True, disabled=(len(valid_rows_to_save) == 0))
                
            if submit:
                if missing_pkg_errors:
                    st.error(f"❌ Gagal Simpan! Isi paket {', '.join(sorted(set(missing_pkg_errors)))} belum diatur. Silakan klik '⚙️ Atur Isi Paket' di atas terlebih dahulu!")
                    return
                if any(r['is_error'] for r in valid_rows_to_save):
                    st.error("Silakan perbaiki stok barang yang merah (tidak cukup) terlebih dahulu!")
                    return
                confirm_batch_save_dialog(valid_rows_to_save, SHEET_PENGELUARAN_DOKTER, shift, kategori, master_df, toast_key, tgl_transaksi=tgl_transaksi)
                
        else:
            # DYNAMIC ROWS UI FOR DR EDI / LAINNYA
            tab_name = f"DokterSingle_{kategori}_{shift}_v3"
            state_items_key = f"dyn_items_{tab_name}"
            state_defaults_key = f"dyn_defaults_{tab_name}"
            reset_counter_key = f"reset_ctr_{tab_name}"
            
            if reset_counter_key not in st.session_state:
                st.session_state[reset_counter_key] = 0
            rc = st.session_state[reset_counter_key]
            
            if state_items_key in st.session_state and kategori == "Dr. Edi" and not st.session_state.get(state_defaults_key):
                del st.session_state[state_items_key]
                if state_defaults_key in st.session_state:
                    del st.session_state[state_defaults_key]

            if state_items_key not in st.session_state:
                default_names = []
                if kategori == "Dr. Edi":
                    default_names = ["Buah (Dr Edi)", "Snack (Dr Edi)", "Le Minerale 330 ml", "Pocari", "Buavita", "Bear Brand", "Yakult", "Puding", "Susu Ultra Mini"]
                elif kategori == "OK Makanan":
                    default_names = ["tempe goreng", "Kopi 3 in 1", "kopi ka", "gula DM", "Teh (ok)"]
                elif kategori == "OK Snack":
                    if "Malam" in shift:
                        default_names = ["pop mie", "Kopi 3 in 1", "Roti"]
                    else:
                        default_names = ["Snack (ok)", "Kopi 3 in 1", "kopi ka"]
                
                valid_defaults = []
                for d in default_names:
                    match = None
                    for item in item_options:
                        if str(item).lower().strip() == d.lower().strip():
                            match = item; break
                    if not match:
                        for item in item_options:
                            if str(item).lower().strip().startswith(d.lower().strip()):
                                match = item; break
                    if not match:
                        for item in item_options:
                            if d.lower().strip() in str(item).lower().strip():
                                match = item; break
                    if match:
                        valid_defaults.append(match)
                        
                if valid_defaults:
                    st.session_state[state_items_key] = list(range(len(valid_defaults)))
                    st.session_state[state_defaults_key] = valid_defaults
                else:
                    st.session_state[state_items_key] = [0]
                    st.session_state[state_defaults_key] = []

            has_pkg_feature = kategori in ["Dr. Edi", "OK Snack"]
            pkg_snack_key = f"pkg_snack_items_{kategori}"
            pkg_toggle_key = f"toggle_pkg_{kategori}"
            
            if has_pkg_feature:
                default_snack_label = "Snack (Dr Edi)" if kategori == "Dr. Edi" else "Snack (ok)"
                selected_snack_items = st.session_state.get(pkg_snack_key, [])
                snack_summary = format_pkg_summary(selected_snack_items, "pkg_snack", default_snack_label, kategori, master_dict_by_name)
                
                if kategori == "Dr. Edi":
                    pkg_buah_key = f"pkg_buah_items_{kategori}"
                    default_buah_label = "Buah (Dr Edi)"
                    selected_buah_items = st.session_state.get(pkg_buah_key, [])
                    buah_summary = format_pkg_summary(selected_buah_items, "pkg_buah", default_buah_label, kategori, master_dict_by_name)
                else:
                    pkg_buah_key = None
                    default_buah_label = ""
                    selected_buah_items = []
                    buah_summary = ""
                    
                snack_options = get_prioritized_options(['pastel', 'lemper', 'risol', 'kue', 'sus', 'pie', 'bolu', 'puding', 'bapel', 'snack'], item_options)
                buah_options = get_prioritized_options(['pisang', 'jeruk', 'apel', 'semangka', 'melon', 'naga', 'buah'], item_options)
            else:
                has_pkg_feature = False
                selected_snack_items = []
                selected_buah_items = []
                snack_summary = ""
                buah_summary = ""
                default_snack_label = ""
                default_buah_label = ""
                
            def add_row():
                new_id = max(st.session_state[state_items_key]) + 1 if st.session_state[state_items_key] else 0
                st.session_state[state_items_key].append(new_id)
                
            def remove_row(row_id):
                st.session_state[state_items_key].remove(row_id)
                
            def clear_all():
                st.session_state[state_items_key] = [0]
                st.session_state[state_defaults_key] = []
                for k in list(st.session_state.keys()):
                    if k.startswith((f"qty_{tab_name}", f"item_{tab_name}", f"sat_{tab_name}", f"ket_{tab_name}", f"sup_{tab_name}")):
                        del st.session_state[k]
                
            h1, h_sup, h2, h_sat, h5, h6 = st.columns([2.5, 1.5, 1.1, 1.1, 1.8, 0.4])
            h1.caption("Pilih Barang")
            h_sup.caption("Supplier / Isi Paket")
            h2.caption("Qty")
            h_sat.caption("Satuan")
            h5.caption("Keterangan Tambahan")
            h6.caption("")
            
            row_data = []
            rendered_pkg_expanders = set()
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
                
                is_snack_row = False
                is_buah_row = False
                if has_pkg_feature:
                    sel_clean = str(selected_item).lower().strip()
                    if kategori == "Dr. Edi":
                        if "snack (dr edi)" in sel_clean or sel_clean in ["snack", "snack (dr. edi)"]:
                            is_snack_row = True
                        elif "buah (dr edi)" in sel_clean or sel_clean in ["buah", "buah (dr. edi)"]:
                            is_buah_row = True
                    elif kategori == "OK Snack":
                        if "snack (ok)" in sel_clean or sel_clean in ["snack", "snack ok"]:
                            is_snack_row = True

                item_data = master_df[master_df['nama_barang'] == selected_item].iloc[0]
                stok_fisik = max(0.0, float(item_data.get('stok_sekarang', 0)))
                harga_master = float(item_data.get('harga_master', 0))
                satuan = item_data.get('satuan', '')
                is_unlimited = str(item_data.get('status', 'True')).upper() not in ['TRUE', '1', 'YES', 'T'] or float(item_data.get('stok_minimal', 0)) == 0
                
                default_qty = 0.0
                max_qty = 99999.0 if (is_unlimited or (is_snack_row and selected_snack_items) or (is_buah_row and selected_buah_items)) else max(1.0, float(stok_fisik), default_qty)
                
                if is_snack_row:
                    with c_sup:
                        with st.popover("Isi Paket", use_container_width=True, key=f"pop_pkg_snack_{tab_name}_{rc}_{row_id}"):
                            render_pkg_config_column("Paket Snack", "🥐", snack_options, selected_snack_items, pkg_snack_key, "pkg_snack", default_snack_label, kategori, master_df, raw_suppliers, "Pilih kue/snack...", key_suffix=f"_row_{row_id}")
                            selected_snack_items = st.session_state.get(pkg_snack_key, [])
                            snack_summary = format_pkg_summary(selected_snack_items, "pkg_snack", default_snack_label, kategori, master_dict_by_name)
                    final_supplier = "[Sesuai Paket]"
                elif is_buah_row:
                    with c_sup:
                        with st.popover("Isi Paket", use_container_width=True, key=f"pop_pkg_buah_{tab_name}_{rc}_{row_id}"):
                            render_pkg_config_column("Paket Buah", "🍎", buah_options, selected_buah_items, pkg_buah_key, "pkg_buah", default_buah_label, kategori, master_df, raw_suppliers, "Pilih buah...", key_suffix=f"_row_{row_id}")
                            selected_buah_items = st.session_state.get(pkg_buah_key, [])
                            buah_summary = format_pkg_summary(selected_buah_items, "pkg_buah", default_buah_label, kategori, master_dict_by_name)
                    final_supplier = "[Sesuai Paket]"
                else:
                    item_sups = get_item_suppliers(selected_item, master_df)
                    row_supplier_options = item_sups if item_sups else ["-"]
                    default_supp = item_sups[0] if item_sups else "-"
                        
                    if default_supp == "-":
                        fb_s = resolve_pkg_supplier(selected_item, "-", master_dict_by_name)
                        if fb_s != "-" and fb_s in row_supplier_options:
                            default_supp = fb_s
                        
                    sup_key = f"sup_{tab_name}_{rc}_{row_id}_{selected_item}"
                    chosen_supp = st.session_state.get(sup_key, default_supp)
                    if chosen_supp not in row_supplier_options:
                        chosen_supp = default_supp if default_supp in row_supplier_options else row_supplier_options[0]
                    default_supp_idx = row_supplier_options.index(chosen_supp)
                    
                    with c_sup:
                        sel_supp = st.selectbox(
                            "Supplier", 
                            row_supplier_options, 
                            index=default_supp_idx, 
                            key=sup_key, 
                            label_visibility="collapsed"
                        )
                    final_supplier = sel_supp

                pkg_unconfigured = (is_snack_row and not selected_snack_items) or (is_buah_row and not selected_buah_items)
                with c2:
                    if pkg_unconfigured:
                        qty = st.number_input("Qty", min_value=0.0, max_value=0.0, value=0.0, disabled=True, key=f"qty_{tab_name}_{rc}_{row_id}", label_visibility="collapsed")
                        st.markdown("<div style='color: #dc2626; font-size: 11px; font-weight: 600; line-height: 1.1; margin-top: -6px;'>⚠️ Atur paket dulu</div>", unsafe_allow_html=True)
                    else:
                        qty = st.number_input("Qty", min_value=0.0, max_value=max_qty, value=min(default_qty, max_qty), step=0.05, format="%.2f", key=f"qty_{tab_name}_{rc}_{row_id}", label_visibility="collapsed")
                
                with c_sat:
                    if is_snack_row or is_buah_row:
                        st.markdown("""
                        <div style="background-color: #fee2e2; border: 1px solid #f87171; color: #991b1b; padding: 7px 4px; border-radius: 8px; text-align: center; font-size: 13px; font-weight: 700; height: 38px; display: flex; align-items: center; justify-content: center;">
                            Paket
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.text_input("Satuan", value=satuan, disabled=True, key=f"sat_{tab_name}_{rc}_{row_id}", label_visibility="collapsed")
                    
                with c5:
                    ket = st.text_input("Keterangan", placeholder="(Opsional)", key=f"ket_{tab_name}_{rc}_{row_id}", label_visibility="collapsed")
                
                with c6:
                    st.button("🗑️", key=f"del_{tab_name}_{rc}_{row_id}", on_click=remove_row, args=(row_id,))

                if is_snack_row:
                    st.caption(f"🍱 **Paket:** {snack_summary}" if selected_snack_items else f"ℹ️ *Default: 1x '{default_snack_label}'*")
                elif is_buah_row:
                    st.caption(f"🍎 **Paket:** {buah_summary}" if selected_buah_items else f"ℹ️ *Default: 1x '{default_buah_label}'*")
                
                if (is_snack_row and selected_snack_items) or (is_buah_row and selected_buah_items):
                    error_stok = False
                else:
                    error_stok = (stok_fisik < qty) and not is_unlimited
                    if error_stok:
                        st.error(f"Stok {selected_item} tidak cukup! (Tersisa: {stok_fisik:g})")
                    
                if qty > 0:
                    row_data.append({
                        "nama_barang": selected_item,
                        "supplier": final_supplier,
                        "qty": qty,
                        "harga_master": harga_master,
                        "keterangan": ket.strip(),
                        "stok_fisik": stok_fisik,
                        "is_unlimited": is_unlimited,
                        "is_error": error_stok,
                        "is_snack_row": is_snack_row,
                        "is_buah_row": is_buah_row
                    })
            
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
            
            master_dict_by_name_sup = {}
            master_dict_by_name = {}
            for _, r in master_df.iterrows():
                master_dict_by_name_sup[(r['nama_barang'], r['supplier'])] = r.to_dict()
                if r['nama_barang'] not in master_dict_by_name:
                    master_dict_by_name[r['nama_barang']] = r.to_dict()

            unrolled_rows = []
            for r in row_data:
                if r.get('is_snack_row') and selected_snack_items:
                    for sit in selected_snack_items:
                        q_unit = get_pkg_qty("pkg_snack", kategori, sit, 1.0)
                        s_chosen = resolve_pkg_supplier(sit, get_pkg_sup("pkg_snack", kategori, sit), master_dict_by_name)
                        m_info = master_dict_by_name_sup.get((sit, s_chosen), master_dict_by_name.get(sit, {}))
                        p_item = float(m_info.get('harga_master', 0))
                        stk_item = float(m_info.get('stok_sekarang', 0))
                        is_unl = str(m_info.get('status', 'True')).upper() not in ['TRUE', '1', 'YES', 'T'] or float(m_info.get('stok_minimal', 0)) == 0
                        tot_q = r['qty'] * q_unit
                        ket_str = f"Paket Snack ({r['qty']:g} pkt)"
                        if r['keterangan']:
                            ket_str += f" - {r['keterangan']}"
                        unrolled_rows.append({
                            "nama_barang": sit,
                            "supplier": s_chosen,
                            "qty": tot_q,
                            "harga_master": p_item,
                            "harga_real": p_item,
                            "keterangan": ket_str,
                            "stok_fisik": stk_item,
                            "is_unlimited": is_unl
                        })
                elif r.get('is_buah_row') and selected_buah_items:
                    for bit in selected_buah_items:
                        q_unit = get_pkg_qty("pkg_buah", kategori, bit, 1.0)
                        s_chosen = resolve_pkg_supplier(bit, get_pkg_sup("pkg_buah", kategori, bit), master_dict_by_name)
                        m_info = master_dict_by_name_sup.get((bit, s_chosen), master_dict_by_name.get(bit, {}))
                        p_item = float(m_info.get('harga_master', 0))
                        stk_item = float(m_info.get('stok_sekarang', 0))
                        is_unl = str(m_info.get('status', 'True')).upper() not in ['TRUE', '1', 'YES', 'T'] or float(m_info.get('stok_minimal', 0)) == 0
                        tot_q = r['qty'] * q_unit
                        ket_str = f"Paket Buah ({r['qty']:g} pkt)"
                        if r['keterangan']:
                            ket_str += f" - {r['keterangan']}"
                        unrolled_rows.append({
                            "nama_barang": bit,
                            "supplier": s_chosen,
                            "qty": tot_q,
                            "harga_master": p_item,
                            "harga_real": p_item,
                            "keterangan": ket_str,
                            "stok_fisik": stk_item,
                            "is_unlimited": is_unl
                        })
                elif r.get('is_snack_row') or r.get('is_buah_row'):
                    # Paket belum diatur, abaikan unrolling default
                    continue
                else:
                    row_sup = resolve_pkg_supplier(r['nama_barang'], r['supplier'], master_dict_by_name)
                    unrolled_rows.append({
                        "nama_barang": r['nama_barang'],
                        "supplier": row_sup,
                        "qty": r['qty'],
                        "harga_master": r['harga_master'],
                        "harga_real": r['harga_master'],
                        "keterangan": r['keterangan'] if r['keterangan'] else f"Input {kategori}",
                        "stok_fisik": r['stok_fisik'],
                        "is_unlimited": r.get('is_unlimited', False)
                    })
                    
            stock_needed = {}
            for ur in unrolled_rows:
                key = (ur['nama_barang'], ur['supplier'])
                stock_needed[key] = stock_needed.get(key, 0.0) + ur['qty']
                
            insufficient_stock_errors = []
            for (it_name, sup_name), needed_qty in stock_needed.items():
                if (it_name, sup_name) in master_dict_by_name_sup:
                    m_info = master_dict_by_name_sup[(it_name, sup_name)]
                    stk_fisik = float(m_info.get('stok_sekarang', 0))
                else:
                    m_info = master_dict_by_name.get(it_name, {})
                    matching_m = master_df[master_df['nama_barang'] == it_name]
                    stk_fisik = float(pd.to_numeric(matching_m['stok_sekarang'], errors='coerce').sum()) if not matching_m.empty else float(m_info.get('stok_sekarang', 0))
                is_unl = str(m_info.get('status', 'True')).upper() not in ['TRUE', '1', 'YES', 'T'] or float(m_info.get('stok_minimal', 0)) == 0
                if not is_unl and stk_fisik < needed_qty:
                    supp_str = f" ({sup_name})" if sup_name and sup_name != "-" else ""
                    insufficient_stock_errors.append(f"• **{it_name}**{supp_str} (dibutuhkan: {needed_qty:g}, stok tersisa: {stok_fisik:g})")
                    
            has_error = bool(insufficient_stock_errors) or any(r.get('is_error') for r in row_data)
                    
            if unrolled_rows:
                total_nilai = sum(r['qty'] * r['harga_real'] for r in unrolled_rows)
                total_qty = sum(r['qty'] for r in unrolled_rows)
                if has_pkg_feature and (selected_snack_items or selected_buah_items):
                    st.success(f"Terdapat **{len(unrolled_rows)} item fisik** (Total Qty: {total_qty:g} | Total Nilai: Rp {total_nilai:,.0f}) yang akan dimasukkan ke **{kategori}** (paket telah diurai).")
                else:
                    st.success(f"Terdapat **{len(unrolled_rows)} macam barang** (Total Qty: {total_qty:g} | Total Nilai: Rp {total_nilai:,.0f}) yang akan dimasukkan ke **{kategori}**.")
                if insufficient_stock_errors:
                    st.error("⚠️ **Peringatan Stok Kurang:**<br>" + "<br>".join(insufficient_stock_errors), icon="🚨")
                    
            submit = st.button("✓ Proses & Simpan", type="primary", use_container_width=True, disabled=(not unrolled_rows))
            
            if submit:
                for r in row_data:
                    if r.get('is_snack_row') and not selected_snack_items and r.get('qty', 0) > 0:
                        st.error("❌ Gagal Simpan! Isi paket Snack belum diatur. Silakan atur melalui tombol 'Isi Paket' pada kolom Supplier terlebih dahulu.")
                        return
                    if r.get('is_buah_row') and not selected_buah_items and r.get('qty', 0) > 0:
                        st.error("❌ Gagal Simpan! Isi paket Buah belum diatur. Silakan atur melalui tombol 'Isi Paket' pada kolom Supplier terlebih dahulu.")
                        return
                if has_error:
                    st.error("Silakan perbaiki stok barang yang merah (tidak cukup) terlebih dahulu!")
                    return
                    
                with st.spinner("Memproses transaksi..."):
                    try:
                        trx_df = get_sheet_data(SHEET_PENGELUARAN_DOKTER)
                        new_rows = []
                        master_df_updated = master_df.copy()
                        
                        timestamp = datetime.datetime.combine(tgl_transaksi, datetime.datetime.now().time()).strftime("%Y-%m-%d %H:%M:%S")
                        
                        for r in unrolled_rows:
                            r_name = r['nama_barang']
                            r_sup = r.get('supplier', '-')
                            matching_indices = []
                            if r_sup and r_sup not in ["-", "[Sesuai Paket]"]:
                                matching_indices = master_df_updated.index[
                                    (master_df_updated['nama_barang'].astype(str).str.strip().str.lower() == r_name.strip().lower()) &
                                    (master_df_updated['supplier'].astype(str).str.strip().str.lower() == r_sup.strip().lower())
                                ].tolist()
                            if not matching_indices:
                                matching_indices = master_df_updated.index[master_df_updated['nama_barang'] == r_name].tolist()
                                
                            if matching_indices:
                                idx = matching_indices[0]
                                cur_stk = float(master_df_updated.at[idx, 'stok_sekarang']) if pd.notna(master_df_updated.at[idx, 'stok_sekarang']) else 0.0
                                master_df_updated.at[idx, 'stok_sekarang'] = max(0.0, cur_stk - r['qty'])
                                
                            new_rows.append({
                                "tanggal": timestamp,
                                "shift": shift,
                                "kategori": kategori,
                                "kategori_freetext": freetext_val.strip(),
                                "nama_barang": r['nama_barang'],
                                "supplier": r.get('supplier', '-'),
                                "qty": r['qty'],
                                "harga_master": r['harga_master'],
                                "harga_real": r.get('harga_real', r['harga_master']),
                                "total_harga": r['qty'] * r.get('harga_real', r['harga_master']),
                                "keterangan": r['keterangan'] if r['keterangan'] else f"Input {kategori}"
                            })
                                    
                        save_data(master_df_updated, SHEET_MASTER)
                        trx_df = pd.concat([trx_df, pd.DataFrame(new_rows)], ignore_index=True)
                        save_data(trx_df, SHEET_PENGELUARAN_DOKTER)
                        
                        if state_items_key in st.session_state:
                            del st.session_state[state_items_key]
                        if state_defaults_key in st.session_state:
                            del st.session_state[state_defaults_key]
                        st.session_state[reset_counter_key] += 1
                        
                        st.session_state[toast_key] = f"Berhasil menyimpan {len(unrolled_rows)} item ke {kategori}!"
                        st.rerun()
                    except Exception as e:
                        st.error(f"Gagal menyimpan: {e}")
