import streamlit as st
import datetime
import pandas as pd
import time
from data.sheets_repository import (
    get_sheet_data, save_data, SHEET_MASTER, 
    SHEET_PENGELUARAN_PASIEN, SHEET_PENGELUARAN_DOKTER, SHEET_PENGELUARAN_MANAJEMEN
)

def show_toast(message, icon="✅", color="#22c55e"):
    """Tampilkan toast notification di pojok kanan atas seperti alert web."""
    toast_key = f"toast_{hash(message)}"
    st.markdown(f"""
    <style>
    @keyframes slideInRight {{
        from {{ transform: translateX(120%); opacity: 0; }}
        to   {{ transform: translateX(0);    opacity: 1; }}
    }}
    @keyframes fadeOut {{
        0%   {{ opacity: 1; }}
        80%  {{ opacity: 1; }}
        100% {{ opacity: 0; }}
    }}
    .custom-toast {{
        position: fixed;
        top: 70px;
        right: 24px;
        z-index: 9999;
        background: {color};
        color: white;
        padding: 14px 20px;
        border-radius: 10px;
        font-size: 1rem;
        font-weight: 600;
        box-shadow: 0 4px 20px rgba(0,0,0,0.2);
        display: flex;
        align-items: center;
        gap: 10px;
        min-width: 260px;
        max-width: 400px;
        animation: slideInRight 0.4s ease forwards, fadeOut 3s ease 0.5s forwards;
    }}
    </style>
    <div class="custom-toast">
        <span style="font-size:1.3rem">{icon}</span>
        <span>{message}</span>
    </div>
    """, unsafe_allow_html=True)

@st.dialog("Pilih Banyak Barang Sekaligus 🛒")
def multi_select_dialog(master_df, state_items_key, state_defaults_key, current_items=None):
    if current_items is None: current_items = []
    st.markdown("Filter & pilih barang-barang yang ingin ditambahkan ke form:")
    
    if 'kategori' in master_df.columns:
        categories = master_df['kategori'].dropna().unique().tolist()
        categories = [c for c in categories if str(c).strip() != '']
        
        cat_options = [f"Semua ({len(master_df)})"]
        for c in categories:
            count = len(master_df[master_df['kategori'] == c])
            cat_options.append(f"{c} ({count})")
            
        selected_cat = st.pills("KATEGORI:", cat_options, default=cat_options[0])
        
        if selected_cat and not selected_cat.startswith("Semua"):
            real_cat = selected_cat.split(" (")[0]
            filtered_df = master_df[master_df['kategori'] == real_cat]
        else:
            filtered_df = master_df
    else:
        filtered_df = master_df
        
    temp_key = f"temp_set_{state_items_key}"
    if temp_key not in st.session_state:
        st.session_state[temp_key] = set(current_items)
            
    search_q = st.text_input("🔍 Cari Barang:", placeholder="Ketik nama atau kode barang...", label_visibility="collapsed")
    if search_q:
        filtered_df = filtered_df[filtered_df['nama_barang'].str.contains(search_q, case=False, na=False)]
        
    item_options = filtered_df['nama_barang'].tolist()
    
    st.markdown(f"<div style='font-size:0.85rem; color:gray; font-weight:600;'>Ringkasan Terpilih: {len(st.session_state[temp_key])} barang secara keseluruhan</div>", unsafe_allow_html=True)
    
    c_btn1, c_btn2 = st.columns(2)
    with c_btn1:
        if st.button("☑️ Pilih Semua (Filter Saat Ini)", use_container_width=True):
            st.session_state[temp_key].update(item_options)
    with c_btn2:
        if st.button("🔲 Kosongkan Semua", use_container_width=True):
            st.session_state[temp_key].clear()
            
    new_dialog_set = set([x for x in st.session_state[temp_key] if x not in item_options])
    
    with st.container(height=350, border=True):
        if not item_options:
            st.info("Tidak ada barang.")
        else:
            cols = st.columns(3)
            for i, item in enumerate(item_options):
                with cols[i % 3]:
                    is_checked = st.checkbox(item, value=(item in st.session_state[temp_key]))
                    if is_checked:
                        new_dialog_set.add(item)
                        
    st.session_state[temp_key] = new_dialog_set
    
    if st.button("➕ Tambahkan ke Form", type="primary", use_container_width=True):
        selected = list(st.session_state[temp_key])
        del st.session_state[temp_key]
        items_to_add = [x for x in selected if x not in current_items]
        
        if items_to_add:
            if state_items_key not in st.session_state:
                st.session_state[state_items_key] = []
            if state_defaults_key not in st.session_state:
                st.session_state[state_defaults_key] = []
            
            # Align defaults list length with items list length
            while len(st.session_state[state_defaults_key]) < len(st.session_state[state_items_key]):
                st.session_state[state_defaults_key].append(None)
                
            for item in items_to_add:
                if len(st.session_state[state_items_key]) > 0:
                    new_id = max(st.session_state[state_items_key]) + 1
                else:
                    new_id = 0
                st.session_state[state_items_key].append(new_id)
                st.session_state[state_defaults_key].append(item)
            
        if 'dialog_sel_items_set' in st.session_state:
            del st.session_state['dialog_sel_items_set']
        st.rerun()

def render_form(tab_name, sheet_name, categories):
    # Tampilkan toast notifikasi jika ada pesan sukses dari submit sebelumnya
    toast_key = f'toast_msg_{tab_name}'
    if toast_key in st.session_state:
        show_toast(st.session_state.pop(toast_key))
    
    # CSS Customizations for disabled HPP field
    st.markdown("""
        <style>
        /* Menghilangkan efek transparan (opacity) bawaan Streamlit pada widget yang disabled */
        div[data-testid="stTextInput"]:has(input:disabled) {
            opacity: 1 !important;
        }
        div[data-testid="stTextInput"] input:disabled,
        div[data-testid="column"]:nth-child(4) div[data-testid="stNumberInput"] input {
            background-color: #fff9c4 !important; 
            color: #000000 !important; 
            -webkit-text-fill-color: #000000 !important; 
            opacity: 1 !important;
            border: 1px solid #fbc02d !important; 
            font-weight: 900 !important;
        }
        </style>
    """, unsafe_allow_html=True)
    
    st.markdown(f"#### 📝 Multi-Input Pengeluaran {tab_name}")
    
    master_df = get_sheet_data(SHEET_MASTER)
    if master_df.empty:
        st.warning("Data Master Barang kosong!")
        return

    now = datetime.datetime.now()
    
    current_kategori = st.session_state.get(f"kat_{tab_name}", categories[0])
    
    # Hanya menu Dokter yang formnya ter-reset otomatis per kategori karena templatenya berbeda
    if tab_name == "Dokter":
        state_items_key = f"dyn_items_{tab_name}_{current_kategori}"
        state_defaults_key = f"dyn_defaults_{tab_name}_{current_kategori}"
    else:
        state_items_key = f"dyn_items_{tab_name}_v3"
        state_defaults_key = f"dyn_defaults_{tab_name}_v3"
        
    item_options = master_df['nama_barang'].tolist()
    
    # Reset counter digunakan agar widget Streamlit dibuat ulang (nilai kembali ke default) setelah submit
    reset_counter_key = f"reset_ctr_{tab_name}"
    if reset_counter_key not in st.session_state:
        st.session_state[reset_counter_key] = 0
    rc = st.session_state[reset_counter_key]  # shorthand

    if state_items_key not in st.session_state:
        if tab_name in ["Dokter", "Manajemen"]:
            if tab_name == "Dokter":
                if current_kategori == "Dr. Edi":
                    default_names = ["Buah", "Le Mineral 330", "Snack", "Pocari", "Buavita", "Bear Brand", "Yakult", "Puding", "Susu Ultra Mini"]
                else:
                    default_names = ["Roti", "Buah", "Telur", "Snack", "Le Mineral 600", "Kopi KA", "Kopi 3 in 1", "Pocari", "Buavita"]
            elif tab_name == "Manajemen":
                default_names = ["Le Mineral 330", "Snack", "Roti", "Jus", "Cleo", "Buah (Dokter)"]
                
            valid_defaults = []
            
            # Find closest matches in master_df
            for d in default_names:
                match = None
                # Priority 1: Exact match
                for item in item_options:
                    if d.lower().strip() == str(item).lower().strip():
                        match = item
                        break
                
                # Priority 2: Starts with
                if not match:
                    for item in item_options:
                        if str(item).lower().strip().startswith(d.lower().strip()):
                            match = item
                            break
                            
                # Priority 3: Contains substring
                if not match:
                    for item in item_options:
                        if d.lower().strip() in str(item).lower().strip():
                            match = item
                            break
                
                # Priority 4: If it's a specific Kopi but not found, fallback to any Kopi
                if not match and "kopi" in d.lower():
                    for item in item_options:
                        if "kopi" in str(item).lower():
                            # Don't match the same kopi we already added
                            if item not in valid_defaults:
                                match = item
                                break
                
                if match and match not in valid_defaults:
                    valid_defaults.append(match)
                        
            if valid_defaults:
                st.session_state[state_items_key] = list(range(len(valid_defaults)))
                st.session_state[state_defaults_key] = valid_defaults
            else:
                st.session_state[state_items_key] = [0]
                st.session_state[state_defaults_key] = []
        else:
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
            if k.startswith((f"qty_{tab_name}", f"ket_{tab_name}", f"real_{tab_name}", f"item_{tab_name}", f"sat_{tab_name}", f"hpp_{tab_name}", f"free_{tab_name}", f"shift_{tab_name}", f"kat_{tab_name}", f"jml_pasien_{tab_name}")):
                del st.session_state[k]

    with st.container(border=True):
        # 1. HEADER (Shift & Kategori)
        if tab_name == "Pasien":
            c1, c2, c_pasien, c3 = st.columns([1.5, 1, 1, 2])
            with c1:
                shift = st.selectbox(f"Keterangan Waktu \*", ["Pagi (07:00-15:00)", "Siang (15:00-22:00)", "Malam (22:00-07:00)", "1 Hari"], key=f"shift_{tab_name}")
            with c2:
                kategori = st.selectbox(f"Kategori {tab_name} \*", categories, key=f"kat_{tab_name}")
            with c_pasien:
                jumlah_pasien = st.number_input(f"Jumlah Pasien \*", min_value=1, value=1, step=1, key=f"jml_pasien_{tab_name}")
            with c3:
                freetext_val = st.text_input(f"Identitas / Keterangan (Nama/Ruangan) \*", key=f"free_{tab_name}")
        else:
            c1, c2, c3 = st.columns([1, 1.5, 2])
            with c1:
                shift = st.selectbox(f"Keterangan Waktu \*", ["Pagi (07:00-15:00)", "Siang (15:00-22:00)", "Malam (22:00-07:00)", "1 Hari"], key=f"shift_{tab_name}")
            with c2:
                kategori = st.selectbox(f"Kategori {tab_name} \*", categories, key=f"kat_{tab_name}")
            with c3:
                freetext_val = st.text_input(f"Identitas / Keterangan (Nama/Ruangan) \*", key=f"free_{tab_name}")
                jumlah_pasien = None  # Not used for non-Pasien
                
        st.divider()

        # 2. DYNAMIC ITEM ROWS
        
        # Header for the dynamic rows (compact)
        if tab_name == "Pasien":
            h1, h2, h_sat, h5, h6 = st.columns([3, 1.5, 1.5, 2, 0.5])
            h1.caption("Pilih Barang")
            h2.caption("Qty")
            h_sat.caption("Satuan")
            h5.caption("Keterangan")
            h6.caption("")
        else:
            h1, h2, h3, h4, h5, h6 = st.columns([2.5, 1.5, 1.5, 1.5, 2, 0.5])
            h1.caption("Pilih Barang")
            h2.caption("Qty")
            h3.caption("HPP Master")
            h4.caption("Harga Real")
            h5.caption("Keterangan")
            h6.caption("")
        
        # To store data for validation & submission
        row_data = []
        
        for i, row_id in enumerate(st.session_state[state_items_key]):
            
            # Determine default index if this is a pre-filled row
            default_idx = 0
            if state_defaults_key in st.session_state and i < len(st.session_state[state_defaults_key]):
                def_val = st.session_state[state_defaults_key][i]
                if def_val in item_options:
                    default_idx = item_options.index(def_val)
                    
            if tab_name == "Pasien":
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
                    qty = st.number_input("Qty", min_value=0.0, max_value=max_qty, value=0.0 if tab_name in ["Dokter", "Manajemen"] else 1.0, step=1.0, format="%.2f", key=f"qty_{tab_name}_{rc}_{row_id}", label_visibility="collapsed")
                
                with c_sat:
                    st.text_input("Satuan", value=satuan, disabled=True, key=f"sat_{tab_name}_{rc}_{row_id}_{selected_item}", label_visibility="collapsed")
                
                harga_real = harga_master
                
                with c5:
                    keterangan = st.text_input("Ket", placeholder="Catatan...", key=f"ket_{tab_name}_{rc}_{row_id}", label_visibility="collapsed")
                    
                with c6:
                    st.button("🗑️", key=f"del_{tab_name}_{rc}_{row_id}", on_click=remove_row, args=(row_id,))
            
            else:
                # Untuk Dokter: key menyertakan current_kategori agar widget dibuat ulang saat kategori berubah
                cat_key = current_kategori if tab_name == "Dokter" else ""
                c1, c2, c3, c4, c5, c6 = st.columns([2.5, 1.5, 1.5, 1.5, 2, 0.5])
                with c1:
                    selected_item = st.selectbox("Barang", item_options, index=default_idx, key=f"item_{tab_name}_{cat_key}_{rc}_{row_id}", label_visibility="collapsed")
                
                item_data = master_df[master_df['nama_barang'] == selected_item].iloc[0]
                stok_fisik = float(item_data.get('stok_sekarang', 0))
                harga_master = float(item_data.get('harga_master', 0))
                is_unlimited = float(item_data.get('stok_minimal', 0)) == 0
                max_qty = 99999.0 if is_unlimited else max(1.0, float(stok_fisik))
                
                with c2:
                    qty = st.number_input("Qty", min_value=0.0, max_value=max_qty, value=0.0, step=1.0, format="%.2f", key=f"qty_{tab_name}_{cat_key}_{rc}_{row_id}", label_visibility="collapsed")
                
                with c3:
                    st.text_input("HPP", value=f"Rp {harga_master:,.0f}", disabled=True, key=f"hpp_{tab_name}_{cat_key}_{rc}_{row_id}_{selected_item}", label_visibility="collapsed")
                    
                with c4:
                    harga_real = st.number_input("Harga Real", min_value=0.0, value=harga_master, step=100.0, key=f"real_{tab_name}_{cat_key}_{rc}_{row_id}_{selected_item}", label_visibility="collapsed")
                    
                with c5:
                    keterangan = st.text_input("Ket", placeholder="Catatan...", key=f"ket_{tab_name}_{cat_key}_{rc}_{row_id}", label_visibility="collapsed")
                    
                with c6:
                    st.button("🗑️", key=f"del_{tab_name}_{cat_key}_{rc}_{row_id}", on_click=remove_row, args=(row_id,))
                
            # Validations
            error_stok = (stok_fisik < qty) and not is_unlimited
            if error_stok:
                st.error(f"Stok {selected_item} tidak cukup! (Tersisa: {stok_fisik})")
                
            # Only save rows where qty > 0 so that pre-filled 0 qty items are ignored
            if qty > 0:
                row_data.append({
                    "nama_barang": selected_item,
                    "qty": qty,
                    "harga_master": harga_master,
                    "harga_real": harga_real,
                    "keterangan": keterangan,
                    "stok_fisik": stok_fisik,
                    "is_error": error_stok
                })
            
        # Add Item Button
        btn_col1, btn_col2, btn_col3, _ = st.columns([1.5, 1.5, 1.5, 0.5])
        with btn_col1:
            st.button("➕ Tambah 1 Baris Kosong", on_click=add_row, key=f"add_{tab_name}", use_container_width=True)
        with btn_col2:
            if st.button("🔍 Pilih Banyak Barang Sekaligus", key=f"multi_add_{tab_name}", use_container_width=True):
                current_items_in_form = []
                for idx, r_id in enumerate(st.session_state[state_items_key]):
                    item_val = st.session_state.get(f"item_{tab_name}_{current_kategori}_{r_id}")
                    if not item_val and idx < len(st.session_state[state_defaults_key]):
                        item_val = st.session_state[state_defaults_key][idx]
                    if item_val:
                        current_items_in_form.append(item_val)
                multi_select_dialog(master_df, state_items_key, state_defaults_key, current_items_in_form)
        with btn_col3:
            st.button("🗑️ Bersihkan Semua", on_click=clear_all, key=f"clear_all_{tab_name}", use_container_width=True)
        
        st.divider()
        
        # 3. SUBMIT
        total_real = sum(r['qty'] * r['harga_real'] for r in row_data)
        
        col_calc, col_sub = st.columns([3, 1])
        
        if tab_name == "Pasien":
            col_calc.info(f"**Total Nilai Pengeluaran:** Rp {total_real:,.0f}")
        else:
            total_hpp = sum(r['qty'] * r['harga_master'] for r in row_data)
            total_selisih = total_real - total_hpp
            margin_pct = (total_selisih / total_hpp * 100) if total_hpp > 0 else 0
            
            if total_selisih > 0:
                margin_text = f"🟩 Margin Profit: +Rp {total_selisih:,.0f} (+{margin_pct:.1f}%)"
            elif total_selisih < 0:
                margin_text = f"🟥 Margin Minus: -Rp {abs(total_selisih):,.0f} ({margin_pct:.1f}%)"
            else:
                margin_text = "⬜ Margin: Rp 0"
                
            col_calc.info(f"**Total Real Transaksi:** Rp {total_real:,.0f} &nbsp;&nbsp;|&nbsp;&nbsp; **Total HPP:** Rp {total_hpp:,.0f} &nbsp;&nbsp;|&nbsp;&nbsp; **{margin_text}**")
        
        with col_sub:
            submit = st.button(f"✓ Simpan Transaksi", type="primary", use_container_width=True, key=f"btn_simpan_{tab_name}")
            
        if submit:
            if not freetext_val:
                st.error("Identitas / Keterangan wajib diisi!")
                return
            if len(row_data) == 0:
                st.error("Pilih minimal 1 barang!")
                return
            if any(r['is_error'] for r in row_data):
                st.error("Ada barang yang stoknya tidak mencukupi. Silakan perbaiki terlebih dahulu!")
                return

            with st.spinner("Menyimpan semua transaksi..."):
                try:
                    trx_df = get_sheet_data(sheet_name)
                    new_rows = []
                    
                    # Update master df logic
                    master_df_updated = master_df.copy()
                    
                    for r in row_data:
                        # 1. Update stok in copy
                        idx = master_df_updated.index[master_df_updated['nama_barang'] == r['nama_barang']].tolist()[0]
                        stok_baru = master_df_updated.at[idx, 'stok_sekarang'] - r['qty']
                        master_df_updated.at[idx, 'stok_sekarang'] = stok_baru
                        
                        row_dict = {
                            "tanggal": now.strftime("%Y-%m-%d %H:%M:%S"),
                            "shift": shift,
                            "kategori": kategori,
                            "kategori_freetext": freetext_val,
                            "nama_barang": r['nama_barang'],
                            "qty": r['qty'],
                            "harga_master": r['harga_master'],
                            "harga_real": r['harga_real'],
                            "total_harga": r['qty'] * r['harga_real'],
                            "keterangan": r['keterangan']
                        }
                        
                        if tab_name == "Pasien":
                            row_dict["jumlah_pasien"] = jumlah_pasien
                            
                        new_rows.append(row_dict)
                    
                    # Save Master Data
                    save_data(master_df_updated, SHEET_MASTER)

                    # Save to Pengeluaran
                    trx_df = pd.concat([trx_df, pd.DataFrame(new_rows)], ignore_index=True)
                    save_data(trx_df, sheet_name)
                    
                    st.session_state[f'toast_msg_{tab_name}'] = f"{len(row_data)} item berhasil disimpan!"
                    
                    if tab_name == "Dokter":
                        # Dokter: pertahankan template barang (daftar barang tetap ada),
                        # tapi reset qty & keterangan dengan cara naikkan counter → semua widget key berubah → default value berlaku
                        st.session_state[reset_counter_key] += 1
                        # Juga reset header (shift & identitas)
                        for k in list(st.session_state.keys()):
                            if k.startswith((f"free_{tab_name}", f"shift_{tab_name}")):
                                del st.session_state[k]
                    else:
                        # Pasien & Manajemen: reset total
                        if state_items_key in st.session_state:
                            del st.session_state[state_items_key]
                        if state_defaults_key in st.session_state:
                            del st.session_state[state_defaults_key]
                        st.session_state[reset_counter_key] += 1
                        for k in list(st.session_state.keys()):
                            if k.startswith((f"free_{tab_name}", f"shift_{tab_name}", f"kat_{tab_name}", f"jml_pasien_{tab_name}")):
                                del st.session_state[k]
                            
                    st.rerun()
                except Exception as e:
                    st.error(f"Gagal menyimpan: {e}")

    # Daftar rekapan dipindahkan ke halaman Laporan Harian sesuai permintaan
