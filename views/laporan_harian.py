import streamlit as st
import pandas as pd
import datetime
from data.sheets_repository import (
    get_sheet_data, SHEET_STOK_MASUK, 
    SHEET_PENGELUARAN_PASIEN, SHEET_PENGELUARAN_DOKTER, SHEET_PENGELUARAN_MANAJEMEN
)

def show_laporan_harian():
    st.header("📅 Laporan Harian dan Rekapan Pengeluaran")
    st.caption("Lihat seluruh rincian transaksi pengeluaran harian yang telah direkap.")
    
    col_d, col_e = st.columns([3, 1])
    with col_d:
        today = datetime.date.today()
        date_range = st.date_input("📅 Rentang Waktu Laporan:", value=(today, today))
        
    if len(date_range) != 2:
        st.warning("Silakan lengkapi rentang tanggal (Mulai - Akhir) untuk melihat laporan.")
        return
        
    start_date, end_date = date_range
    
    st.markdown("---")
    
    # Load all sheets
    df_masuk = get_sheet_data(SHEET_STOK_MASUK)
    df_pasien = get_sheet_data(SHEET_PENGELUARAN_PASIEN)
    df_dokter = get_sheet_data(SHEET_PENGELUARAN_DOKTER)
    df_manajemen = get_sheet_data(SHEET_PENGELUARAN_MANAJEMEN)
    
    def filter_by_date(df):
        if df.empty or 'tanggal' not in df.columns:
            return pd.DataFrame()
        df_copy = df.copy()
        df_copy['date_only'] = pd.to_datetime(df_copy['tanggal'], errors='coerce').dt.date
        mask = (df_copy['date_only'] >= start_date) & (df_copy['date_only'] <= end_date)
        filtered = df_copy[mask].copy()
        if not filtered.empty:
            filtered = filtered.drop(columns=['date_only'])
        return filtered

    f_masuk = filter_by_date(df_masuk)
    f_pasien = filter_by_date(df_pasien)
    f_dokter = filter_by_date(df_dokter)
    f_manajemen = filter_by_date(df_manajemen)
    
    # Combine all pengeluaran
    if not f_pasien.empty: f_pasien['Sumber'] = 'Pasien'
    if not f_dokter.empty: f_dokter['Sumber'] = 'Dokter'
    if not f_manajemen.empty: f_manajemen['Sumber'] = 'Manajemen'
    
    dfs_keluar = []
    if not f_pasien.empty: dfs_keluar.append(f_pasien)
    if not f_dokter.empty: dfs_keluar.append(f_dokter)
    if not f_manajemen.empty: dfs_keluar.append(f_manajemen)
    
    f_keluar = pd.concat(dfs_keluar, ignore_index=True) if dfs_keluar else pd.DataFrame()
    
    # Filter by Shift & Supplier
    shift_options = ["Pagi (07:00-15:00)", "Siang (15:00-22:00)", "Malam (22:00-07:00)", "1 Hari"]
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        selected_shifts = st.multiselect("⏳ Filter Shift:", shift_options, default=shift_options, placeholder="Pilih shift...")
    
    with col_f2:
        available_sups = ["Pak Urip", "Wahana", "Ari Snack", "Supplier Yulia", "Roti Mayestik"]
        if not df_masuk.empty:
            df_masuk['supplier'] = df_masuk['keterangan'].apply(lambda x: x.split('| Supplier:')[1].split('|')[0].strip() if '| Supplier:' in str(x) else 'Unknown')
            extra_sups = [s for s in df_masuk['supplier'].dropna().unique() if s not in available_sups and str(s).strip() != '']
            available_sups.extend(extra_sups)
            
        sup_filter = st.multiselect("🏢 Filter Supplier:", available_sups, placeholder="Semua Supplier")
    
    if selected_shifts:
        if not f_keluar.empty and 'shift' in f_keluar.columns:
            f_keluar = f_keluar[f_keluar['shift'].isin(selected_shifts)]
    else:
        if not f_keluar.empty:
            f_keluar = f_keluar.iloc[0:0]
            
    if sup_filter and not f_masuk.empty:
        if 'supplier' not in f_masuk.columns:
            f_masuk['supplier'] = f_masuk['keterangan'].apply(lambda x: x.split('| Supplier:')[1].split('|')[0].strip() if '| Supplier:' in str(x) else 'Unknown')
        f_masuk = f_masuk[f_masuk['supplier'].isin(sup_filter)]
            
    st.markdown("<br>", unsafe_allow_html=True)
    
    # CALCULATE METRICS FOR PENGELUARAN
    t_real = f_keluar['total_harga'].sum() if not f_keluar.empty and 'total_harga' in f_keluar.columns else 0
    t_pasien = f_keluar[f_keluar['Sumber'] == 'Pasien']['total_harga'].sum() if not f_keluar.empty and 'total_harga' in f_keluar.columns else 0
    t_dokter = f_keluar[f_keluar['Sumber'] == 'Dokter']['total_harga'].sum() if not f_keluar.empty and 'total_harga' in f_keluar.columns else 0
    t_manajemen = f_keluar[f_keluar['Sumber'] == 'Manajemen']['total_harga'].sum() if not f_keluar.empty and 'total_harga' in f_keluar.columns else 0
    
    # Calculate Pasien breakdown
    t_kelas_1 = 0; qty_k1 = 0
    t_kelas_2 = 0; qty_k2 = 0
    t_kelas_3 = 0; qty_k3 = 0
    t_vip = 0; qty_vip = 0
    total_pasien_qty = 0
    total_dokter_qty = 0
    
    if not f_keluar.empty and 'kategori' in f_keluar.columns:
        df_pas = f_keluar[f_keluar['Sumber'] == 'Pasien'].copy()
        if not df_pas.empty:
            t_kelas_1 = df_pas[df_pas['kategori'] == 'Kelas 1']['total_harga'].sum()
            t_kelas_2 = df_pas[df_pas['kategori'] == 'Kelas 2']['total_harga'].sum()
            t_kelas_3 = df_pas[df_pas['kategori'] == 'Kelas 3']['total_harga'].sum()
            t_vip = df_pas[df_pas['kategori'] == 'VIP']['total_harga'].sum()
            
            if 'jumlah_pasien' in df_pas.columns:
                df_pas['jumlah_pasien'] = pd.to_numeric(df_pas['jumlah_pasien'], errors='coerce').fillna(0)
                unique_pasien = df_pas.groupby(['tanggal', 'shift', 'kategori'])['jumlah_pasien'].first().reset_index()
                
                qty_k1 = unique_pasien[unique_pasien['kategori'] == 'Kelas 1']['jumlah_pasien'].sum()
                qty_k2 = unique_pasien[unique_pasien['kategori'] == 'Kelas 2']['jumlah_pasien'].sum()
                qty_k3 = unique_pasien[unique_pasien['kategori'] == 'Kelas 3']['jumlah_pasien'].sum()
                qty_vip = unique_pasien[unique_pasien['kategori'] == 'VIP']['jumlah_pasien'].sum()
                
                total_pasien_qty = qty_k1 + qty_k2 + qty_k3 + qty_vip
                
        if 'kategori_freetext' in f_keluar.columns:
            df_dok = f_keluar[f_keluar['Sumber'] == 'Dokter'].copy()
            if not df_dok.empty:
                unique_dokters = df_dok.groupby(['tanggal', 'shift', 'kategori_freetext']).size().reset_index()
                total_dokter_qty = len(unique_dokters)
    
    total_masuk_qty = f_masuk['qty'].sum() if not f_masuk.empty and 'qty' in f_masuk.columns else 0
    total_masuk_rp = f_masuk['total_harga'].sum() if not f_masuk.empty and 'total_harga' in f_masuk.columns else 0
    
    with st.container(border=True):
        st.markdown("##### 📥 Rangkuman Belanja / Masuk")
        m1, m2 = st.columns(2)
        m1.metric("Total Qty Masuk", f"{total_masuk_qty:,.0f} Qty")
        m2.metric("Total Pembelian (Rp)", f"Rp {total_masuk_rp:,.0f}")
        
    st.markdown("<br>", unsafe_allow_html=True)
    
    with st.container(border=True):
        st.markdown("##### 📤 Rangkuman Pengeluaran")
        c1, c2 = st.columns(2)
        c1.metric("Total Keseluruhan", f"Rp {t_real:,.0f}")
        c2.metric(f"Total Pasien ({total_pasien_qty:,.0f} org)", f"Rp {t_pasien:,.0f}")
        
        st.markdown("<br>", unsafe_allow_html=True)
        c3, c4 = st.columns(2)
        c3.metric(f"Dokter ({total_dokter_qty:,.0f} org)", f"Rp {t_dokter:,.0f}")
        c4.metric("Manajemen", f"Rp {t_manajemen:,.0f}")
        
        st.divider()
        st.caption("Rincian Pengeluaran Pasien:")
        p1, p2 = st.columns(2)
        p1.metric(f"Kelas 1 ({qty_k1:,.0f} org)", f"Rp {t_kelas_1:,.0f}")
        p2.metric(f"Kelas 2 ({qty_k2:,.0f} org)", f"Rp {t_kelas_2:,.0f}")
        
        st.markdown("<br>", unsafe_allow_html=True)
        p3, p4 = st.columns(2)
        p3.metric(f"Kelas 3 ({qty_k3:,.0f} org)", f"Rp {t_kelas_3:,.0f}")
        p4.metric(f"VIP ({qty_vip:,.0f} org)", f"Rp {t_vip:,.0f}")
        
    st.markdown("<br>", unsafe_allow_html=True)
    
    # GROUPBY PER TANGGAL & SHIFT (PIVOT)
    tab1, tab2 = st.tabs(["📤 Tabel Rekapan Pengeluaran", "📥 Tabel Pembelian / Supplier"])
    
    with tab1:
        st.subheader(f"Tabel Rekapan Pengeluaran ({len(f_keluar)} Transaksi Mentah)")
        if f_keluar.empty:
            st.info(f"Tidak ada data pengeluaran pada periode {start_date.strftime('%d %b %Y')} s/d {end_date.strftime('%d %b %Y')}.")
        else:
            # Extract date from datetime string
            f_keluar['Tanggal_Only'] = pd.to_datetime(f_keluar['tanggal'], errors='coerce').dt.strftime('%Y-%m-%d')
            
            # Create detailed group for Pasien classes
            def get_grup(row):
                if row['Sumber'] == 'Pasien':
                    kat = str(row.get('kategori', '')).strip()
                    return f"Pasien {kat}" if kat else "Pasien"
                return row['Sumber']
                
            f_keluar['Grup'] = f_keluar.apply(get_grup, axis=1)
            
            pivot_df = pd.pivot_table(
                f_keluar,
                values=['qty', 'total_harga'],
                index=['Tanggal_Only', 'shift'],
                columns='Grup',
                aggfunc='sum',
                fill_value=0
            )
            
            # Flatten MultiIndex columns: e.g. ('qty', 'Dokter') -> 'Qty Dokter'
            pivot_df.columns = [f"{'Rp' if col[0] == 'total_harga' else 'Qty'} {col[1]}" for col in pivot_df.columns]
            
            pivot_df = pivot_df.reset_index()
            pivot_df = pivot_df.rename(columns={'Tanggal_Only': 'Tanggal', 'shift': 'Shift'})
            
            # Calculate Grand Totals
            qty_cols = [c for c in pivot_df.columns if c.startswith('Qty ')]
            rp_cols = [c for c in pivot_df.columns if c.startswith('Rp ')]
            
            if qty_cols:
                pivot_df['Total Qty (Semua)'] = pivot_df[qty_cols].sum(axis=1)
                
            pivot_df['Total Pengeluaran'] = pivot_df[rp_cols].sum(axis=1) if rp_cols else 0
            
            # Sort before converting to string so it sorts correctly
            display_df = pivot_df.sort_values(['Tanggal', 'Shift'], ascending=[False, True]).copy()
            
            # Format as string with thousands separators for Rp columns
            for col in rp_cols + ['Total Pengeluaran']:
                display_df[col] = display_df[col].apply(lambda x: f"{x:,.0f}")
            
            st.dataframe(display_df, use_container_width=True, hide_index=True)
            
            csv_data = pivot_df.sort_values(['Tanggal', 'Shift'], ascending=[False, True]).to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Export ke CSV (Pengeluaran)",
                data=csv_data,
                file_name=f"Rekapan_Pengeluaran_{start_date}_sd_{end_date}.csv",
                mime="text/csv",
            )
            
    with tab2:
        st.subheader(f"Tabel Pembelian dari Supplier ({len(f_masuk)} Transaksi)")
        if f_masuk.empty:
            st.info(f"Tidak ada data pembelian/stok masuk pada periode {start_date.strftime('%d %b %Y')} s/d {end_date.strftime('%d %b %Y')} untuk supplier yang difilter.")
        else:
            if 'supplier' not in f_masuk.columns:
                f_masuk['supplier'] = f_masuk['keterangan'].apply(lambda x: x.split('| Supplier:')[1].split('|')[0].strip() if '| Supplier:' in str(x) else 'Unknown')
                
            disp_masuk = f_masuk[['tanggal', 'shift', 'supplier', 'nama_barang', 'qty', 'harga_master', 'harga_real', 'total_harga', 'keterangan']].copy()
            disp_masuk = disp_masuk.sort_values(by=['tanggal', 'shift'], ascending=[False, True])
            
            # Formatting
            format_cols = ['harga_master', 'harga_real', 'total_harga']
            for c in format_cols:
                disp_masuk[c] = disp_masuk[c].apply(lambda x: f"Rp {pd.to_numeric(x, errors='coerce'):,.0f}")
                
            st.dataframe(disp_masuk, use_container_width=True, hide_index=True)
            
            # CSV export
            csv_masuk = disp_masuk.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Export ke CSV (Pembelian Supplier)",
                data=csv_masuk,
                file_name=f"Rekapan_Pembelian_Supplier_{start_date}_sd_{end_date}.csv",
                mime="text/csv",
            )
