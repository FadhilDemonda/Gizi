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

def extract_unique_suppliers(df):
    """Ambil daftar unik supplier dari master_df (bisa dipisah titik koma ';')."""
    suppliers = set()
    if 'supplier' in df.columns:
        for val in df['supplier'].dropna():
            for s in str(val).split(';'):
                clean_s = s.strip()
                if clean_s:
                    suppliers.add(clean_s)
    sorted_suppliers = sorted(list(suppliers), key=lambda x: x.lower())
    # Prioritaskan Pak Urip dan Wahana di atas jika ada
    top_picks = [p for p in ["Pak Urip", "Wahana"] if p in sorted_suppliers]
    other_picks = [p for p in sorted_suppliers if p not in top_picks and p not in ["Kasir", "Lainnya"]]
    if not top_picks and not other_picks:
        top_picks = ["Pak Urip", "Wahana", "Ari Snack", "Bu Yunia", "Roti Mayestik"]
    return top_picks + other_picks

def match_supplier(val, target):
    """Cek apakah val (string supplier barang) mengandung target supplier (case-insensitive, dipisah ';')."""
    if not val or pd.isna(val) or not target:
        return False
    target_clean = str(target).strip().lower()
    val_parts = [s.strip().lower() for s in str(val).split(';')]
    return target_clean in val_parts

@st.dialog("Pilih Banyak Barang Sekaligus 🛒")
def multi_select_dialog(master_df, state_items_key, state_defaults_key, current_items=None, default_supplier=None):
    if current_items is None: current_items = []
    st.markdown("Filter & pilih barang-barang yang ingin ditambahkan ke form:")
    
    # 1. Filter Supplier
    supp_list = extract_unique_suppliers(master_df)
    supp_options = ["Semua Supplier"] + supp_list
    
    default_supp_idx = 0
    if default_supplier and default_supplier in supp_list:
        default_supp_idx = supp_options.index(default_supplier)
        
    c_f1, c_f2 = st.columns([1.3, 1.7])
    with c_f1:
        selected_supplier = st.selectbox(
            "🏢 Filter Supplier:",
            supp_options,
            index=default_supp_idx,
            key="dlg_supp_filter"
        )
    with c_f2:
        search_q = st.text_input("🔍 Cari Barang:", placeholder="Ketik nama atau kode barang...", key="dlg_search_input")

    # Filter berdasarkan Supplier
    if selected_supplier and selected_supplier != "Semua Supplier" and 'supplier' in master_df.columns:
        supplier_df = master_df[master_df['supplier'].apply(lambda x: match_supplier(x, selected_supplier))]
    else:
        supplier_df = master_df

    # 2. Filter Kategori (Bahan Basah, Bahan Kering, Alat tetap dipertahankan)
    if 'kategori' in master_df.columns:
        categories = master_df['kategori'].dropna().unique().tolist()
        categories = [c for c in categories if str(c).strip() != '']
        
        cat_options = [f"Semua ({supplier_df['nama_barang'].nunique() if 'nama_barang' in supplier_df.columns else len(supplier_df)})"]
        for c in categories:
            matching_cat_df = supplier_df[supplier_df['kategori'] == c]
            count = matching_cat_df['nama_barang'].nunique() if 'nama_barang' in matching_cat_df.columns else len(matching_cat_df)
            cat_options.append(f"{c} ({count})")
            
        selected_cat = st.pills("KATEGORI:", cat_options, default=cat_options[0], key=f"dlg_cat_pills_{selected_supplier}")
        
        if selected_cat and not selected_cat.startswith("Semua"):
            real_cat = selected_cat.split(" (")[0]
            filtered_df = supplier_df[supplier_df['kategori'] == real_cat]
        else:
            filtered_df = supplier_df
    else:
        filtered_df = supplier_df
        
    # 3. Filter Pencarian Nama Barang
    if search_q:
        filtered_df = filtered_df[filtered_df['nama_barang'].str.contains(search_q, case=False, na=False, regex=False)]
        
    item_options = [x for x in filtered_df['nama_barang'].dropna().unique().tolist() if str(x).strip()]
    
    if 'dialog_sel_items_set' not in st.session_state:
        st.session_state['dialog_sel_items_set'] = set(current_items)
        
    def toggle_item(item_name):
        if st.session_state.get(f"chk_dlg_trans_{item_name}"):
            st.session_state['dialog_sel_items_set'].add(item_name)
        else:
            st.session_state['dialog_sel_items_set'].discard(item_name)
            
    c_info, c_sel_all, c_desel = st.columns([1.8, 1.1, 1.1])
    with c_info:
        st.markdown(f"<div style='font-size:0.85rem; color:#4b5563; font-weight:600; padding-top:6px;'>Ringkasan Terpilih: {len(st.session_state['dialog_sel_items_set'])} barang</div>", unsafe_allow_html=True)
    with c_sel_all:
        if st.button("☑️ Pilih Semua", key="btn_dlg_sel_all", use_container_width=True):
            for it in item_options:
                st.session_state['dialog_sel_items_set'].add(it)
                st.session_state[f"chk_dlg_trans_{it}"] = True
            st.rerun()
    with c_desel:
        if st.button("⬜ Reset Pilihan", key="btn_dlg_desel", use_container_width=True):
            for it in list(st.session_state['dialog_sel_items_set']):
                st.session_state[f"chk_dlg_trans_{it}"] = False
            st.session_state['dialog_sel_items_set'].clear()
            st.rerun()
            
    with st.container(height=350, border=True):
        if not item_options:
            st.info("Tidak ada barang yang cocok dengan filter.")
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
            
            existing_items_list = list(st.session_state[state_items_key])
            existing_defaults_list = list(st.session_state[state_defaults_key])
            
            kept_ids = []
            kept_defaults = []
            
            if current_items:
                remaining_curr = list(current_items)
                for idx, r_id in enumerate(existing_items_list):
                    d_val = existing_defaults_list[idx] if idx < len(existing_defaults_list) else None
                    if not d_val:
                        d_val = st.session_state.get(f"item_masuk_{r_id}")
                    if d_val and d_val in remaining_curr:
                        kept_ids.append(r_id)
                        kept_defaults.append(d_val)
                        remaining_curr.remove(d_val)
            
            # Clean up old empty widget keys from st.session_state
            for r_id in existing_items_list:
                if r_id not in kept_ids:
                    for k in list(st.session_state.keys()):
                        if k.endswith(f"_{r_id}"):
                            st.session_state.pop(k, None)
            
            max_id = max(existing_items_list) if existing_items_list else 0
            new_ids = [max_id + 1 + idx for idx in range(len(items_to_add))]
            
            st.session_state[state_items_key] = kept_ids + new_ids
            st.session_state[state_defaults_key] = kept_defaults + list(items_to_add)
            
        if 'dialog_sel_items_set' in st.session_state:
            del st.session_state['dialog_sel_items_set']
        st.rerun()

def execute_koreksi_save(items_to_save, master_df):
    """Menyimpan pembaruan koreksi transaksi stok masuk dan master barang."""
    trx_masuk_current = get_sheet_data(SHEET_STOK_MASUK)
    master_current = master_df.copy()
    master_changed = False
    log_entries = []
    
    for item in items_to_save:
        o_idx = item['orig_idx']
        item_name = item['nama_barang']
        supp_name = item['supplier']
        new_q = float(item['new_qty'])
        old_q = float(item['old_qty'])
        new_p = float(item['new_price'])
        old_p = float(item['old_price'])
        new_tot = float(item['new_total'])
        new_ket = item['keterangan']
        upd_hpp = item['update_hpp']
        
        # 1. Update baris di SHEET_STOK_MASUK
        if o_idx in trx_masuk_current.index:
            trx_masuk_current.at[o_idx, 'qty'] = new_q
            trx_masuk_current.at[o_idx, 'harga_real'] = new_p
            trx_masuk_current.at[o_idx, 'total_harga'] = new_tot
            trx_masuk_current.at[o_idx, 'keterangan'] = new_ket
            if 'sisa_qty' in trx_masuk_current.columns:
                curr_sisa = float(trx_masuk_current.at[o_idx, 'sisa_qty']) if pd.notna(trx_masuk_current.at[o_idx, 'sisa_qty']) else old_q
                trx_masuk_current.at[o_idx, 'sisa_qty'] = max(0.0, curr_sisa + (new_q - old_q))
            
        # 2. Update Master Barang jika Qty berubah atau HPP dicentang
        qty_diff = new_q - old_q
        idx_m_list = []
        if supp_name and str(supp_name).strip() not in ["-", ""]:
            idx_m_list = master_current.index[
                (master_current['nama_barang'].astype(str).str.strip().str.lower() == item_name.strip().lower()) &
                (master_current['supplier'].astype(str).str.strip().str.lower() == str(supp_name).strip().lower())
            ].tolist()
        if not idx_m_list:
            idx_m_list = master_current.index[master_current['nama_barang'].astype(str).str.strip().str.lower() == item_name.strip().lower()].tolist()

        if idx_m_list:
            m_idx = idx_m_list[0]
            if qty_diff != 0:
                cur_stok = float(pd.to_numeric(master_current.at[m_idx, 'stok_sekarang'], errors='coerce')) if pd.notna(master_current.at[m_idx, 'stok_sekarang']) else 0.0
                master_current.at[m_idx, 'stok_sekarang'] = max(0.0, cur_stok + qty_diff)
                master_changed = True
            if 'harga_real' not in master_current.columns:
                master_current['harga_real'] = master_current['harga_master'].copy() if 'harga_master' in master_current.columns else 0.0
            if new_p > 0:
                master_current.at[m_idx, 'harga_real'] = new_p
                master_changed = True
            if upd_hpp:
                master_current.at[m_idx, 'harga_master'] = new_p
                master_changed = True
                
        # 3. Catat Log
        log_entries.append({
            "tanggal": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "aksi": "KOREKSI_HARGA_STOK_MASUK",
            "keterangan": f"Koreksi {item_name} ({supp_name}): Harga Rp {old_p:,.0f} -> Rp {new_p:,.0f} (Qty: {old_q} -> {new_q})"
        })
        
    save_data(trx_masuk_current, SHEET_STOK_MASUK)
    if master_changed:
        save_data(master_current, SHEET_MASTER)
        
    if log_entries:
        from data.sheets_repository import SHEET_LOG
        crud_log_df = get_sheet_data(SHEET_LOG)
        new_log_df = pd.DataFrame(log_entries)
        crud_log_df = pd.concat([crud_log_df, new_log_df], ignore_index=True)
        save_data(crud_log_df, SHEET_LOG)
        
    # Bersihkan session state widget koreksi agar nilai terupdate bersih
    for k in list(st.session_state.keys()):
        if k.startswith(("kor_qty_", "kor_real_", "kor_ket_", "kor_hpp_", "rw_qty_", "rw_real_", "rw_ket_", "rw_hpp_", "rw_tot_")):
            del st.session_state[k]
            
    count_saved = len(items_to_save)
    st.session_state['toast_msg_masuk'] = f"Koreksi {count_saved} barang berhasil disimpan!"
    st.rerun()

def render_koreksi_pembelian(master_df):
    st.title("🏷️ Input Riwayat Harga")
    st.caption("Pilih tanggal dan supplier untuk menampilkan daftar pembelian yang telah diinput, lalu langsung koreksi harga beli real atau qty di bawah:")

    today = datetime.date.today()
    
    with st.container(border=True):
        c_k_date, c_k_sup, c_k_search = st.columns([1.5, 1.5, 1.5])
        with c_k_date:
            date_range = st.date_input(
                "📅 Tanggal Pembelian:",
                value=(today, today),
                key="koreksi_date_range"
            )
            if len(date_range) == 2:
                k_start, k_end = date_range
            else:
                k_start = date_range[0]
                k_end = date_range[0]
                
        with c_k_sup:
            raw_sups = extract_unique_suppliers(master_df)
            k_sup_opts = ["Semua Supplier"] + raw_sups
            selected_k_sup = st.selectbox("🏢 Filter Supplier:", k_sup_opts, key="koreksi_filter_sup")
            
        with c_k_search:
            k_search = st.text_input("🔍 Cari Barang / Nota:", placeholder="Ketik nama barang atau nota...", key="koreksi_search_q")

    # Ambil data transaksi stok masuk
    trx_masuk_df = get_sheet_data(SHEET_STOK_MASUK)
    if trx_masuk_df.empty or 'tanggal' not in trx_masuk_df.columns:
        st.info("ℹ️ Belum ada data transaksi stok masuk yang tersimpan.")
        return

    # Track original dataframe index
    df_trx = trx_masuk_df.copy()
    df_trx['_orig_idx'] = df_trx.index
    df_trx['parsed_date'] = pd.to_datetime(df_trx['tanggal'], errors='coerce').dt.date
    
    # Filter
    mask = (df_trx['parsed_date'] >= k_start) & (df_trx['parsed_date'] <= k_end)
    if selected_k_sup != "Semua Supplier":
        mask = mask & df_trx['supplier'].apply(lambda x: match_supplier(x, selected_k_sup))
    if k_search:
        search_mask = (
            df_trx['nama_barang'].astype(str).str.contains(k_search, case=False, na=False) |
            df_trx['keterangan'].astype(str).str.contains(k_search, case=False, na=False)
        )
        mask = mask & search_mask
        
    filtered_trx = df_trx[mask].copy().sort_values(by='tanggal', ascending=False)
    
    if filtered_trx.empty:
        tgl_info = k_start.strftime('%d %b %Y') if k_start == k_end else f"{k_start.strftime('%d %b %Y')} s/d {k_end.strftime('%d %b %Y')}"
        st.info(f"ℹ️ Tidak ditemukan transaksi pembelian dari **{selected_k_sup}** pada periode **{tgl_info}**.")
        return

    st.markdown("<br>", unsafe_allow_html=True)

    with st.container(border=True):
        st.markdown(f"#### 📋 Tabel Koreksi Harga & Qty Pembelian ({len(filtered_trx)} Baris Transaksi)")
        st.caption("Semua barang dari hasil filter tanggal & supplier telah dimuat otomatis di bawah. Silakan langsung ubah **Harga Real** atau **Qty Masuk**:")
        
        # Header tabel input persis seperti Input Stok Masuk
        h1, h2, h3, h4, h5, h6, h7 = st.columns([2.3, 0.9, 1.2, 1.3, 1.4, 1.2, 1.8])
        h1.caption("Nama Barang & Supplier")
        h2.caption("Qty Masuk")
        h3.caption("HPP Master")
        h4.caption("Harga Real Beli")
        h5.caption("Status Perubahan")
        h6.caption("Subtotal Real")
        h7.caption("Keterangan / Nota")
        
        items_list = []
        grand_old_total = 0.0
        grand_new_total = 0.0

        for idx, (_, row) in enumerate(filtered_trx.iterrows()):
            orig_idx = int(row['_orig_idx'])
            item_name = str(row['nama_barang'])
            supp_val = str(row.get('supplier', '-'))
            tgl_val = str(row.get('tanggal', ''))[:10]
            
            try:
                old_qty = float(row['qty']) if pd.notna(row['qty']) else 1.0
            except:
                old_qty = 1.0

            try:
                old_price = float(row['harga_real']) if pd.notna(row['harga_real']) else 0.0
            except:
                old_price = 0.0

            old_hpp = float(row.get('harga_master', old_price)) if pd.notna(row.get('harga_master')) else old_price
            old_total = float(row.get('total_harga', old_qty * old_price)) if pd.notna(row.get('total_harga')) else (old_qty * old_price)
            old_ket = str(row['keterangan']) if pd.notna(row.get('keterangan')) and str(row.get('keterangan')).strip() not in ['nan', 'None'] else ""

            # Cari satuan dari master
            matching_m = master_df[master_df['nama_barang'] == item_name]
            satuan = matching_m['satuan'].iloc[0] if not matching_m.empty and 'satuan' in matching_m.columns else "Pcs"

            c1, c2, c3, c4, c5, c6, c7 = st.columns([2.3, 0.9, 1.2, 1.3, 1.4, 1.2, 1.8])
            
            with c1:
                st.text_input("Barang", value=item_name, disabled=True, key=f"rw_name_{orig_idx}", label_visibility="collapsed")
                st.markdown(f"<div style='font-size: 11px; color: #0284c7; margin-top: -10px; margin-bottom: 4px;'>🏢 {supp_val} <span style='color:gray;'>({tgl_val})</span></div>", unsafe_allow_html=True)
                
            with c2:
                edit_qty = st.number_input("Qty", min_value=0.0, value=old_qty, step=0.05, format="%.2f", key=f"rw_qty_{orig_idx}", label_visibility="collapsed")
                st.markdown(f"<div style='font-size: 11px; color: gray; margin-top: -10px; margin-bottom: 4px;'>{satuan}</div>", unsafe_allow_html=True)
                
            with c3:
                st.text_input("HPP", value=f"Rp {old_hpp:,.0f}", disabled=True, key=f"rw_hpp_{orig_idx}", label_visibility="collapsed")
                
            with c4:
                edit_price = st.number_input("Harga Real", min_value=0, value=int(old_price), step=100, format="%d", key=f"rw_real_{orig_idx}", label_visibility="collapsed")
                st.markdown(f"<div style='font-size: 11px; color: gray; margin-top: -10px; margin-bottom: 4px;'>Semula: Rp {old_price:,.0f}</div>", unsafe_allow_html=True)
                
            with c5:
                selisih_hpp = edit_price - old_hpp
                if selisih_hpp > 0:
                    badge_html = f"<div style='background-color: #fee2e2; border: 1px solid #f87171; color: #991b1b; padding: 7px 8px; border-radius: 8px; text-align: center; font-size: 12px; font-weight: 700; height: 38px; display: flex; align-items: center; justify-content: center;' title='Harga di atas HPP (+Rp {selisih_hpp:,.0f})'>🔺 Naik</div>"
                elif selisih_hpp < 0:
                    badge_html = f"<div style='background-color: #dcfce7; border: 1px solid #4ade80; color: #166534; padding: 7px 8px; border-radius: 8px; text-align: center; font-size: 12px; font-weight: 700; height: 38px; display: flex; align-items: center; justify-content: center;' title='Harga di bawah HPP (-Rp {abs(selisih_hpp):,.0f})'>🔻 Turun</div>"
                else:
                    badge_html = "<div style='background-color: #f3f4f6; border: 1px solid #d1d5db; color: #4b5563; padding: 7px 8px; border-radius: 8px; text-align: center; font-size: 12px; font-weight: 700; height: 38px; display: flex; align-items: center; justify-content: center;'>⚖️ Sama</div>"
                st.markdown(badge_html, unsafe_allow_html=True)
                
            new_total = edit_qty * edit_price
            with c6:
                st.text_input("Subtotal", value=f"Rp {new_total:,.0f}", disabled=True, key=f"rw_tot_{orig_idx}", label_visibility="collapsed")
                
            with c7:
                edit_ket = st.text_input("Ket", value=old_ket, placeholder="Catatan...", key=f"rw_ket_{orig_idx}", label_visibility="collapsed")

            is_changed = (edit_qty != old_qty) or (edit_price != old_price) or (edit_ket.strip() != old_ket.strip())
            items_list.append({
                'orig_idx': orig_idx,
                'nama_barang': item_name,
                'supplier': supp_val,
                'old_qty': old_qty,
                'new_qty': edit_qty,
                'old_price': old_price,
                'new_price': edit_price,
                'old_total': old_total,
                'new_total': new_total,
                'keterangan': edit_ket.strip(),
                'is_changed': is_changed
            })
            grand_old_total += old_total
            grand_new_total += new_total

        st.divider()

        # Bottom Summary & Save Controls
        col_calc, col_opt, col_sub = st.columns([2.5, 1.8, 1.4])
        
        changed_count = sum(1 for it in items_list if it['is_changed'])
        diff_total = grand_new_total - grand_old_total
        
        with col_calc:
            if diff_total < 0:
                diff_tag = f"🟩 Hemat Rp {abs(diff_total):,.0f}"
            elif diff_total > 0:
                diff_tag = f"🟥 Naik +Rp {diff_total:,.0f}"
            else:
                diff_tag = "⚖️ Tetap"
            st.info(f"**Total Semula:** Rp {grand_old_total:,.0f} ➡️ **Total Baru:** Rp {grand_new_total:,.0f} &nbsp;|&nbsp; **{diff_tag}** ({changed_count} item diubah)")
            
        with col_opt:
            update_hpp_master = st.checkbox(
                "🔄 Sekaligus update HPP Master",
                value=False,
                key="rw_update_hpp_global",
                help="Jika dicentang, harga real baru yang diubah akan otomatis dijadikan harga acuan HPP di Master Barang."
            )
            
        with col_sub:
            btn_save = st.button("💾 Simpan Perubahan", type="primary", use_container_width=True, key="btn_save_riwayat", disabled=(changed_count == 0))

        if btn_save:
            modified_items = [it for it in items_list if it['is_changed']]
            for it in modified_items:
                it['update_hpp'] = update_hpp_master
                
            with st.spinner(f"Menyimpan pembaruan untuk {len(modified_items)} barang..."):
                try:
                    execute_koreksi_save(modified_items, master_df)
                except Exception as e:
                    st.error(f"Gagal menyimpan: {e}")

    # Tabel Riwayat Lengkap & Ekspor CSV
    st.markdown("<br>", unsafe_allow_html=True)
    with st.expander("🔍 Lihat Tabel Lengkap Riwayat Pembelian (Data Mentah)", expanded=False):
        t_disp = filtered_trx[['tanggal', 'shift', 'supplier', 'nama_barang', 'qty', 'harga_master', 'harga_real', 'total_harga', 'keterangan']].copy()
        for col_rp in ['harga_master', 'harga_real', 'total_harga']:
            if col_rp in t_disp.columns:
                t_disp[col_rp] = t_disp[col_rp].apply(lambda x: f"Rp {float(x):,.0f}")
        
        t_disp = t_disp.rename(columns={
            'tanggal': 'Tanggal',
            'shift': 'Shift',
            'supplier': 'Supplier',
            'nama_barang': 'Nama Barang',
            'qty': 'Qty',
            'harga_master': 'HPP Master',
            'harga_real': 'Harga Real',
            'total_harga': 'Total Harga',
            'keterangan': 'Nota / Ket'
        })
        
        st.dataframe(t_disp, use_container_width=True, hide_index=True)
        
        csv_bytes = filtered_trx.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Export Riwayat Pembelian ke CSV",
            data=csv_bytes,
            file_name=f"Riwayat_Pembelian_{k_start}_sd_{k_end}.csv",
            mime="text/csv",
            key="dl_csv_riwayat_pembelian"
        )

def render_input_stok_masuk(master_df):
    col_title, col_date = st.columns([2.8, 1.4])
    with col_title:
        st.title("📥 Input Stok Masuk (Belanja)")
    with col_date:
        st.markdown('<span class="timestamp-blue-marker"></span>', unsafe_allow_html=True)
        tgl_transaksi = st.date_input("📅 Tanggal Transaksi", value=datetime.date.today(), key="tgl_trx_masuk")

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
            raw_suppliers = extract_unique_suppliers(master_df)
            supplier_list = raw_suppliers + [s for s in ["Kasir", "Lainnya"] if s not in raw_suppliers]
            supplier_opt = st.selectbox("Nama Supplier *", supplier_list, key="supplier_masuk_opt")
            if supplier_opt == "Lainnya":
                supplier = st.text_input("Ketik Nama Supplier *", key="supplier_masuk")
            else:
                supplier = supplier_opt
        with c4:
            freetext_val = st.text_input("Nota / Keterangan Pembelian *", placeholder="Contoh: INV-8921...", key="free_masuk")

        st.divider()

        # 2. DYNAMIC ITEM ROWS
        all_items = [x for x in master_df['nama_barang'].dropna().unique().tolist() if str(x).strip()]
        if supplier and supplier not in ["Lainnya", "Kasir"] and 'supplier' in master_df.columns:
            supp_items = [x for x in master_df[master_df['supplier'].apply(lambda x: match_supplier(x, supplier))]['nama_barang'].dropna().unique().tolist() if str(x).strip()]
            item_options = supp_items if supp_items else all_items
        else:
            item_options = all_items
        
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

            # Get item data sesuai supplier yang dipilih (jika ada)
            matching_items = master_df[master_df['nama_barang'].astype(str).str.strip().str.lower() == selected_item.strip().lower()]
            if not matching_items.empty:
                if supplier and supplier not in ["Lainnya", "Kasir", "-", ""]:
                    matched_by_sup = matching_items[matching_items['supplier'].astype(str).str.strip().str.lower() == str(supplier).strip().lower()]
                    if not matched_by_sup.empty:
                        item_data = matched_by_sup.iloc[0]
                        stok_fisik = max(0.0, float(pd.to_numeric(item_data.get('stok_sekarang', 0), errors='coerce')))
                    else:
                        item_data = matching_items.iloc[0]
                        stok_fisik = 0.0  # Supplier baru untuk barang ini
                else:
                    item_data = matching_items.iloc[0]
                    stok_fisik = max(0.0, float(pd.to_numeric(item_data.get('stok_sekarang', 0), errors='coerce')))

                satuan = str(item_data.get('satuan', '')).strip()
                kategori = item_data.get('kategori', '')
                harga_master = float(pd.to_numeric(item_data.get('harga_master', 0), errors='coerce'))
                harga_real_prev = float(pd.to_numeric(item_data.get('harga_real', 0), errors='coerce'))
                default_beli = int(harga_real_prev) if harga_real_prev > 0 else int(harga_master)
            else:
                stok_fisik = 0.0
                satuan = "Pcs"
                kategori = ""
                harga_master = 0.0
                harga_real_prev = 0.0
                default_beli = 0
            
            with c2:
                qty = st.number_input("Qty", min_value=0.0, value=1.0, step=0.05, format="%.2f", key=f"qty_masuk_{row_id}", label_visibility="collapsed")
                st.markdown(f"<div style='font-size: 11px; color: gray; text-align: left; margin-top: -10px; margin-bottom: 5px; padding-left: 2px;'>{satuan}</div>", unsafe_allow_html=True)
            
            with c3:
                st.text_input("HPP", value=f"Rp {harga_master:,.0f}", disabled=True, key=f"hpp_masuk_{row_id}_{selected_item}", label_visibility="collapsed")
                
            with c4:
                harga_real = st.number_input("Harga Beli", min_value=0, value=default_beli, step=100, format="%d", key=f"real_masuk_{row_id}_{selected_item}", label_visibility="collapsed")
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
                # Sinkronkan filter supplier di dialog dengan supplier yang dipilih di form utama
                valid_sups = extract_unique_suppliers(master_df)
                if supplier in valid_sups:
                    st.session_state["dlg_supp_filter"] = supplier
                else:
                    st.session_state["dlg_supp_filter"] = "Semua Supplier"

                current_items_in_form = []
                for idx, r_id in enumerate(st.session_state[state_items_key]):
                    item_val = st.session_state.get(f"item_masuk_{r_id}")
                    if not item_val and idx < len(st.session_state[state_defaults_key]):
                        item_val = st.session_state[state_defaults_key][idx]
                    if item_val:
                        current_items_in_form.append(item_val)
                multi_select_dialog(master_df, state_items_key, state_defaults_key, current_items_in_form, default_supplier=supplier)
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
                    if 'harga_real' not in master_df_updated.columns:
                        master_df_updated['harga_real'] = master_df_updated['harga_master'].copy() if 'harga_master' in master_df_updated.columns else 0.0
                    
                    timestamp = datetime.datetime.combine(tgl_transaksi, now.time()).strftime("%Y-%m-%d %H:%M:%S")
                    
                    for r in row_data:
                        r_name = str(r['nama_barang']).strip()
                        r_supp = str(supplier).strip()

                        # Cari baris spesifik nama_barang DAN supplier
                        matching_indices = []
                        if r_supp and r_supp not in ["Lainnya", "Kasir", "-", ""]:
                            matching_indices = master_df_updated.index[
                                (master_df_updated['nama_barang'].astype(str).str.strip().str.lower() == r_name.lower()) &
                                (master_df_updated['supplier'].astype(str).str.strip().str.lower() == r_supp.lower())
                            ].tolist()

                        if matching_indices:
                            idx = matching_indices[0]
                            stok_lama = float(pd.to_numeric(master_df_updated.at[idx, 'stok_sekarang'], errors='coerce')) if pd.notna(master_df_updated.at[idx, 'stok_sekarang']) else 0.0
                            stok_baru = stok_lama + r['qty']
                            master_df_updated.at[idx, 'stok_sekarang'] = stok_baru
                            if float(r.get('harga_real', 0)) > 0:
                                master_df_updated.at[idx, 'harga_real'] = float(r['harga_real'])
                        else:
                            # Jika belum ada baris spesifik untuk supplier ini pada master_barang
                            base_indices = master_df_updated.index[
                                master_df_updated['nama_barang'].astype(str).str.strip().str.lower() == r_name.lower()
                            ].tolist()

                            if base_indices and r_supp and r_supp not in ["Lainnya", "Kasir", "-", ""]:
                                # Buat baris baru untuk supplier ini di master_barang
                                base_row = master_df_updated.loc[base_indices[0]].copy()
                                base_row['supplier'] = r_supp
                                base_row['stok_sekarang'] = float(r['qty'])
                                if float(r.get('harga_real', 0)) > 0:
                                    base_row['harga_real'] = float(r['harga_real'])
                                master_df_updated = pd.concat([master_df_updated, pd.DataFrame([base_row])], ignore_index=True)
                            elif base_indices:
                                idx = base_indices[0]
                                stok_lama = float(pd.to_numeric(master_df_updated.at[idx, 'stok_sekarang'], errors='coerce')) if pd.notna(master_df_updated.at[idx, 'stok_sekarang']) else 0.0
                                master_df_updated.at[idx, 'stok_sekarang'] = stok_lama + r['qty']
                                if float(r.get('harga_real', 0)) > 0:
                                    master_df_updated.at[idx, 'harga_real'] = float(r['harga_real'])
                        
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
                            "keterangan": freetext_val,
                            "sisa_qty": r['qty']
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
    
    master_df = get_sheet_data(SHEET_MASTER)
    if master_df.empty:
        st.warning("Data Master Barang kosong!")
        return

    render_input_stok_masuk(master_df)

def show_riwayat_harga():
    if 'toast_msg_masuk' in st.session_state:
        show_toast(st.session_state.pop('toast_msg_masuk'))
        
    master_df = get_sheet_data(SHEET_MASTER)
    if master_df.empty:
        st.warning("Data Master Barang kosong!")
        return

    render_koreksi_pembelian(master_df)

