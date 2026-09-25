import streamlit as st
import pandas as pd
from data.sheets_repository import load_data
from services.stock_service import (
    classify_stock_status, 
    calculate_bar_width,
    filter_stock_by_status
)
from utils.formatting import get_header_html, get_row_html

def show_dashboard():
    st.header("📊 Dashboard Stok Gizi")
    
    master_df, _ = load_data()
    
    if master_df.empty:
        st.info("Belum ada data barang di Master Data.")
        return
        
    master_df['stok_minimum_safe'] = master_df['stok_minimum'].apply(lambda x: max(x, 1))
    master_df['persentase'] = master_df['stok_sekarang'] / master_df['stok_minimum_safe']
    
    krisis_df, mendekati_df, aman_df = filter_stock_by_status(master_df)
    
    # Scorecards
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        with st.container(border=True):
            st.markdown("🏢 **Total Barang**")
            st.markdown(f"<h2>{len(master_df)} <span style='font-size:16px'>SKU</span></h2>", unsafe_allow_html=True)
    with col2:
        with st.container(border=True):
            st.markdown("🚨 **Stok Krisis / Habis**")
            st.markdown(f"<h2 style='color:#d32f2f'>{len(krisis_df)} <span style='font-size:16px; opacity: 0.7;'>SKU</span></h2>", unsafe_allow_html=True)
    with col3:
        with st.container(border=True):
            st.markdown("⚠️ **Mendekati Minimum**")
            st.markdown(f"<h2 style='color:#fbc02d'>{len(mendekati_df)} <span style='font-size:16px; opacity: 0.7;'>SKU</span></h2>", unsafe_allow_html=True)
    with col4:
        with st.container(border=True):
            st.markdown("✅ **Stok Aman**")
            st.markdown(f"<h2 style='color:#388e3c'>{len(aman_df)} <span style='font-size:16px; opacity: 0.7;'>SKU</span></h2>", unsafe_allow_html=True)
            
    st.markdown("---")
    
    # --- DAFTAR SELURUH STOK BARANG ---
    full_df = pd.concat([krisis_df, mendekati_df, aman_df]).sort_values(by='persentase')
    
    col_title, col_search = st.columns([1, 1])
    with col_title:
        st.markdown(get_header_html(len(full_df)), unsafe_allow_html=True)
    with col_search:
        st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
        search_q = st.text_input("🔍 Cari Barang (Nama / SKU):", placeholder="Ketik nama atau kode barang...", label_visibility="collapsed")
        
    st.markdown("<br>", unsafe_allow_html=True)
        
    if search_q:
        full_df = full_df[
            full_df['nama_barang'].str.contains(search_q, case=False, na=False) | 
            full_df['kode_barang'].str.contains(search_q, case=False, na=False)
        ]
        
    if len(full_df) == 0:
        if search_q:
            st.info(f"Pencarian '{search_q}' tidak ditemukan.")
        else:
            st.success("✅ **Semua Stok Aman!** Tidak ada barang yang tercatat.")
    else:
        h_col1, h_col2, h_col3 = st.columns([2, 2, 1.5])
        with h_col1: st.markdown("<span style='color: gray; font-size: 0.85rem; font-weight: 700;'>DETAIL BARANG & SKU</span>", unsafe_allow_html=True)
        with h_col2: st.markdown("<span style='color: gray; font-size: 0.85rem; font-weight: 700;'>LEVEL STOK SAAT INI</span>", unsafe_allow_html=True)
        with h_col3: st.markdown("<span style='color: gray; font-size: 0.85rem; font-weight: 700;'>STATUS & ESTIMASI</span>", unsafe_allow_html=True)
        st.markdown("<hr style='margin-top: 5px; margin-bottom: 15px;'>", unsafe_allow_html=True)
        
        for _, row in full_df.iterrows():
            stok = row['stok_sekarang']
            minimum = row['stok_minimum']
            pct = row['persentase']
            
            status_text, color_hex, bg_color, text_color, icon, estimasi = classify_stock_status(stok, minimum, pct)
            bar_width = calculate_bar_width(stok, minimum)
            
            c1_html, c2_html, c3_html = get_row_html(
                row['nama_barang'], row['kode_barang'], stok, row['satuan'], 
                minimum, bar_width, status_text, color_hex, bg_color, text_color, icon, estimasi
            )
            
            with st.container():
                c1, c2, c3 = st.columns([2, 2, 1.5])
                with c1: st.markdown(c1_html, unsafe_allow_html=True)
                with c2: st.markdown(c2_html, unsafe_allow_html=True)
                with c3: st.markdown(c3_html, unsafe_allow_html=True)
                st.markdown("<hr style='margin: 0; padding: 0;'>", unsafe_allow_html=True)
