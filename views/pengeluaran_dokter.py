import streamlit as st
import datetime
import pandas as pd
from data.sheets_repository import (
    get_sheet_data, save_data, SHEET_MASTER, SHEET_PENGELUARAN_DOKTER, SHEET_MASTER_DOKTER
)
from views.pengeluaran_common import show_toast, multi_select_dialog

@st.dialog("Konfirmasi Penyimpanan Massal 📦")
def confirm_batch_save_dialog(valid_rows_to_save, sheet_name, shift, kategori, master_df, toast_key):
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
                    trx_df = get_sheet_data(sheet_name)
                    new_rows = []
                    master_df_updated = master_df.copy()
                    
                    for r in valid_rows_to_save:
                        idx = master_df_updated.index[master_df_updated['nama_barang'] == r['nama_barang']].tolist()[0]
                        master_df_updated.at[idx, 'stok_sekarang'] = master_df_updated.at[idx, 'stok_sekarang'] - r['qty']
                        
                        new_rows.append({
                            "tanggal": now.strftime("%Y-%m-%d %H:%M:%S"),
                            "shift": shift,
                            "kategori": kategori,
                            "kategori_freetext": r['kategori_freetext'],
                            "nama_barang": r['nama_barang'],
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
    
    c_btn1, c_btn2 = st.columns(2)
    with c_btn1:
        if st.button("☑️ Pilih Semua", use_container_width=True):
            st.session_state[temp_key].update(docs_to_show)
    with c_btn2:
        if st.button("🔲 Kosongkan", use_container_width=True):
            st.session_state[temp_key].clear()
            
    new_dialog_set = set([x for x in st.session_state[temp_key] if x not in docs_to_show])
    
    with st.container(height=350, border=True):
        if not docs_to_show:
            st.info("Tidak ada dokter yang cocok.")
            
        cols = st.columns(2)
        for i, d in enumerate(docs_to_show):
            with cols[i % 2]:
                is_checked = st.checkbox(d, value=(d in st.session_state[temp_key]))
                if is_checked:
                    new_dialog_set.add(d)
                    
    st.session_state[temp_key] = new_dialog_set
    
    if st.button("➕ Terapkan Pilihan", type="primary", use_container_width=True):
        st.session_state[state_doc_key] = list(st.session_state[temp_key])
        del st.session_state[temp_key]
        st.rerun()

def show_pengeluaran_dokter():
    st.title("🩺 Pengeluaran Dokter")
    
    master_df = get_sheet_data(SHEET_MASTER)
    if master_df.empty:
        st.warning("Data Master Barang kosong!")
        return
        
    master_dokter_df = get_sheet_data(SHEET_MASTER_DOKTER)
    item_options = master_df['nama_barang'].tolist()
    
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
                config[vi] = st.column_config.NumberColumn(vi, min_value=0, step=1, default=0)
                
            st.info("💡 **Tips:** Klik sel angka lalu ketik qty. Tekan `Tab` atau `Panah` untuk pindah sel.")
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
            master_dict = master_df.set_index('nama_barang').to_dict('index')
            
            for index, row in edited_df.iterrows():
                nama_dokter = str(row.get('Nama Dokter', '')).strip()
                if not nama_dokter: continue
                    
                for col_item in valid_items:
                    qty = row.get(col_item, 0)
                    if pd.notnull(qty) and qty > 0:
                        try: qty = float(qty)
                        except: continue
                            
                        if col_item in master_dict:
                            harga_master = float(master_dict[col_item].get('harga_master', 0))
                            stok_fisik = float(master_dict[col_item].get('stok_sekarang', 0))
                            is_unlimited = float(master_dict[col_item].get('stok_minimal', 0)) == 0
                            error_stok = (stok_fisik < qty) and not is_unlimited
                            
                            total_real += (qty * harga_master)
                            total_items_qty += qty
                            
                            valid_rows_to_save.append({
                                "nama_barang": col_item,
                                "qty": qty,
                                "harga_master": harga_master,
                                "harga_real": harga_master,
                                "keterangan": "Batch Input",
                                "kategori_freetext": nama_dokter,
                                "stok_fisik": stok_fisik,
                                "is_error": error_stok
                            })

            if valid_rows_to_save:
                col_calc.success(f"**Terdapat {total_items_qty:,.0f} barang untuk {len(set([r['kategori_freetext'] for r in valid_rows_to_save]))} dokter!** | Total Nilai: Rp {total_real:,.0f}")
                if any(r['is_error'] for r in valid_rows_to_save):
                    col_calc.error("⚠️ Peringatan: Ada barang yang stok fisiknya tidak cukup.")
            else:
                col_calc.info("Tabel masih kosong atau semua qty 0.")
                
            with col_sub:
                submit = st.button("✓ Simpan Transaksi", type="primary", use_container_width=True, disabled=(len(valid_rows_to_save) == 0))
                
            if submit:
                if any(r['is_error'] for r in valid_rows_to_save):
                    st.error("Silakan perbaiki stok barang yang merah (tidak cukup) terlebih dahulu!")
                    return
                confirm_batch_save_dialog(valid_rows_to_save, SHEET_PENGELUARAN_DOKTER, shift, kategori, master_df, toast_key)
                
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
                    default_names = ["Buah (Dr Edi)", "Le Minerale 330 ml", "Snack (Dr Edi)", "Pocari", "Buavita", "Bear Brand", "Yakult", "Puding", "Susu Ultra Mini"]
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
                
            def add_row():
                new_id = max(st.session_state[state_items_key]) + 1 if st.session_state[state_items_key] else 0
                st.session_state[state_items_key].append(new_id)
                
            def remove_row(row_id):
                st.session_state[state_items_key].remove(row_id)
                
            def clear_all():
                st.session_state[state_items_key] = [0]
                st.session_state[state_defaults_key] = []
                
            h1, h2, h_sat, h5, h6 = st.columns([3, 1.5, 1.5, 2, 0.5])
            h1.caption("Pilih Barang")
            h2.caption("Qty")
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
                is_unlimited = str(item_data.get('status', 'True')).upper() not in ['TRUE', '1', 'YES', 'T']
                
                default_qty = 5.0 if kategori == "OK Snack" and "Malam" in shift else 1.0
                max_qty = 99999.0 if is_unlimited else max(1.0, float(stok_fisik), default_qty)
                
                with c2:
                    qty = st.number_input("Qty", min_value=0.0, max_value=max_qty, value=default_qty, step=1.0, format="%.2f", key=f"qty_{tab_name}_{rc}_{row_id}", label_visibility="collapsed")
                
                with c_sat:
                    st.text_input("Satuan", value=satuan, disabled=True, key=f"sat_{tab_name}_{rc}_{row_id}", label_visibility="collapsed")
                    
                with c5:
                    ket = st.text_input("Keterangan", placeholder="(Opsional)", key=f"ket_{tab_name}_{rc}_{row_id}", label_visibility="collapsed")
                
                with c6:
                    st.button("🗑️", key=f"del_{tab_name}_{rc}_{row_id}", on_click=remove_row, args=(row_id,))
                
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
            
            has_error = any(r['is_error'] for r in row_data)
                    
            if row_data:
                total_nilai = sum(r['qty'] * r['harga_master'] for r in row_data)
                st.success(f"Terdapat **{len(row_data)} macam barang** (Total: Rp {total_nilai:,.0f}) yang akan dimasukkan ke **{kategori}**.")
                if has_error:
                    st.error("⚠️ Peringatan: Ada barang yang stok fisiknya tidak cukup.")
                    
            submit = st.button("✓ Proses & Simpan", type="primary", use_container_width=True, disabled=(not row_data))
            
            if submit:
                if has_error:
                    st.error("Silakan perbaiki stok barang yang merah terlebih dahulu!")
                    return
                    
                with st.spinner("Memproses transaksi..."):
                    try:
                        trx_df = get_sheet_data(SHEET_PENGELUARAN_DOKTER)
                        new_rows = []
                        master_df_updated = master_df.copy()
                        
                        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        
                        for r in row_data:
                            idx = master_df_updated.index[master_df_updated['nama_barang'] == r['nama_barang']].tolist()[0]
                            master_df_updated.at[idx, 'stok_sekarang'] = master_df_updated.at[idx, 'stok_sekarang'] - r['qty']
                            
                            new_rows.append({
                                "tanggal": timestamp,
                                "shift": shift,
                                "kategori": kategori,
                                "kategori_freetext": freetext_val.strip(),
                                "nama_barang": r['nama_barang'],
                                "qty": r['qty'],
                                "harga_master": r['harga_master'],
                                "harga_real": r['harga_master'],
                                "total_harga": r['qty'] * r['harga_master'],
                                "keterangan": r['keterangan'] if r['keterangan'] else "Input Satuan"
                            })
                                    
                        save_data(master_df_updated, SHEET_MASTER)
                        trx_df = pd.concat([trx_df, pd.DataFrame(new_rows)], ignore_index=True)
                        save_data(trx_df, SHEET_PENGELUARAN_DOKTER)
                        
                        if state_items_key in st.session_state:
                            del st.session_state[state_items_key]
                        if state_defaults_key in st.session_state:
                            del st.session_state[state_defaults_key]
                        st.session_state[reset_counter_key] += 1
                        
                        st.session_state[toast_key] = f"Berhasil menyimpan {len(row_data)} barang ke {kategori}!"
                        st.rerun()
                    except Exception as e:
                        st.error(f"Gagal menyimpan: {e}")
