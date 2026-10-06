import streamlit as st
import pandas as pd
from data.sheets_repository import load_data, get_sheet_data, SHEET_STOK_MASUK
from services.stock_service import (
    classify_stock_status, 
    calculate_bar_width,
    filter_stock_by_status
)
from utils.formatting import get_header_html, get_row_html

def show_analisis_stok():
    st.header("📈 Analisis Stok Gudang")
    
    master_df, _ = load_data()
    
    if master_df.empty:
        st.info("Belum ada data barang di Master Data.")
        return
        
    master_df['stok_minimum_safe'] = master_df['stok_minimum'].apply(lambda x: max(x, 1))
    master_df['persentase'] = master_df['stok_sekarang'] / master_df['stok_minimum_safe']
    
    krisis_df, mendekati_df, aman_df, bebas_df = filter_stock_by_status(master_df)
    
    # Scorecards
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        with st.container(border=True):
            st.markdown("🏢 **Total Barang**")
            st.markdown(f"<h2>{len(master_df)} <span style='font-size:16px'>SKU</span></h2>", unsafe_allow_html=True)
    with col2:
        with st.container(border=True):
            st.markdown("🚨 **Stok Habis**")
            st.markdown(f"<h2 style='color:#d32f2f'>{len(krisis_df)} <span style='font-size:16px; opacity: 0.7;'>SKU</span></h2>", unsafe_allow_html=True)
    with col3:
        with st.container(border=True):
            st.markdown("⚠️ **Mendekati Min**")
            st.markdown(f"<h2 style='color:#fbc02d'>{len(mendekati_df)} <span style='font-size:16px; opacity: 0.7;'>SKU</span></h2>", unsafe_allow_html=True)
    with col4:
        with st.container(border=True):
            st.markdown("✅ **Stok Aman**")
            st.markdown(f"<h2 style='color:#388e3c'>{len(aman_df)} <span style='font-size:16px; opacity: 0.7;'>SKU</span></h2>", unsafe_allow_html=True)
    # with col5:
    #     with st.container(border=True):
    #         st.markdown("🍲 **Bahan Bebas**")
    #         st.markdown(f"<h2 style='color:#1976d2'>{len(bebas_df)} <span style='font-size:16px; opacity: 0.7;'>SKU</span></h2>", unsafe_allow_html=True)
            
    st.markdown("---")
    
    # --- DAFTAR SELURUH STOK BARANG ---
    full_df = pd.concat([krisis_df, mendekati_df, aman_df, bebas_df]).sort_values(by='persentase')
    
    col_sup, col_filter, col_search = st.columns([1, 1, 1])
    # with col_title:
    #     st.markdown(get_header_html(len(full_df)), unsafe_allow_html=True)
    with col_sup:
        st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
        hist_masuk = get_sheet_data(SHEET_STOK_MASUK)
        available_sups = ["Pak Urip", "Wahana", "Ari Snack", "Supplier Yulia", "Roti Mayestik"]
        if not hist_masuk.empty and 'supplier' in hist_masuk.columns:
            extra_sups = [s for s in hist_masuk['supplier'].dropna().unique() if s not in available_sups and str(s).strip() != '']
            available_sups.extend(extra_sups)
        sup_filter = st.multiselect("Supplier:", available_sups, placeholder="Filter by Supplier...", label_visibility="collapsed")
    with col_filter:
        st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
        status_filter = st.multiselect("Status:", ["Krisis", "Minimum", "Aman", "Bahan Bebas"], default=["Krisis", "Minimum", "Aman", "Bahan Bebas"], label_visibility="collapsed")
    with col_search:
        st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
        search_q = st.text_input("🔍 Cari Barang (Nama / SKU):", placeholder="Ketik nama atau kode barang...", label_visibility="collapsed")
        
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Apply Status Filter
    if status_filter:
        # Full DF concat order matches the status classes roughly, but it's better to explicitly check
        # We can map the status back or just use the separate DFs
        filtered_dfs = []
        if "Krisis" in status_filter: filtered_dfs.append(krisis_df)
        if "Minimum" in status_filter: filtered_dfs.append(mendekati_df)
        if "Aman" in status_filter: filtered_dfs.append(aman_df)
        if "Bahan Bebas" in status_filter: filtered_dfs.append(bebas_df)
        
        full_df = pd.concat(filtered_dfs).sort_values(by='persentase') if filtered_dfs else pd.DataFrame(columns=full_df.columns)
    else:
        full_df = pd.DataFrame(columns=full_df.columns)
        
    # Apply Supplier Filter
    if sup_filter:
        if not hist_masuk.empty and 'supplier' in hist_masuk.columns:
            items_from_sups = hist_masuk[hist_masuk['supplier'].isin(sup_filter)]['nama_barang'].unique()
            full_df = full_df[full_df['nama_barang'].isin(items_from_sups)]
        else:
            full_df = full_df.iloc[0:0]
            
    if search_q:
        full_df = full_df[
            full_df['nama_barang'].str.contains(search_q, case=False, na=False, regex=False) | 
            full_df['kode_barang'].str.contains(search_q, case=False, na=False, regex=False)
        ]
        
    if len(full_df) == 0:
        if search_q:
            st.info(f"Pencarian '{search_q}' tidak ditemukan.")
        else:
            st.success("✅ **Semua Stok Aman!** Tidak ada barang yang tercatat.")
    else:
        h_col1, h_col2, h_col3, h_col4 = st.columns([1.5, 1.5, 1.2, 1.3])
        with h_col1: st.markdown("<span style='color: gray; font-size: 0.85rem; font-weight: 700;'>DETAIL BARANG & SKU</span>", unsafe_allow_html=True)
        with h_col2: st.markdown("<span style='color: gray; font-size: 0.85rem; font-weight: 700;'>LEVEL STOK SAAT INI</span>", unsafe_allow_html=True)
        with h_col3: st.markdown("<span style='color: gray; font-size: 0.85rem; font-weight: 700;'>STATUS & ESTIMASI</span>", unsafe_allow_html=True)
        with h_col4: st.markdown("<span style='color: gray; font-size: 0.85rem; font-weight: 700;'>SUPPLIER TERMURAH</span>", unsafe_allow_html=True)
        st.markdown("<hr style='margin-top: 5px; margin-bottom: 15px;'>", unsafe_allow_html=True)
        
        full_df['harga_master_numeric'] = pd.to_numeric(full_df['harga_master'], errors='coerce').fillna(float('inf'))
        full_df['stok_sekarang_numeric'] = pd.to_numeric(full_df['stok_sekarang'], errors='coerce').fillna(0)
        
        # Hitung total stok per barang dari semua supplier
        total_stok = full_df.groupby('nama_barang')['stok_sekarang_numeric'].sum()
        min_prices = full_df.groupby('nama_barang')['harga_master_numeric'].min()
        
        # Urutkan berdasarkan harga termurah lalu hapus duplikat (hanya simpan 1 barang termurah)
        full_df = full_df.sort_values(by=['nama_barang', 'harga_master_numeric']).drop_duplicates(subset=['nama_barang'], keep='first')
        
        # Kembalikan urutan berdasarkan persentase stok
        full_df['stok_sekarang'] = full_df['nama_barang'].map(total_stok)
        full_df['persentase'] = full_df['stok_sekarang'] / full_df['stok_minimum_safe']
        full_df = full_df.sort_values(by='persentase')
        
        for _, row in full_df.iterrows():
            stok = row['stok_sekarang']
            minimum = row['stok_minimum']
            pct = row['persentase']
            kat = row.get('kategori', '')
            status_flag = str(row.get('status', 'True')).upper() in ['TRUE', '1', 'YES', 'T']
            
            # Klasifikasi ulang status berdasarkan total stok gabungan
            status_text, color_hex, bg_color, text_color, icon, estimasi = classify_stock_status(stok, minimum, pct, kat, status=status_flag)
            bar_width = calculate_bar_width(stok, minimum)
            
            item_name = row['nama_barang']
            harga_m = row['harga_master_numeric']
            is_termurah = (harga_m == min_prices.get(item_name, -1) and harga_m != float('inf'))
            supplier = row.get('supplier', '')
            
            c1_html, c2_html, c3_html, c4_html = get_row_html(
                row['nama_barang'], row['kode_barang'], stok, row['satuan'], 
                minimum, bar_width, status_text, color_hex, bg_color, text_color, icon, estimasi,
                supplier=supplier, is_termurah=is_termurah, harga_master=harga_m if harga_m != float('inf') else 0.0
            )
            
            with st.container():
                c1, c2, c3, c4 = st.columns([1.5, 1.5, 1.2, 1.3])
                with c1: st.markdown(c1_html, unsafe_allow_html=True)
                with c2: st.markdown(c2_html, unsafe_allow_html=True)
                with c3: st.markdown(c3_html, unsafe_allow_html=True)
                with c4: st.markdown(c4_html, unsafe_allow_html=True)
                st.markdown("<hr style='margin: 0; padding: 0;'>", unsafe_allow_html=True)
