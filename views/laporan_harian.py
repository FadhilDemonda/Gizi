import streamlit as st
import pandas as pd
from data.sheets_repository import load_data
from services.report_service import get_daily_transactions, aggregate_daily_summary

def show_laporan_harian():
    st.header("📅 Laporan Harian")
    st.caption("Lihat rangkuman aktivitas pergerakan stok dan rincian transaksi per hari.")
    
    master_df, transaksi_df = load_data()
    
    if len(transaksi_df) == 0:
        st.info("Belum ada data transaksi yang dicatat di database.")
        return
        
    try:
        transaksi_df['tanggal_dt'] = pd.to_datetime(transaksi_df['tanggal'])
    except Exception:
        import logging
        logging.getLogger(__name__).warning("Format tanggal di database transaksi belum terstandarisasi.")
        transaksi_df['tanggal_dt'] = pd.to_datetime('today')
        
    min_date = transaksi_df['tanggal_dt'].min().date()
    max_date = transaksi_df['tanggal_dt'].max().date()
    
    col_d, col_e = st.columns([3, 1])
    with col_d:
        selected_date = st.date_input("Pilih Tanggal Laporan:", value=max_date, min_value=min_date, max_value=max_date)
        
    selected_date_str = selected_date.strftime('%Y-%m-%d')
    df_daily = get_daily_transactions(transaksi_df, selected_date_str)
    
    with col_e:
        st.markdown("<br>", unsafe_allow_html=True) 
        if len(df_daily) > 0:
            csv_daily = df_daily.drop(columns=['tanggal_dt']).to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Export (CSV)",
                data=csv_daily,
                file_name=f"Laporan_Harian_{selected_date_str}.csv",
                mime="text/csv",
                use_container_width=True
            )
            
    if len(df_daily) == 0:
        st.warning(f"Tidak ada aktivitas keluar/masuk barang pada tanggal {selected_date_str}.")
        return
        
    st.markdown("---")
    
    st.subheader("📊 Summary Pergerakan per Barang")
    st.caption("Rangkuman akumulasi barang masuk dan keluar pada hari ini.")
    
    summary_df = aggregate_daily_summary(df_daily, master_df)
    st.dataframe(summary_df, use_container_width=True, hide_index=True)
    
    st.markdown("---")
    
    st.subheader("📝 Detail Seluruh Transaksi Harian")
    
    df_merge = pd.merge(df_daily, master_df[['kode_barang', 'nama_barang', 'satuan']], on='kode_barang', how='left')
    display_trx = df_merge.drop(columns=['tanggal_dt'])
    
    cols = display_trx.columns.tolist()
    if 'nama_barang' in cols:
        cols.remove('nama_barang')
        idx = cols.index('kode_barang') + 1
        cols.insert(idx, 'nama_barang')
    display_trx = display_trx[cols]
    
    st.dataframe(display_trx, use_container_width=True, hide_index=True)
