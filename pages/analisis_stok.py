import streamlit as st
import pandas as pd
import plotly.express as px
from data.sheets_repository import load_data
from services.report_service import filter_last_n_days, aggregate_trend_data

def show_analisis_stok():
    st.header("📈 Analisis & Laporan Stok")
    st.caption("Pantau statistik pergerakan barang, riwayat, dan grafik tren masuk/keluar.")
    
    master_df, transaksi_df = load_data()
    
    if len(transaksi_df) == 0:
        st.info("Belum ada data transaksi yang dicatat.")
        return
        
    try:
        transaksi_df['tanggal_dt'] = pd.to_datetime(transaksi_df['tanggal'])
    except Exception:
        import logging
        logging.getLogger(__name__).warning("Format tanggal di database transaksi belum terstandarisasi.")
        transaksi_df['tanggal_dt'] = pd.to_datetime('today')
    
    st.subheader("1. Laporan Detail Per Barang")
    brg_options = master_df['kode_barang'] + " - " + master_df['nama_barang']
    selected_brg = st.selectbox("Pilih Barang yang ingin dianalisis:", brg_options)
    
    kode_brg = selected_brg.split(" - ")[0]
    nama_brg = selected_brg.split(" - ")[1]
    
    item_master = master_df[master_df['kode_barang'] == kode_brg].iloc[0]
    satuan = item_master['satuan']
    
    df_trx = transaksi_df[transaksi_df['kode_barang'] == kode_brg].copy()
    
    with st.container(border=True):
        st.markdown(f"**Statistik Kumulatif: {nama_brg}**")
        c1, c2, c3, c4 = st.columns(4)
        
        total_trx = len(df_trx)
        total_masuk = df_trx[df_trx['jenis'] == 'Masuk']['jumlah'].sum() if total_trx > 0 else 0
        total_keluar = df_trx[df_trx['jenis'] == 'Keluar']['jumlah'].sum() if total_trx > 0 else 0
        
        with c1: st.metric("Total Transaksi", f"{total_trx} Kali")
        with c2: st.metric("Total Barang Masuk", f"{total_masuk} {satuan}")
        with c3: st.metric("Total Barang Keluar", f"{total_keluar} {satuan}")
        with c4: st.metric("Sisa Stok (Saat Ini)", f"{item_master['stok_sekarang']} {satuan}")
        
    st.markdown("---")
    
    col_t1, col_t2 = st.columns([3, 1])
    with col_t1:
        st.subheader("2. Riwayat & Grafik Transaksi")
    with col_t2:
        n_hari = st.selectbox("Rentang Waktu:", [7, 14, 30, 90, 365], index=2, format_func=lambda x: f"{x} Hari Terakhir")
        
    df_trx_filtered = filter_last_n_days(df_trx, n_hari)
    
    if len(df_trx_filtered) > 0:
        daily_trx = aggregate_trend_data(df_trx_filtered)
        
        fig = px.bar(
            daily_trx, 
            x='tanggal', 
            y='jumlah', 
            color='jenis',
            barmode='group',
            color_discrete_map={'Masuk': '#2ca02c', 'Keluar': '#d32f2f'},
            labels={'tanggal': 'Tanggal', 'jumlah': f'Volume ({satuan})', 'jenis': 'Jenis Transaksi'},
            title=f"Grafik Volume Transaksi (Masuk vs Keluar) - {n_hari} Hari Terakhir"
        )
        fig.update_layout(xaxis_title="", yaxis_title="Jumlah", legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info(f"Tidak ada aktivitas pergerakan stok untuk {nama_brg} dalam {n_hari} hari terakhir.")
        
    with st.expander(f"Tampilkan Tabel Riwayat ({n_hari} Hari Terakhir)", expanded=True):
        if 'tanggal_dt' in df_trx_filtered.columns:
            display_df = df_trx_filtered.drop(columns=['tanggal_dt']).sort_values(by='tanggal', ascending=False)
        else:
            display_df = df_trx_filtered.sort_values(by='tanggal', ascending=False)
        st.dataframe(display_df, use_container_width=True, hide_index=True)
