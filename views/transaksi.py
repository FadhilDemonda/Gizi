import streamlit as st
import datetime
import pandas as pd
import time
from data.sheets_repository import get_sheet_data, save_data, SHEET_MASTER, SHEET_STOK_MASUK

def show_toast(message, icon="✅", color="#22c55e"):
    """Tampilkan toast notification di pojok kanan atas seperti alert web."""
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
        
    if 'dialog_sel_items_set' not in st.session_state:
        st.session_state['dialog_sel_items_set'] = set(current_items)
        
    def toggle_item(item_name):
        if st.session_state.get(f"chk_dlg_trans_{item_name}"):
            st.session_state['dialog_sel_items_set'].add(item_name)
        else:
            st.session_state['dialog_sel_items_set'].discard(item_name)
            
    search_q = st.text_input("🔍 Cari Barang:", placeholder="Ketik nama atau kode barang...", label_visibility="collapsed")
    if search_q:
        filtered_df = filtered_df[filtered_df['nama_barang'].str.contains(search_q, case=False, na=False, regex=False)]
        
    item_options = filtered_df['nama_barang'].tolist()
    
    st.markdown(f"<div style='font-size:0.85rem; color:gray; font-weight:600;'>Ringkasan Terpilih: {len(st.session_state['dialog_sel_items_set'])} barang</div>", unsafe_allow_html=True)
    
    with st.container(height=350, border=True):
        if not item_options:
            st.info("Tidak ada barang.")
        else:
            cols = st.columns(3)
            for i, item in enumerate(item_options):
                with cols[i % 3]:
                    st.checkbox(
                        item, 
                        value=(item in st.session_state['dialog_sel_items_set']),
                        key=f"chk_dlg_trans_{item}",
                        on_change=toggle_item,
                        args=(item,)
                    )
    
    if st.button("➕ Tambahkan ke Form", type="primary", use_container_width=True):
        selected = list(st.session_state.get('dialog_sel_items_set', []))
        items_to_add = [x for x in selected if x not in current_items]
        
        if items_to_add:
            if state_items_key not in st.session_state:
                st.session_state[state_items_key] = []
            if state_defaults_key not in st.session_state:
                st.session_state[state_defaults_key] = []
            
            # Jika form hanya punya 1 baris awal dan baris tsb belum memilih barang, gunakan baris pertama itu
            if len(st.session_state[state_items_key]) == 1:
                first_id = st.session_state[state_items_key][0]
                first_val = st.session_state.get(f"item_masuk_{first_id}")
                if not first_val and (not st.session_state[state_defaults_key] or not st.session_state[state_defaults_key][0]):
                    st.session_state[state_defaults_key] = [items_to_add[0]]
                    items_to_add = items_to_add[1:]

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

def show_transaksi():
    # Tampilkan toast notifikasi jika ada pesan sukses dari submit sebelumnya
    if 'toast_msg_masuk' in st.session_state:
        show_toast(st.session_state.pop('toast_msg_masuk'))
    
    # CSS Customizations for disabled HPP field and Harga Real field
    st.markdown("""
        <style>
        /* Menghilangkan efek transparan (opacity) bawaan Streamlit pada widget yang disabled */
        div[data-testid="stTextInput"]:has(input:disabled) {
            opacity: 1 !important;
        }
        div[data-testid="stTextInput"] input:disabled,
        div[data-testid="column"]:nth-child(4) div[data-testid="stNumberInput"] input {
            background-color: #fff9c4 !important; /* Kuning pastel */
            color: #000000 !important; /* Teks hitam */
            -webkit-text-fill-color: #000000 !important; /* Wajib untuk override Dark Mode */
            opacity: 1 !important;
            border: 1px solid #fbc02d !important; 
            font-weight: 900 !important;
        }
        </style>
    """, unsafe_allow_html=True)
    
    col_title, col_date = st.columns([2.8, 1.4])
    with col_title:
        st.title("📥 Input Stok Masuk (Belanja)")
    with col_date:
        st.markdown('<span class="timestamp-blue-marker"></span>', unsafe_allow_html=True)
        tgl_transaksi = st.date_input("📅 Tanggal Transaksi", value=datetime.date.today(), key="tgl_trx_masuk")
    
    toast_key = 'toast_msg_masuk'
    if toast_key in st.session_state:
        show_toast(st.session_state.pop(toast_key))
        
    master_df = get_sheet_data(SHEET_MASTER)
    if master_df.empty:
        st.warning("Data Master Barang kosong!")
        return

    now = datetime.datetime.now()
    
    # Init dynamic rows state
    state_items_key = "dyn_items_masuk"
    state_defaults_key = "dyn_defaults_masuk"
    if state_items_key not in st.session_state:
        # Array of unique IDs for the rows
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
            if k.startswith(("qty_masuk", "ket_masuk", "real_masuk", "item_masuk", "hpp_masuk", "shift_masuk", "petugas_masuk", "supplier_masuk", "free_masuk")):
                del st.session_state[k]

    with st.container(border=True):
        # 1. HEADER
        c1, c2, c3, c4 = st.columns([1, 1, 1, 1.5])
        with c1:
            shift = st.selectbox("Keterangan Waktu \*", ["Pagi (07:00-11:00)", "Siang (12:00-15:00)", "Sore (16:00-20:00)"], key="shift_masuk")
        with c2:
            petugas = st.text_input("Nama Petugas \*", key="petugas_masuk")
        with c3:
            supplier_list = ["Pak Urip", "Wahana", "Ari Snack", "Supplier Yulia", "Roti Mayestik", "Kasir", "Lainnya"]
            supplier_opt = st.selectbox("Nama Supplier \*", supplier_list, key="supplier_masuk_opt")
            if supplier_opt == "Lainnya":
                supplier = st.text_input("Ketik Nama Supplier \*", key="supplier_masuk")
            else:
                supplier = supplier_opt
        with c4:
            freetext_val = st.text_input("Nota / Keterangan Pembelian \*", placeholder="Contoh: INV-8921...", key="free_masuk")

        st.divider()

        # 2. DYNAMIC ITEM ROWS
        item_options = master_df['nama_barang'].tolist()
        
        # Header for the dynamic rows (compact)
        h1, h2, h3, h4, h5, h6, h7 = st.columns([2.3, 1.0, 1.3, 1.3, 1.6, 1.2, 0.4])
        h1.caption("Pilih Barang")
        h2.caption("Qty Masuk")
        h3.caption("HPP Master")
        h4.caption("Harga Beli Real")
        h5.caption("Status Perubahan Harga")
        h6.caption("Sisa Stok")
        h7.caption("")
        
        # To store data for validation & submission
        row_data = []

        for i, row_id in enumerate(st.session_state[state_items_key]):
            c1, c2, c3, c4, c5, c6, c7 = st.columns([2.3, 1.0, 1.3, 1.3, 1.6, 1.2, 0.4])
            
            default_idx = None
            if state_defaults_key in st.session_state and i < len(st.session_state[state_defaults_key]):
                def_val = st.session_state[state_defaults_key][i]
                if def_val in item_options:
                    default_idx = item_options.index(def_val)
                    
            with c1:
                selected_item = st.selectbox(
                    "Barang", 
                    item_options, 
                    index=default_idx, 
                    placeholder="-- Pilih Barang --", 
                    key=f"item_masuk_{row_id}", 
                    label_visibility="collapsed"
                )
            
            # Jika belum memilih barang (baris baru kosong)
            if not selected_item:
                with c2:
                    st.number_input("Qty", min_value=0.0, value=0.0, disabled=True, key=f"qty_masuk_dis_{row_id}", label_visibility="collapsed")
                with c3:
                    st.text_input("HPP", value="-", disabled=True, key=f"hpp_masuk_dis_{row_id}", label_visibility="collapsed")
                with c4:
                    st.number_input("Harga Beli", value=0, disabled=True, key=f"real_masuk_dis_{row_id}", label_visibility="collapsed")
                with c5:
                    st.markdown("<div style='background-color: #f3f4f6; border: 1px dashed #d1d5db; color: #9ca3af; padding: 7px 10px; border-radius: 8px; text-align: center; font-size: 13px; font-weight: 500; display: flex; align-items: center; justify-content: center; height: 38px;'>-</div>", unsafe_allow_html=True)
                with c6:
                    st.info("-")
                with c7:
                    st.button("🗑️", key=f"del_masuk_{row_id}", on_click=remove_row, args=(row_id,))
                continue

            # Get item data
            item_data = master_df[master_df['nama_barang'] == selected_item].iloc[0]
            stok_fisik = float(item_data.get('stok_sekarang', 0))
            satuan = str(item_data.get('satuan', '')).strip()
            kategori = item_data.get('kategori', '')
            harga_master = float(item_data.get('harga_master', 0))
            
            with c2:
                qty = st.number_input("Qty", min_value=0.0, value=1.0, step=1.0, format="%.2f", key=f"qty_masuk_{row_id}", label_visibility="collapsed")
                st.markdown(f"<div style='font-size: 11px; color: gray; text-align: left; margin-top: -10px; margin-bottom: 5px; padding-left: 2px;'>{satuan}</div>", unsafe_allow_html=True)
            
            with c3:
                st.text_input("HPP", value=f"Rp {harga_master:,.0f}", disabled=True, key=f"hpp_masuk_{row_id}_{selected_item}", label_visibility="collapsed")
                
            with c4:
                harga_real = st.number_input("Harga Beli", min_value=0, value=int(harga_master), step=100, format="%d", key=f"real_masuk_{row_id}_{selected_item}", label_visibility="collapsed")
                st.markdown(f"<div style='font-size: 11px; color: gray; text-align: left; margin-top: -10px; margin-bottom: 5px; padding-left: 2px;'>Rp {harga_real:,.0f}</div>", unsafe_allow_html=True)
                
            with c5:
                # Notifikasi instan harga naik / turun / sama (di sebelah kiri sisa stok)
                selisih_harga = harga_real - harga_master
                if selisih_harga > 0:
                    st.markdown(f"""
                        <div style="background-color: #fee2e2; border: 1px solid #f87171; color: #991b1b; padding: 7px 10px; border-radius: 8px; text-align: center; font-size: 13px; font-weight: 700; display: flex; align-items: center; justify-content: center; height: 38px;" title="Harga naik +Rp {selisih_harga:,.0f} dari HPP">
                            🔺 Naik
                        </div>
                    """, unsafe_allow_html=True)
                elif selisih_harga < 0:
                    selisih_abs = abs(selisih_harga)
                    st.markdown(f"""
                        <div style="background-color: #dcfce7; border: 1px solid #4ade80; color: #166534; padding: 7px 10px; border-radius: 8px; text-align: center; font-size: 13px; font-weight: 700; display: flex; align-items: center; justify-content: center; height: 38px;" title="Harga turun -Rp {selisih_abs:,.0f} dari HPP">
                            🔻 Turun
                        </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                        <div style="background-color: #f3f4f6; border: 1px solid #d1d5db; color: #4b5563; padding: 7px 10px; border-radius: 8px; text-align: center; font-size: 13px; font-weight: 700; display: flex; align-items: center; justify-content: center; height: 38px;" title="Harga sama sesuai HPP Master">
                            ⚖️ Sama
                        </div>
                    """, unsafe_allow_html=True)

            with c6:
                # Show current stock
                st.info(f"{stok_fisik} {satuan}")
                
            with c7:
                # Trash button
                st.button("🗑️", key=f"del_masuk_{row_id}", on_click=remove_row, args=(row_id,))
                
            row_data.append({
                "nama_barang": selected_item,
                "qty": qty,
                "harga_master": harga_master,
                "harga_real": harga_real,
                "stok_fisik": stok_fisik
            })
            
        # Add Item Button
        btn_col1, btn_col2, btn_col3, _ = st.columns([1.5, 1.5, 1.5, 0.5])
        with btn_col1:
            st.button("➕ Tambah 1 Baris Kosong", on_click=add_row, key="add_masuk", use_container_width=True)
        with btn_col2:
            if st.button("🔍 Pilih Banyak Barang Sekaligus", key="multi_add_masuk", use_container_width=True):
                current_items_in_form = []
                for idx, r_id in enumerate(st.session_state[state_items_key]):
                    item_val = st.session_state.get(f"item_masuk_{r_id}")
                    if not item_val and idx < len(st.session_state[state_defaults_key]):
                        item_val = st.session_state[state_defaults_key][idx]
                    if item_val:
                        current_items_in_form.append(item_val)
                multi_select_dialog(master_df, state_items_key, state_defaults_key, current_items_in_form)
        with btn_col3:
            st.markdown('<span class="btn-clear-target"></span>', unsafe_allow_html=True)
            st.button("🗑️ Bersihkan Semua", on_click=clear_all, key="clear_all_masuk", use_container_width=True)
        
        st.divider()
        
        # 3. SUBMIT
        total_real = sum(r['qty'] * r['harga_real'] for r in row_data)
        total_hpp = sum(r['qty'] * r['harga_master'] for r in row_data)
        total_selisih = total_real - total_hpp
        
        # Variance badge for Stok Masuk: If real > HPP = Rugi/Lebih Mahal (Negative). If real < HPP = Hemat (Positive).
        margin_pct = (abs(total_selisih) / total_hpp * 100) if total_hpp > 0 else 0
        
        col_calc, col_sub = st.columns([3, 1])
        
        if total_selisih < 0:
            # We spent less than HPP -> Good (Hemat)
            margin_text = f"🟩 Hemat: +Rp {abs(total_selisih):,.0f} (+{margin_pct:.1f}%)"
        elif total_selisih > 0:
            # We spent more than HPP -> Bad (Overbudget)
            margin_text = f"🟥 Overbudget/Rugi: -Rp {total_selisih:,.0f} ({margin_pct:.1f}%)"
        else:
            margin_text = "⬜ Sesuai HPP"
            
        col_calc.info(f"**Total Modal Dikeluarkan:** Rp {total_real:,.0f} &nbsp;&nbsp;|&nbsp;&nbsp; **Total Nilai HPP:** Rp {total_hpp:,.0f} &nbsp;&nbsp;|&nbsp;&nbsp; **{margin_text}**")
        
        with col_sub:
            submit = st.button(f"✓ Simpan Stok Masuk", type="primary", use_container_width=True, key="btn_simpan_masuk")
            
        if submit:
            if not str(petugas).strip():
                st.error("Nama Petugas wajib diisi!")
                return
            elif not str(supplier).strip():
                st.error("Nama Supplier wajib diisi!")
                return
            elif not str(freetext_val).strip():
                st.error("Nota / Keterangan Pembelian wajib diisi!")
                return
            if len(row_data) == 0:
                st.error("Pilih minimal 1 barang!")
                return
            if any(r['qty'] <= 0 for r in row_data):
                st.error("Qty untuk setiap barang harus lebih besar dari 0!")
                return

            with st.spinner("Menyimpan stok masuk..."):
                try:
                    from data.sheets_repository import SHEET_LOG
                    trx_masuk_df = get_sheet_data(SHEET_STOK_MASUK)
                    crud_log_df = get_sheet_data(SHEET_LOG)
                    
                    new_masuk_rows = []
                    new_crud_logs = []
                    
                    # Update master df logic
                    master_df_updated = master_df.copy()
                    
                    timestamp = datetime.datetime.combine(tgl_transaksi, now.time()).strftime("%Y-%m-%d %H:%M:%S")
                    
                    for r in row_data:
                        idx_list = master_df_updated.index[master_df_updated['nama_barang'] == r['nama_barang']].tolist()
                        if idx_list:
                            idx = idx_list[0]
                            # HPP Master TETAP (tidak berubah dari harga realnya)
                            # Hanya tambahkan stok fisik
                            stok_baru = master_df_updated.at[idx, 'stok_sekarang'] + r['qty']
                            master_df_updated.at[idx, 'stok_sekarang'] = stok_baru
                        
                        # 1. Log Stok Masuk (riwayat transaksi mencatat harga_master dan harga_real riil)
                        new_masuk_rows.append({
                            "tanggal": timestamp,
                            "shift": shift,
                            "kategori": "Penerimaan Barang",
                            "petugas": petugas,
                            "supplier": supplier, 
                            "nama_barang": r['nama_barang'],
                            "qty": r['qty'],
                            "harga_master": r['harga_master'],
                            "harga_real": r['harga_real'],
                            "total_harga": r['qty'] * r['harga_real'],
                            "keterangan": freetext_val
                        })
                    
                    # Save Master Data
                    save_data(master_df_updated, SHEET_MASTER)

                    # Save to Stok Masuk
                    trx_masuk_df = pd.concat([trx_masuk_df, pd.DataFrame(new_masuk_rows)], ignore_index=True)
                    save_data(trx_masuk_df, SHEET_STOK_MASUK)
                    
                    # Save HPP Logs if any
                    if new_crud_logs:
                        crud_log_df = pd.concat([crud_log_df, pd.DataFrame(new_crud_logs)], ignore_index=True)
                        save_data(crud_log_df, SHEET_LOG)
                    
                    st.session_state['toast_msg_masuk'] = f"{len(row_data)} item berhasil ditambahkan ke stok!"
                    
                    # Reset dynamic rows
                    if state_items_key in st.session_state:
                        del st.session_state[state_items_key]
                    if state_defaults_key in st.session_state:
                        del st.session_state[state_defaults_key]
                        
                    # Reset widget values so they revert to default 0/empty
                    for k in list(st.session_state.keys()):
                        if k.startswith(("qty_masuk", "ket_masuk", "real_masuk", "item_masuk", "hpp_masuk", "shift_masuk", "petugas_masuk", "supplier_masuk", "free_masuk")):
                            del st.session_state[k]
                            
                    st.rerun()
                except Exception as e:
                    st.error(f"Gagal menyimpan: {e}")
