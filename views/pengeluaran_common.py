import streamlit as st
import datetime
import pandas as pd
import time
from data.sheets_repository import (
    get_sheet_data, save_data, SHEET_MASTER, 
    SHEET_PENGELUARAN_PASIEN, SHEET_PENGELUARAN_DOKTER, SHEET_PENGELUARAN_MANAJEMEN
)
from views.transaksi import extract_unique_suppliers

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

def get_item_suppliers(item_name, master_df, stok_masuk_df=None):
    """Ambil daftar supplier unik yang memasok barang ini dari master_df & stok_masuk_df."""
    item_sups = []
    if not item_name or str(item_name).strip() == "":
        return item_sups
    clean_target = str(item_name).strip().lower()
    
    # 1. Dari master_df (bisa multi baris per barang atau dipisah titik koma)
    if not master_df.empty and 'nama_barang' in master_df.columns:
        m_match = master_df[master_df['nama_barang'].astype(str).str.strip().str.lower() == clean_target]
        for _, row in m_match.iterrows():
            raw_s = str(row.get('supplier', '')).strip()
            if raw_s and raw_s not in ['-', 'nan', 'None']:
                for s in raw_s.split(';'):
                    s_clean = s.strip()
                    if s_clean and s_clean not in item_sups:
                        item_sups.append(s_clean)
                        
    # 2. Dari stok_masuk_df (prioritaskan yang ada sisa_qty > 0)
    if stok_masuk_df is not None and not stok_masuk_df.empty and 'nama_barang' in stok_masuk_df.columns and 'supplier' in stok_masuk_df.columns:
        s_match = stok_masuk_df[stok_masuk_df['nama_barang'].astype(str).str.strip().str.lower() == clean_target]
        if 'sisa_qty' in s_match.columns:
            s_active = s_match[pd.to_numeric(s_match['sisa_qty'], errors='coerce').fillna(0) > 0]
            for s in s_active['supplier'].dropna():
                s_clean = str(s).strip()
                if s_clean and s_clean not in ['-', 'nan', 'None'] and s_clean not in item_sups:
                    item_sups.append(s_clean)
        for s in s_match['supplier'].dropna():
            s_clean = str(s).strip()
            if s_clean and s_clean not in ['-', 'nan', 'None'] and s_clean not in item_sups:
                item_sups.append(s_clean)
                
    return item_sups

def get_pkg_qty(prefix, kategori, item, default_val=1.0):
    val = st.session_state.get(f"stored_{prefix}_qty_{kategori}_{item}")
    if val is None:
        val = st.session_state.get(f"{prefix}_qty_{kategori}_{item}")
    try:
        return float(val) if val is not None else default_val
    except (ValueError, TypeError):
        return default_val

def get_pkg_sup(prefix, kategori, item, default_val="-"):
    val = st.session_state.get(f"stored_{prefix}_sup_{kategori}_{item}")
    if not val or val == "-":
        val = st.session_state.get(f"{prefix}_sup_{kategori}_{item}")
    return str(val).strip() if val else default_val

def resolve_pkg_supplier(item_name, chosen, master_dict_by_name):
    if chosen and str(chosen).strip() not in ["-", "[Sesuai Paket]", "None", "nan", ""]:
        return str(chosen).strip()
    m = master_dict_by_name.get(item_name, {})
    raw_s = str(m.get('supplier', '-')).strip()
    if raw_s and raw_s not in ['nan', 'None', '-', '']:
        return raw_s.split(';')[0].strip()
    return "-"

def get_prioritized_options(keywords, all_options):
    matches = []
    others = []
    seen = set()
    for opt in all_options:
        opt_str = str(opt).strip()
        if not opt_str or opt_str.lower() in ['nan', 'none']:
            continue
        key_lower = opt_str.lower()
        if key_lower in seen:
            continue
        seen.add(key_lower)
        if any(kw in key_lower for kw in keywords):
            matches.append(opt_str)
        else:
            others.append(opt_str)
    return sorted(matches, key=str.lower) + sorted(others, key=str.lower)

def format_pkg_summary(items, prefix, default_label, kategori, master_dict_by_name=None):
    if not items:
        def_s = get_pkg_sup(prefix, kategori, default_label)
        if (not def_s or def_s == "-") and master_dict_by_name:
            def_s = resolve_pkg_supplier(default_label, def_s, master_dict_by_name)
        return f"{default_label} [{def_s}]" if def_s and def_s != "-" else default_label
    parts = []
    for it in items:
        q = get_pkg_qty(prefix, kategori, it, 1.0)
        s = get_pkg_sup(prefix, kategori, it)
        if (not s or s == "-") and master_dict_by_name:
            s = resolve_pkg_supplier(it, s, master_dict_by_name)
        s_str = f" [{s}]" if s and s != "-" else ""
        parts.append(f"{q:g}x {it}{s_str}")
    return ", ".join(parts)

def render_pkg_config_column(title, emoji, items_options, selected_items, state_key, prefix, default_item, kategori, master_df, raw_suppliers, placeholder="Pilih item..."):
    st.markdown(f"**{emoji} {title}**")
    
    # 1. Deduplicate & clean options
    cleaned_options = []
    seen_opts = set()
    for opt in items_options:
        o_clean = str(opt).strip()
        if o_clean and o_clean.lower() not in seen_opts and o_clean.lower() not in ['nan', 'none']:
            seen_opts.add(o_clean.lower())
            cleaned_options.append(o_clean)
            
    # Clean selected_items
    valid_defaults = []
    seen_sel = set()
    for s in selected_items:
        s_clean = str(s).strip()
        if s_clean in cleaned_options and s_clean.lower() not in seen_sel:
            seen_sel.add(s_clean.lower())
            valid_defaults.append(s_clean)
            
    new_items = st.multiselect(
        f"Pilih {title}:",
        options=cleaned_options,
        default=valid_defaults,
        key=f"input_{prefix}_{kategori}",
        placeholder=placeholder
    )
    st.session_state[state_key] = new_items
    if new_items:
        for it in new_items:
            col_q, col_s = st.columns([1, 1.4])
            with col_q:
                k_qty = f"{prefix}_qty_{kategori}_{it}"
                stored_k_qty = f"stored_{prefix}_qty_{kategori}_{it}"
                init_qty = get_pkg_qty(prefix, kategori, it, 1.0)
                val = st.number_input(f"Qty {it}:", min_value=0.5, value=init_qty, step=0.5, key=k_qty)
                st.session_state[stored_k_qty] = val
            with col_s:
                it_sups = get_item_suppliers(it, master_df)
                it_other_sups = [s for s in raw_suppliers if s not in it_sups]
                it_sup_options = it_sups + (["-"] if "-" not in it_sups else []) + it_other_sups
                k_sup = f"{prefix}_sup_{kategori}_{it}"
                stored_k_sup = f"stored_{prefix}_sup_{kategori}_{it}"
                def_sup = it_sups[0] if it_sups else "-"
                cur_sup = st.session_state.get(stored_k_sup, st.session_state.get(k_sup, def_sup))
                if cur_sup not in it_sup_options:
                    cur_sup = def_sup if def_sup in it_sup_options else it_sup_options[0]
                sup_idx = it_sup_options.index(cur_sup)
                sel_sup = st.selectbox(f"Supplier {it}:", it_sup_options, index=sup_idx, key=k_sup)
                st.session_state[stored_k_sup] = sel_sup
    else:
        st.caption(f"ℹ️ *Default: 1x '{default_item}'*")
        def_it = default_item
        col_q, col_s = st.columns([1, 1.4])
        with col_q:
            st.number_input(f"Qty {def_it}:", min_value=0.5, value=1.0, step=0.5, disabled=True, key=f"dis_qty_{prefix}_{kategori}")
        with col_s:
            it_sups = get_item_suppliers(def_it, master_df)
            it_other_sups = [s for s in raw_suppliers if s not in it_sups]
            it_sup_options = it_sups + (["-"] if "-" not in it_sups else []) + it_other_sups
            k_sup = f"{prefix}_sup_{kategori}_{def_it}"
            stored_k_sup = f"stored_{prefix}_sup_{kategori}_{def_it}"
            def_sup = it_sups[0] if it_sups else "-"
            cur_sup = st.session_state.get(stored_k_sup, st.session_state.get(k_sup, def_sup))
            if cur_sup not in it_sup_options:
                cur_sup = def_sup if def_sup in it_sup_options else it_sup_options[0]
            sup_idx = it_sup_options.index(cur_sup)
            sel_sup = st.selectbox(f"Supplier {def_it}:", it_sup_options, index=sup_idx, key=k_sup)
            st.session_state[stored_k_sup] = sel_sup
    return new_items

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
        filtered_df = filtered_df[filtered_df['nama_barang'].str.contains(search_q, case=False, na=False, regex=False)]
        
    filtered_df = filtered_df.drop_duplicates(subset=['nama_barang'])
    item_options = [str(x).strip() for x in filtered_df['nama_barang'].dropna().unique() if str(x).strip()]
    
    st.markdown(f"<div style='font-size:0.85rem; color:gray; font-weight:600;'>Ringkasan Terpilih: {len(st.session_state[temp_key])} barang secara keseluruhan</div>", unsafe_allow_html=True)
    
    c_btn1, c_btn2 = st.columns(2)
    with c_btn1:
        if st.button("☑️ Pilih Semua (Filter Saat Ini)", use_container_width=True):
            st.session_state[temp_key].update(item_options)
            st.rerun()
    with c_btn2:
        if st.button("🔲 Kosongkan Semua", use_container_width=True):
            st.session_state[temp_key].clear()
            st.rerun()
            
    new_dialog_set = set([x for x in st.session_state[temp_key] if x not in item_options])
    
    with st.container(height=350, border=True):
        if not item_options:
            st.info("Tidak ada barang.")
        else:
            cols = st.columns(3)
            for i, item in enumerate(item_options):
                with cols[i % 3]:
                    is_checked = st.checkbox(
                        item, 
                        value=(item in st.session_state[temp_key]),
                        key=f"chk_multi_{state_items_key}_{i}_{item}"
                    )
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
            
            existing_items_list = list(st.session_state[state_items_key])
            existing_defaults_list = list(st.session_state[state_defaults_key])
            
            kept_ids = []
            kept_defaults = []
            
            if current_items:
                remaining_curr = list(current_items)
                for idx, r_id in enumerate(existing_items_list):
                    d_val = existing_defaults_list[idx] if idx < len(existing_defaults_list) else None
                    if not d_val:
                        for k, v in st.session_state.items():
                            if k.endswith(f"_{r_id}") and v in remaining_curr:
                                d_val = v
                                break
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

def render_form(tab_name, sheet_name, categories, tgl_transaksi=None):
    if tgl_transaksi is None:
        tgl_transaksi = datetime.date.today()
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

    raw_suppliers = extract_unique_suppliers(master_df)
    now = datetime.datetime.now()
    
    current_kategori = st.session_state.get(f"kat_{tab_name}", categories[0])
    
    state_items_key = f"dyn_items_{tab_name}_v3"
    state_defaults_key = f"dyn_defaults_{tab_name}_v3"
        
    item_options = list(dict.fromkeys(master_df['nama_barang'].tolist()))
    
    # Reset counter digunakan agar widget Streamlit dibuat ulang (nilai kembali ke default) setelah submit
    reset_counter_key = f"reset_ctr_{tab_name}"
    if reset_counter_key not in st.session_state:
        st.session_state[reset_counter_key] = 0
    rc = st.session_state[reset_counter_key]  # shorthand

    if state_items_key not in st.session_state:
        if tab_name == "Manajemen":
            default_names = ["Snack", "Buah (Manajemen)", "Roti", "Le Mineral 330", "Jus", "Cleo"]
            valid_defaults = []
            
            # Find closest matches in master_df
            for d in default_names:
                match = None
                for item in item_options:
                    if d.lower().strip() == str(item).lower().strip():
                        match = item; break
                if not match:
                    for item in item_options:
                        if str(item).lower().strip().startswith(d.lower().strip()):
                            match = item; break
                if not match:
                    for item in item_options:
                        if d.lower().strip() in str(item).lower().strip():
                            match = item; break
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
            if k.startswith((f"qty_{tab_name}", f"ket_{tab_name}", f"item_{tab_name}", f"sat_{tab_name}", f"sup_{tab_name}", f"sup_pkg_{tab_name}", f"free_{tab_name}", f"shift_{tab_name}", f"kat_{tab_name}", f"jml_pasien_{tab_name}")):
                del st.session_state[k]

    with st.container(border=True):
        # 1. HEADER (Shift & Kategori)
        c1, c2, c3 = st.columns([1, 1.5, 2])
        with c1:
            shift = st.selectbox(f"Keterangan Waktu \*", ["Pagi (07:00-15:00)", "Siang (15:00-22:00)", "Malam (22:00-07:00)", "1 Hari"], key=f"shift_{tab_name}")
        with c2:
            kategori = st.selectbox(f"Kategori {tab_name} \*", categories, key=f"kat_{tab_name}")
        with c3:
            freetext_val = st.text_input(f"Identitas / Keterangan (Nama/Ruangan) \*", key=f"free_{tab_name}")
            
        st.divider()

        # --- PENGATURAN PAKET MANAJEMEN ---
        has_pkg_feature = (tab_name == "Manajemen")
        pkg_snack_key = f"pkg_snack_items_{tab_name}"
        pkg_buah_key = f"pkg_buah_items_{tab_name}"
        pkg_roti_key = f"pkg_roti_items_{tab_name}"
        pkg_toggle_key = f"toggle_pkg_{tab_name}"
        
        if has_pkg_feature:
            default_snack_label = "Snack"
            default_buah_label = "Buah (Manejemen)"
            default_roti_label = "Roti"
            
            selected_snack_items = st.session_state.get(pkg_snack_key, [])
            selected_buah_items = st.session_state.get(pkg_buah_key, [])
            selected_roti_items = st.session_state.get(pkg_roti_key, [])
            
            snack_summary = format_pkg_summary(selected_snack_items, "pkg_snack", default_snack_label, tab_name)
            buah_summary = format_pkg_summary(selected_buah_items, "pkg_buah", default_buah_label, tab_name)
            roti_summary = format_pkg_summary(selected_roti_items, "pkg_roti", default_roti_label, tab_name)
            
            snack_options = get_prioritized_options(['pastel', 'lemper', 'risol', 'kue', 'sus', 'pie', 'bolu', 'puding', 'bapel', 'snack'], item_options)
            buah_options = get_prioritized_options(['pisang', 'jeruk', 'apel', 'semangka', 'melon', 'naga', 'buah'], item_options)
            roti_options = get_prioritized_options(['roti', 'bread'], item_options)
            
            bar_col1, bar_col2 = st.columns([3.2, 1.3])
            with bar_col1:
                st.markdown(f"""
                <div style="background-color: #f8fafc; border: 1px solid #cbd5e1; border-radius: 8px; padding: 7px 12px; font-size: 0.88em; line-height: 1.4;">
                    <b>🍱 Paket Aktif Manajemen:</b> &nbsp;
                    <span style="color: #0f766e;">🥐 <b>Snack:</b> {snack_summary}</span> &nbsp;|&nbsp; 
                    <span style="color: #b45309;">🍎 <b>Buah:</b> {buah_summary}</span> &nbsp;|&nbsp; 
                    <span style="color: #4338ca;">🍞 <b>Roti:</b> {roti_summary}</span>
                </div>
                """, unsafe_allow_html=True)
            with bar_col2:
                st.markdown("<div style='margin-top: 4px;'></div>", unsafe_allow_html=True)
                show_pkg_panel = st.toggle("⚙️ **Atur Isi Paket**", key=pkg_toggle_key, help="Buka/tutup form untuk mengatur komposisi barang fisik & supplier paket shift ini")
                
            def close_pkg_panel_mgmt():
                st.session_state[pkg_toggle_key] = False
                
            if show_pkg_panel:
                with st.container(border=True):
                    st.markdown(f"##### 🍱 Atur Komposisi Barang Fisik & Supplier ({tab_name})")
                    st.caption("Pilih barang fisik, lalu atur **Qty** dan **Supplier** masing-masing secara berdampingan di bawah ini:")
                    c_snk, c_buh, c_rot = st.columns(3)
                    with c_snk:
                        render_pkg_config_column("Paket Snack", "🥐", snack_options, selected_snack_items, pkg_snack_key, "pkg_snack", default_snack_label, tab_name, master_df, raw_suppliers, "Pilih kue/snack...")
                    with c_buh:
                        render_pkg_config_column("Paket Buah", "🍎", buah_options, selected_buah_items, pkg_buah_key, "pkg_buah", default_buah_label, tab_name, master_df, raw_suppliers, "Pilih buah...")
                    with c_rot:
                        render_pkg_config_column("Pilihan Roti", "🍞", roti_options, selected_roti_items, pkg_roti_key, "pkg_roti", default_roti_label, tab_name, master_df, raw_suppliers, "Pilih jenis roti...")
                        
                    selected_snack_items = st.session_state.get(pkg_snack_key, [])
                    selected_buah_items = st.session_state.get(pkg_buah_key, [])
                    selected_roti_items = st.session_state.get(pkg_roti_key, [])
                    snack_summary = format_pkg_summary(selected_snack_items, "pkg_snack", default_snack_label, tab_name)
                    buah_summary = format_pkg_summary(selected_buah_items, "pkg_buah", default_buah_label, tab_name)
                    roti_summary = format_pkg_summary(selected_roti_items, "pkg_roti", default_roti_label, tab_name)
                    
                    st.divider()
                    st.button("✅ Selesai Mengatur (Tutup Panel)", on_click=close_pkg_panel_mgmt, key=f"btn_close_pkg_{tab_name}", use_container_width=True)
                    
            st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
        else:
            selected_snack_items = []
            selected_buah_items = []
            selected_roti_items = []
            snack_summary = ""
            buah_summary = ""
            roti_summary = ""
            default_snack_label = ""
            default_buah_label = ""
            default_roti_label = ""

        # 2. DYNAMIC ITEM ROWS (Layout tanpa HPP Master dan Harga Real)
        h1, h_sup, h2, h_sat, h5, h6 = st.columns([2.5, 1.5, 1.1, 1.1, 1.8, 0.4])
        h1.caption("Pilih Barang")
        h_sup.caption("Pilih Supplier")
        h2.caption("Qty")
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
                    st.text_input("Ket", placeholder="Catatan...", disabled=True, key=f"ket_dis_{tab_name}_{rc}_{row_id}", label_visibility="collapsed")
                with c6:
                    st.button("🗑️", key=f"del_{tab_name}_{rc}_{row_id}", on_click=remove_row, args=(row_id,))
                continue
                
            is_snack_row = False
            is_buah_row = False
            is_roti_row = False
            if has_pkg_feature:
                sel_clean = str(selected_item).lower().strip()
                if "snack" in sel_clean:
                    is_snack_row = True
                elif "buah" in sel_clean:
                    is_buah_row = True
                elif "roti" in sel_clean or sel_clean == "roti":
                    is_roti_row = True
                    
            if is_snack_row:
                if selected_snack_items:
                    c1.caption(f"🍱 **Paket Snack:** {snack_summary}")
                else:
                    c1.caption(f"ℹ️ *Default: 1x '{default_snack_label}'*")
            elif is_buah_row:
                if selected_buah_items:
                    c1.caption(f"🍎 **Paket Buah:** {buah_summary}")
                else:
                    c1.caption(f"ℹ️ *Default: 1x '{default_buah_label}'*")
            elif is_roti_row:
                if selected_roti_items:
                    c1.caption(f"🍞 **Paket Roti:** {roti_summary}")
                else:
                    c1.caption(f"ℹ️ *Default: 1x '{default_roti_label}'*")
                    
            item_data = master_df[master_df['nama_barang'] == selected_item].iloc[0]
            stok_fisik = max(0.0, float(item_data.get('stok_sekarang', 0)))
            harga_master = float(item_data.get('harga_master', 0))
            satuan = item_data.get('satuan', '')
            is_unlimited = str(item_data.get('status', 'True')).upper() not in ['TRUE', '1', 'YES', 'T'] or float(item_data.get('stok_minimal', 0)) == 0
            
            default_qty = 1.0 if (is_snack_row or is_buah_row or is_roti_row) else 0.0
            max_qty = 99999.0 if (is_unlimited or (is_snack_row and selected_snack_items) or (is_buah_row and selected_buah_items) or (is_roti_row and selected_roti_items)) else max(1.0, float(stok_fisik))
            
            if is_snack_row and selected_snack_items:
                with c_sup:
                    st.text_input("Supplier", value="[Sesuai Paket]", disabled=True, key=f"sup_pkg_{tab_name}_{rc}_{row_id}", label_visibility="collapsed")
                final_supplier = "[Sesuai Paket]"
            elif is_buah_row and selected_buah_items:
                with c_sup:
                    st.text_input("Supplier", value="[Sesuai Paket]", disabled=True, key=f"sup_pkg_{tab_name}_{rc}_{row_id}", label_visibility="collapsed")
                final_supplier = "[Sesuai Paket]"
            elif is_roti_row and selected_roti_items:
                with c_sup:
                    st.text_input("Supplier", value="[Sesuai Paket]", disabled=True, key=f"sup_pkg_{tab_name}_{rc}_{row_id}", label_visibility="collapsed")
                final_supplier = "[Sesuai Paket]"
            else:
                item_sups = get_item_suppliers(selected_item, master_df)
                other_sups = [s for s in raw_suppliers if s not in item_sups]
                row_supplier_options = item_sups + (["-"] if "-" not in item_sups else []) + other_sups
                
                if is_snack_row:
                    def_s = st.session_state.get(f"pkg_snack_sup_{tab_name}_{default_snack_label}", "-")
                    default_supp = def_s if def_s in row_supplier_options else (item_sups[0] if item_sups else "-")
                elif is_buah_row:
                    def_s = st.session_state.get(f"pkg_buah_sup_{tab_name}_{default_buah_label}", "-")
                    default_supp = def_s if def_s in row_supplier_options else (item_sups[0] if item_sups else "-")
                elif is_roti_row:
                    def_s = st.session_state.get(f"pkg_roti_sup_{tab_name}_{default_roti_label}", "-")
                    default_supp = def_s if def_s in row_supplier_options else (item_sups[0] if item_sups else "-")
                else:
                    default_supp = item_sups[0] if item_sups else "-"
                    
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
                
            with c2:
                qty = st.number_input("Qty", min_value=0.0, max_value=max_qty, value=default_qty, step=1.0, format="%.2f", key=f"qty_{tab_name}_{rc}_{row_id}", label_visibility="collapsed")
                
            with c_sat:
                satuan_val = "Paket" if (is_snack_row or is_buah_row or is_roti_row) else satuan
                st.text_input("Satuan", value=satuan_val, disabled=True, key=f"sat_{tab_name}_{rc}_{row_id}", label_visibility="collapsed")
                
            with c5:
                keterangan = st.text_input("Ket", placeholder="Catatan (Opsional)...", key=f"ket_{tab_name}_{rc}_{row_id}", label_visibility="collapsed")
                
            with c6:
                st.button("🗑️", key=f"del_{tab_name}_{rc}_{row_id}", on_click=remove_row, args=(row_id,))
                
            if (is_snack_row and selected_snack_items) or (is_buah_row and selected_buah_items) or (is_roti_row and selected_roti_items):
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
                    "harga_real": harga_master,
                    "keterangan": keterangan.strip(),
                    "stok_fisik": stok_fisik,
                    "is_unlimited": is_unlimited,
                    "is_error": error_stok,
                    "is_snack_row": is_snack_row,
                    "is_buah_row": is_buah_row,
                    "is_roti_row": is_roti_row
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
        
        # 3. PENGURAIAN PAKET & VALIDASI STOK
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
                    q_unit = get_pkg_qty("pkg_snack", tab_name, sit, 1.0)
                    s_chosen = resolve_pkg_supplier(sit, get_pkg_sup("pkg_snack", tab_name, sit), master_dict_by_name)
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
                    q_unit = get_pkg_qty("pkg_buah", tab_name, bit, 1.0)
                    s_chosen = resolve_pkg_supplier(bit, get_pkg_sup("pkg_buah", tab_name, bit), master_dict_by_name)
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
            elif r.get('is_roti_row') and selected_roti_items:
                for rit in selected_roti_items:
                    q_unit = get_pkg_qty("pkg_roti", tab_name, rit, 1.0)
                    s_chosen = resolve_pkg_supplier(rit, get_pkg_sup("pkg_roti", tab_name, rit), master_dict_by_name)
                    m_info = master_dict_by_name_sup.get((rit, s_chosen), master_dict_by_name.get(rit, {}))
                    p_item = float(m_info.get('harga_master', 0))
                    stk_item = float(m_info.get('stok_sekarang', 0))
                    is_unl = str(m_info.get('status', 'True')).upper() not in ['TRUE', '1', 'YES', 'T'] or float(m_info.get('stok_minimal', 0)) == 0
                    tot_q = r['qty'] * q_unit
                    ket_str = f"Paket Roti ({r['qty']:g} pkt)"
                    if r['keterangan']:
                        ket_str += f" - {r['keterangan']}"
                    unrolled_rows.append({
                        "nama_barang": rit,
                        "supplier": s_chosen,
                        "qty": tot_q,
                        "harga_master": p_item,
                        "harga_real": p_item,
                        "keterangan": ket_str,
                        "stok_fisik": stk_item,
                        "is_unlimited": is_unl
                    })
            else:
                row_sup = resolve_pkg_supplier(r['nama_barang'], r['supplier'], master_dict_by_name)
                unrolled_rows.append({
                    "nama_barang": r['nama_barang'],
                    "supplier": row_sup,
                    "qty": r['qty'],
                    "harga_master": r['harga_master'],
                    "harga_real": r['harga_master'],
                    "keterangan": r['keterangan'] if r['keterangan'] else f"Input {tab_name}",
                    "stok_fisik": r['stok_fisik'],
                    "is_unlimited": r.get('is_unlimited', False)
                })
                
        stock_needed = {}
        for ur in unrolled_rows:
            key = (ur['nama_barang'], ur['supplier'])
            stock_needed[key] = stock_needed.get(key, 0.0) + ur['qty']
            
        insufficient_stock_errors = []
        for (it_name, sup_name), needed_qty in stock_needed.items():
            m_info = master_dict_by_name_sup.get((it_name, sup_name), master_dict_by_name.get(it_name, {}))
            stk_fisik = float(m_info.get('stok_sekarang', 0))
            is_unl = str(m_info.get('status', 'True')).upper() not in ['TRUE', '1', 'YES', 'T'] or float(m_info.get('stok_minimal', 0)) == 0
            if not is_unl and stk_fisik < needed_qty:
                supp_str = f" ({sup_name})" if sup_name and sup_name != "-" else ""
                insufficient_stock_errors.append(f"• **{it_name}**{supp_str} (dibutuhkan: {needed_qty:g}, stok tersisa: {stok_fisik:g})")
                
        has_error = bool(insufficient_stock_errors) or any(r.get('is_error') for r in row_data)
        
        total_real = sum(r['qty'] * r['harga_real'] for r in unrolled_rows)
        total_qty = sum(r['qty'] for r in unrolled_rows)
        
        col_calc, col_sub = st.columns([3, 1])
        with col_calc:
            if unrolled_rows:
                if has_pkg_feature and (selected_snack_items or selected_buah_items or selected_roti_items):
                    st.success(f"Terdapat **{len(unrolled_rows)} item fisik** (Total Qty: {total_qty:g} | Total Nilai: Rp {total_real:,.0f}) yang akan dimasukkan ke **{tab_name}** (paket telah diurai).")
                else:
                    st.success(f"Terdapat **{len(unrolled_rows)} macam barang** (Total Qty: {total_qty:g} | Total Nilai: Rp {total_real:,.0f}) yang akan dimasukkan ke **{tab_name}**.")
            else:
                col_calc.info("Tabel masih kosong atau semua qty 0.")
            if insufficient_stock_errors:
                st.error("⚠️ **Peringatan Stok Kurang:**<br>" + "<br>".join(insufficient_stock_errors), icon="🚨")
                
        with col_sub:
            submit = st.button("✓ Simpan Transaksi", type="primary", use_container_width=True, key=f"btn_simpan_{tab_name}", disabled=(len(unrolled_rows) == 0))
            
        if submit:
            if not str(freetext_val).strip():
                st.error("Identitas / Keterangan wajib diisi!")
                return
            if len(unrolled_rows) == 0:
                st.error("Pilih minimal 1 barang!")
                return
            if has_error:
                st.error("Ada barang yang stoknya tidak mencukupi. Silakan perbaiki terlebih dahulu!")
                return

            with st.spinner("Menyimpan semua transaksi..."):
                try:
                    trx_df = get_sheet_data(sheet_name)
                    new_rows = []
                    master_df_updated = master_df.copy()
                    timestamp = datetime.datetime.combine(tgl_transaksi, now.time()).strftime("%Y-%m-%d %H:%M:%S")
                    
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
                            
                        row_dict = {
                            "tanggal": timestamp,
                            "shift": shift,
                            "kategori": kategori,
                            "kategori_freetext": freetext_val.strip(),
                            "nama_barang": r['nama_barang'],
                            "supplier": r.get('supplier', '-'),
                            "qty": r['qty'],
                            "harga_master": r['harga_master'],
                            "harga_real": r['harga_real'],
                            "total_harga": r['qty'] * r['harga_real'],
                            "keterangan": r['keterangan']
                        }
                        new_rows.append(row_dict)
                        
                    save_data(master_df_updated, SHEET_MASTER)
                    trx_df = pd.concat([trx_df, pd.DataFrame(new_rows)], ignore_index=True)
                    save_data(trx_df, sheet_name)
                    
                    st.session_state[f'toast_msg_{tab_name}'] = f"{len(unrolled_rows)} item berhasil disimpan!"
                    
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
