import streamlit as st
import pandas as pd
import datetime
from data.sheets_repository import (
    get_sheet_data, SHEET_MASTER, SHEET_STOK_MASUK, 
    SHEET_PENGELUARAN_PASIEN, SHEET_PENGELUARAN_DOKTER, SHEET_PENGELUARAN_MANAJEMEN
)
from views.transaksi import extract_unique_suppliers, match_supplier

def format_qty(val) -> str:
    """
    Format kuantitas agar mendukung angka desimal hingga 0.05 tanpa kehilangan presisi,
    sekaligus menghilangkan nol trailing untuk angka bulat.
    Contoh:
        0.05 -> '0.05'
        0.07 -> '0.07'
        7.8  -> '7.8'
        10.0 -> '10'
        1250.25 -> '1,250.25'
    """
    try:
        if val is None or pd.isna(val):
            return "0"
        v = round(float(val), 2)
        s = f"{v:,.2f}"
        if "." in s:
            s = s.rstrip("0").rstrip(".")
        return s if s else "0"
    except Exception:
        return "0"

def render_rekapan_pasien(df_pasien_in, start_date, end_date):
    st.subheader(f"🛏️ Tabel Rekapan Pengeluaran Pasien ({len(df_pasien_in)} Transaksi Mentah)")
    if df_pasien_in.empty:
        st.info(f"Tidak ada data pengeluaran pasien pada periode {start_date.strftime('%d %b %Y')} s/d {end_date.strftime('%d %b %Y')}.")
        return
        
    df_p = df_pasien_in.copy()
    df_p['qty'] = pd.to_numeric(df_p['qty'], errors='coerce').fillna(0)
    df_p['total_harga'] = pd.to_numeric(df_p['total_harga'], errors='coerce').fillna(0)
    if 'jumlah_pasien' in df_p.columns:
        df_p['jumlah_pasien'] = pd.to_numeric(df_p['jumlah_pasien'], errors='coerce').fillna(0)
    else:
        df_p['jumlah_pasien'] = 0
        
    df_p['Tanggal'] = pd.to_datetime(df_p['tanggal'], errors='coerce').dt.strftime('%Y-%m-%d')
    df_p['Shift'] = df_p['shift'].fillna('-')
    df_p['Kategori'] = df_p['kategori'].fillna('-').astype(str).str.strip()
    
    # 1. Tabel Utama: Rekapan per Tanggal, Shift, Kategori
    grouped_rows = []
    for (tgl, shf, kat), grp in df_p.groupby(['Tanggal', 'Shift', 'Kategori'], sort=False):
        jml_pas = grp['jumlah_pasien'].iloc[0] if 'jumlah_pasien' in grp.columns else 0
        mc_brg = grp['nama_barang'].nunique()
        q_sum = grp['qty'].sum()
        rp_sum = grp['total_harga'].sum()
        cost_per_p = (rp_sum / jml_pas) if jml_pas > 0 else 0
        grouped_rows.append({
            "Tanggal": tgl,
            "Shift": shf,
            "Kategori Kelas": kat,
            "Jml Pasien": f"{jml_pas:,.0f}",
            "Macam Bahan": f"{mc_brg} Macam",
            "Total Qty": format_qty(q_sum),
            "Total Biaya": f"Rp {rp_sum:,.0f}",
            "Biaya / Pasien": f"Rp {cost_per_p:,.0f}",
            "_sort_tgl": tgl
        })
    rekap_df = pd.DataFrame(grouped_rows).sort_values(by=['_sort_tgl', 'Shift'], ascending=[False, True]).drop(columns=['_sort_tgl'])
    st.dataframe(rekap_df, use_container_width=True, hide_index=True)
    
    # 2. Rekapan Pemakaian per Bahan (Dropdown 1)
    with st.expander("🥦 Rekapan Pemakaian per Bahan Makanan (Total Qty & Biaya)", expanded=False):
        brg_rows = []
        for brg, grp in df_p.groupby('nama_barang', sort=False):
            b_qty = grp['qty'].sum()
            b_rp = grp['total_harga'].sum()
            avg_p = (b_rp / b_qty) if b_qty > 0 else 0
            brg_rows.append({
                "Nama Bahan": brg,
                "Total Qty": format_qty(b_qty),
                "Harga Satuan Rata-rata": f"Rp {avg_p:,.0f}",
                "Total Biaya": f"Rp {b_rp:,.0f}",
                "_raw_rp": b_rp
            })
        brg_df = pd.DataFrame(brg_rows).sort_values(by='_raw_rp', ascending=False).drop(columns=['_raw_rp'])
        st.dataframe(brg_df, use_container_width=True, hide_index=True)
        
    # Detail Mentah (Dropdown 2)
    with st.expander("🔍 Lihat Rincian Semua Item Pengeluaran Pasien (Data Mentah)", expanded=False):
        raw_cols = ['tanggal', 'shift', 'kategori', 'supplier', 'nama_barang', 'qty', 'harga_real', 'total_harga', 'jumlah_pasien', 'keterangan']
        avail_raw = [c for c in raw_cols if c in df_p.columns]
        raw_show = df_p[avail_raw].copy().sort_values(by=['tanggal', 'shift'], ascending=[False, True])
        for c in ['harga_real', 'total_harga']:
            if c in raw_show.columns:
                raw_show[c] = raw_show[c].apply(lambda x: f"Rp {x:,.0f}")
        st.dataframe(raw_show, use_container_width=True, hide_index=True)
        
    csv_bytes = df_p.to_csv(index=False).encode('utf-8')
    st.download_button(
        "📥 Export CSV (Rekapan Pasien)",
        data=csv_bytes,
        file_name=f"Rekap_Pasien_{start_date}_sd_{end_date}.csv",
        mime="text/csv"
    )

def render_rekapan_dokter(df_dokter_in, start_date, end_date):
    st.subheader(f"🩺 Tabel Rekapan Pengeluaran Dokter ({len(df_dokter_in)} Transaksi Mentah)")
    if df_dokter_in.empty:
        st.info(f"Tidak ada data pengeluaran dokter pada periode {start_date.strftime('%d %b %Y')} s/d {end_date.strftime('%d %b %Y')}.")
        return
        
    df_d = df_dokter_in.copy()
    df_d['qty'] = pd.to_numeric(df_d['qty'], errors='coerce').fillna(0)
    df_d['total_harga'] = pd.to_numeric(df_d['total_harga'], errors='coerce').fillna(0)
    df_d['Tanggal'] = pd.to_datetime(df_d['tanggal'], errors='coerce').dt.strftime('%Y-%m-%d')
    df_d['Shift'] = df_d['shift'].fillna('-')
    df_d['Kategori'] = df_d['kategori'].fillna('-').astype(str).str.strip()
    df_d['Nama Dokter'] = df_d['kategori_freetext'].fillna('-').astype(str).str.strip()
    
    # 1. Tabel Utama: Rekapan per Tanggal, Shift, Kategori, Dokter
    grouped_rows = []
    for (tgl, shf, kat, dok), grp in df_d.groupby(['Tanggal', 'Shift', 'Kategori', 'Nama Dokter'], sort=False):
        mc_brg = grp['nama_barang'].nunique()
        q_sum = grp['qty'].sum()
        rp_sum = grp['total_harga'].sum()
        rincian_snack = ", ".join([f"{r.nama_barang} ({format_qty(r.qty)})" for r in grp.itertuples()])
        grouped_rows.append({
            "Tanggal": tgl,
            "Shift": shf,
            "Kategori": kat,
            "Nama Dokter": dok,
            "Macam Snack": f"{mc_brg} Macam",
            "Total Qty": format_qty(q_sum),
            "Total Biaya": f"Rp {rp_sum:,.0f}",
            "Rincian Menu Snack": rincian_snack,
            "_sort_tgl": tgl
        })
    rekap_df = pd.DataFrame(grouped_rows).sort_values(by=['_sort_tgl', 'Shift'], ascending=[False, True]).drop(columns=['_sort_tgl'])
    st.dataframe(rekap_df, use_container_width=True, hide_index=True)
    
    # 2. Rekapan Per Barang (Dropdown 1)
    with st.expander("☕ Rekapan Konsumsi per Item Barang (Total Qty & Biaya)", expanded=False):
        brg_rows = []
        for brg, grp in df_d.groupby('nama_barang', sort=False):
            b_qty = grp['qty'].sum()
            b_rp = grp['total_harga'].sum()
            avg_p = (b_rp / b_qty) if b_qty > 0 else 0
            brg_rows.append({
                "Nama Snack / Makanan": brg,
                "Total Qty": format_qty(b_qty),
                "Harga Satuan Rata-rata": f"Rp {avg_p:,.0f}",
                "Total Biaya": f"Rp {b_rp:,.0f}",
                "_raw_rp": b_rp
            })
        brg_df = pd.DataFrame(brg_rows).sort_values(by='_raw_rp', ascending=False).drop(columns=['_raw_rp'])
        st.dataframe(brg_df, use_container_width=True, hide_index=True)
        
    # Detail Mentah (Dropdown 2)
    with st.expander("🔍 Lihat Rincian Semua Item Pengeluaran Dokter (Data Mentah)", expanded=False):
        raw_cols = ['tanggal', 'shift', 'kategori', 'kategori_freetext', 'supplier', 'nama_barang', 'qty', 'harga_real', 'total_harga', 'keterangan']
        avail_raw = [c for c in raw_cols if c in df_d.columns]
        raw_show = df_d[avail_raw].copy().sort_values(by=['tanggal', 'shift'], ascending=[False, True])
        for c in ['harga_real', 'total_harga']:
            if c in raw_show.columns:
                raw_show[c] = raw_show[c].apply(lambda x: f"Rp {x:,.0f}")
        st.dataframe(raw_show, use_container_width=True, hide_index=True)
        
    csv_bytes = df_d.to_csv(index=False).encode('utf-8')
    st.download_button(
        "📥 Export CSV (Rekapan Dokter)",
        data=csv_bytes,
        file_name=f"Rekap_Dokter_{start_date}_sd_{end_date}.csv",
        mime="text/csv"
    )

def render_rekapan_manajemen(df_manajemen_in, start_date, end_date):
    st.subheader(f"💼 Tabel Rekapan Pengeluaran Manajemen ({len(df_manajemen_in)} Transaksi Mentah)")
    if df_manajemen_in.empty:
        st.info(f"Tidak ada data pengeluaran manajemen pada periode {start_date.strftime('%d %b %Y')} s/d {end_date.strftime('%d %b %Y')}.")
        return
        
    df_m = df_manajemen_in.copy()
    df_m['qty'] = pd.to_numeric(df_m['qty'], errors='coerce').fillna(0)
    df_m['total_harga'] = pd.to_numeric(df_m['total_harga'], errors='coerce').fillna(0)
    df_m['Tanggal'] = pd.to_datetime(df_m['tanggal'], errors='coerce').dt.strftime('%Y-%m-%d')
    df_m['Shift'] = df_m['shift'].fillna('-')
    df_m['Kategori'] = df_m['kategori'].fillna('-').astype(str).str.strip()
    df_m['Keterangan'] = df_m['keterangan'].fillna('-').astype(str).str.strip()
    
    # 1. Tabel Utama: Rekapan per Tanggal, Shift, Kategori, Kegiatan
    grouped_rows = []
    for (tgl, shf, kat, ket), grp in df_m.groupby(['Tanggal', 'Shift', 'Kategori', 'Keterangan'], sort=False):
        mc_brg = grp['nama_barang'].nunique()
        q_sum = grp['qty'].sum()
        rp_sum = grp['total_harga'].sum()
        rincian_item = ", ".join([f"{r.nama_barang} ({format_qty(r.qty)})" for r in grp.itertuples()])
        grouped_rows.append({
            "Tanggal": tgl,
            "Shift": shf,
            "Kategori": kat,
            "Kegiatan / Keterangan": ket,
            "Macam Konsumsi": f"{mc_brg} Macam",
            "Total Qty": format_qty(q_sum),
            "Total Biaya": f"Rp {rp_sum:,.0f}",
            "Rincian Konsumsi": rincian_item,
            "_sort_tgl": tgl
        })
    rekap_df = pd.DataFrame(grouped_rows).sort_values(by=['_sort_tgl', 'Shift'], ascending=[False, True]).drop(columns=['_sort_tgl'])
    st.dataframe(rekap_df, use_container_width=True, hide_index=True)
    
    # 2. Rekapan Per Barang (Dropdown 1)
    with st.expander("🍱 Rekapan Konsumsi per Item Barang (Total Qty & Biaya)", expanded=False):
        brg_rows = []
        for brg, grp in df_m.groupby('nama_barang', sort=False):
            b_qty = grp['qty'].sum()
            b_rp = grp['total_harga'].sum()
            avg_p = (b_rp / b_qty) if b_qty > 0 else 0
            brg_rows.append({
                "Nama Konsumsi / Barang": brg,
                "Total Qty": format_qty(b_qty),
                "Harga Satuan Rata-rata": f"Rp {avg_p:,.0f}",
                "Total Biaya": f"Rp {b_rp:,.0f}",
                "_raw_rp": b_rp
            })
        brg_df = pd.DataFrame(brg_rows).sort_values(by='_raw_rp', ascending=False).drop(columns=['_raw_rp'])
        st.dataframe(brg_df, use_container_width=True, hide_index=True)
        
    # Detail Mentah (Dropdown 2)
    with st.expander("🔍 Lihat Rincian Semua Item Pengeluaran Manajemen (Data Mentah)", expanded=False):
        raw_cols = ['tanggal', 'shift', 'kategori', 'supplier', 'nama_barang', 'qty', 'harga_real', 'total_harga', 'keterangan']
        avail_raw = [c for c in raw_cols if c in df_m.columns]
        raw_show = df_m[avail_raw].copy().sort_values(by=['tanggal', 'shift'], ascending=[False, True])
        for c in ['harga_real', 'total_harga']:
            if c in raw_show.columns:
                raw_show[c] = raw_show[c].apply(lambda x: f"Rp {x:,.0f}")
        st.dataframe(raw_show, use_container_width=True, hide_index=True)
        
    csv_bytes = df_m.to_csv(index=False).encode('utf-8')
    st.download_button(
        "📥 Export CSV (Rekapan Manajemen)",
        data=csv_bytes,
        file_name=f"Rekap_Manajemen_{start_date}_sd_{end_date}.csv",
        mime="text/csv"
    )

def filter_df_by_suppliers(df, target_suppliers):
    if df.empty or not target_suppliers:
        return df
    def check_row_sup(row):
        val = row.get('supplier')
        if (pd.isna(val) or str(val).strip() in ['', 'Unknown', '-', 'nan', 'None']) and 'keterangan' in row and '| Supplier:' in str(row.get('keterangan', '')):
            val = str(row['keterangan']).split('| Supplier:')[1].split('|')[0].strip()
        if not val or pd.isna(val):
            return False
        val_str = str(val).strip().lower()
        val_parts = [p.strip().lower() for p in val_str.split(';')]
        for target in target_suppliers:
            t_clean = str(target).strip().lower()
            if t_clean in val_parts or t_clean == val_str:
                return True
        return False
        
    return df[df.apply(check_row_sup, axis=1)]

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
    
    # Tag sources
    if not f_pasien.empty: f_pasien['Sumber'] = 'Pasien'
    if not f_dokter.empty: f_dokter['Sumber'] = 'Dokter'
    if not f_manajemen.empty: f_manajemen['Sumber'] = 'Manajemen'

    # Filter by Shift & Supplier
    shift_options = ["Pagi (07:00-15:00)", "Siang (15:00-22:00)", "Malam (22:00-07:00)", "1 Hari"]
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        selected_shifts = st.multiselect("⏳ Filter Shift:", shift_options, default=shift_options, placeholder="Pilih shift...")
    
    with col_f2:
        master_df = get_sheet_data(SHEET_MASTER)
        all_dfs_for_sup = [master_df, df_masuk, df_pasien, df_dokter, df_manajemen]
        supp_list = extract_unique_suppliers(pd.concat([d for d in all_dfs_for_sup if not d.empty and isinstance(d, pd.DataFrame)], ignore_index=True))
        available_sups = supp_list if supp_list else ["Pak Urip", "Wahana", "Ari Snack", "Bu Yunia", "Roti Mayestik"]
        sup_filter = st.multiselect("🏢 Filter Supplier:", available_sups, placeholder="Semua Supplier")
    
    if selected_shifts:
        if not f_pasien.empty and 'shift' in f_pasien.columns:
            f_pasien = f_pasien[f_pasien['shift'].isin(selected_shifts)]
        if not f_dokter.empty and 'shift' in f_dokter.columns:
            f_dokter = f_dokter[f_dokter['shift'].isin(selected_shifts)]
        if not f_manajemen.empty and 'shift' in f_manajemen.columns:
            f_manajemen = f_manajemen[f_manajemen['shift'].isin(selected_shifts)]
        if not f_masuk.empty and 'shift' in f_masuk.columns:
            shift_prefixes = [s.split()[0].lower() for s in selected_shifts]
            def match_shift(val):
                val_str = str(val).lower()
                for p in shift_prefixes:
                    if p in val_str:
                        return True
                    if p in ['malam', 'siang'] and 'sore' in val_str:
                        return True
                return False
            f_masuk = f_masuk[f_masuk['shift'].apply(match_shift)]
    else:
        if not f_pasien.empty:
            f_pasien = f_pasien.iloc[0:0]
        if not f_dokter.empty:
            f_dokter = f_dokter.iloc[0:0]
        if not f_manajemen.empty:
            f_manajemen = f_manajemen.iloc[0:0]
        if not f_masuk.empty:
            f_masuk = f_masuk.iloc[0:0]
            
    if sup_filter:
        f_pasien = filter_df_by_suppliers(f_pasien, sup_filter)
        f_dokter = filter_df_by_suppliers(f_dokter, sup_filter)
        f_manajemen = filter_df_by_suppliers(f_manajemen, sup_filter)
        f_masuk = filter_df_by_suppliers(f_masuk, sup_filter)
        
    dfs_keluar = []
    if not f_pasien.empty: dfs_keluar.append(f_pasien)
    if not f_dokter.empty: dfs_keluar.append(f_dokter)
    if not f_manajemen.empty: dfs_keluar.append(f_manajemen)
    f_keluar = pd.concat(dfs_keluar, ignore_index=True) if dfs_keluar else pd.DataFrame()
            
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
    
    efisiensi_belanja = 0
    if not f_masuk.empty:
        df_masuk_eff = f_masuk.copy()
        df_masuk_eff['qty_n'] = pd.to_numeric(df_masuk_eff['qty'], errors='coerce').fillna(0)
        df_masuk_eff['hm_n'] = pd.to_numeric(df_masuk_eff['harga_master'], errors='coerce').fillna(0)
        df_masuk_eff['hr_n'] = pd.to_numeric(df_masuk_eff['harga_real'], errors='coerce').fillna(0)
        efisiensi_belanja = sum((df_masuk_eff['hm_n'] - df_masuk_eff['hr_n']) * df_masuk_eff['qty_n'])
        
    with st.container(border=True):
        st.markdown('<span class="card-belanja-marker"></span>', unsafe_allow_html=True)
        st.markdown("##### 📥 Rangkuman Belanja / Masuk")
        m1, m2 = st.columns(2)
        m1.metric("Total Qty Masuk", f"{format_qty(total_masuk_qty)} Qty")
        m2.metric("Total Pembelian (Rp)", f"Rp {total_masuk_rp:,.0f}")
        
    st.markdown("<br>", unsafe_allow_html=True)
    
    with st.container(border=True):
        if efisiensi_belanja > 0:
            st.metric("💡 Status Efisiensi Belanja", f"Hemat Rp {efisiensi_belanja:,.0f}")
        elif efisiensi_belanja < 0:
            st.metric("📉 Status Efisiensi Belanja", f"Rugi Rp {abs(efisiensi_belanja):,.0f}")
        else:
            st.metric("⚖️ Status Efisiensi Belanja", "Sesuai HPP (Rp 0)")
            
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
    tab_all, tab_pasien, tab_dokter, tab_manajemen, tab2 = st.tabs([
        "📤 Rekapan Semua", 
        "🛏️ Rekapan Pasien", 
        "🩺 Rekapan Dokter", 
        "💼 Rekapan Manajemen", 
        "📥 Pembelian / Supplier"
    ])
    
    with tab_all:
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
            for col in qty_cols + (['Total Qty (Semua)'] if 'Total Qty (Semua)' in display_df.columns else []):
                display_df[col] = display_df[col].apply(format_qty)
            
            st.dataframe(display_df, use_container_width=True, hide_index=True)
            
            csv_data = pivot_df.sort_values(['Tanggal', 'Shift'], ascending=[False, True]).to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Export ke CSV (Pengeluaran)",
                data=csv_data,
                file_name=f"Rekapan_Pengeluaran_{start_date}_sd_{end_date}.csv",
                mime="text/csv",
            )
            
            with st.expander("🔍 Lihat Rincian Semua Item Pengeluaran (Data Mentah)", expanded=False):
                raw_all_cols = ['tanggal', 'shift', 'Sumber', 'supplier', 'nama_barang', 'kategori', 'kategori_freetext', 'qty', 'harga_real', 'total_harga', 'keterangan']
                avail_all = [c for c in raw_all_cols if c in f_keluar.columns]
                disp_all_raw = f_keluar[avail_all].copy().sort_values(by=['tanggal', 'shift'], ascending=[False, True])
                for c in ['harga_real', 'total_harga']:
                    if c in disp_all_raw.columns:
                        disp_all_raw[c] = disp_all_raw[c].apply(lambda x: f"Rp {float(x):,.0f}" if pd.notna(x) else "-")
                st.dataframe(disp_all_raw, use_container_width=True, hide_index=True)
            
    with tab_pasien:
        render_rekapan_pasien(f_pasien, start_date, end_date)
        
    with tab_dokter:
        render_rekapan_dokter(f_dokter, start_date, end_date)
        
    with tab_manajemen:
        render_rekapan_manajemen(f_manajemen, start_date, end_date)
            
    with tab2:
        if f_masuk.empty:
            st.subheader("Tabel Rekapan Pembelian dari Supplier")
            st.info(f"Tidak ada data pembelian/stok masuk pada periode {start_date.strftime('%d %b %Y')} s/d {end_date.strftime('%d %b %Y')} untuk filter yang dipilih.")
        else:
            df_m = f_masuk.copy()
            if 'supplier' not in df_m.columns:
                df_m['supplier'] = df_m['keterangan'].apply(lambda x: x.split('| Supplier:')[1].split('|')[0].strip() if '| Supplier:' in str(x) else 'Unknown')
            df_m['supplier'] = df_m['supplier'].fillna('Unknown').replace('', 'Unknown')
            
            # Format date & columns
            df_m['Tanggal'] = pd.to_datetime(df_m['tanggal'], errors='coerce').dt.strftime('%Y-%m-%d')
            df_m['Shift'] = df_m['shift'].fillna('-')
            df_m['Supplier'] = df_m['supplier']
            
            df_m['qty'] = pd.to_numeric(df_m['qty'], errors='coerce').fillna(0)
            df_m['harga_master'] = pd.to_numeric(df_m['harga_master'], errors='coerce').fillna(0)
            df_m['harga_real'] = pd.to_numeric(df_m['harga_real'], errors='coerce').fillna(0)
            if 'total_harga' in df_m.columns:
                df_m['total_harga'] = pd.to_numeric(df_m['total_harga'], errors='coerce').fillna(0)
            else:
                df_m['total_harga'] = df_m['qty'] * df_m['harga_real']
            
            df_m['total_hpp_row'] = df_m['qty'] * df_m['harga_master']
            
            def clean_ket(val):
                if pd.isna(val) or str(val).strip() in ['', 'None', 'nan']:
                    return ""
                s = str(val).strip()
                if '| Supplier:' in s:
                    s = s.split('| Supplier:')[0].strip()
                return s

            # Grouping per Tanggal, Shift, Supplier (Rekapan)
            rekap_rows = []
            grouped = df_m.groupby(['Tanggal', 'Shift', 'Supplier'], sort=False)
            
            for (tgl, shf, sup), group in grouped:
                jml_barang = group['nama_barang'].nunique()
                tot_qty = group['qty'].sum()
                sum_harga_master = group['harga_master'].sum()
                sum_harga_real = group['harga_real'].sum()
                tot_harga_semua = group['total_harga'].sum()
                tot_hpp = group['total_hpp_row'].sum()
                selisih_hpp = tot_harga_semua - tot_hpp
                
                notes = [clean_ket(k) for k in group['keterangan'].dropna().unique()]
                notes = [n for n in notes if n]
                ket_text = ", ".join(notes) if notes else "-"
                
                rekap_rows.append({
                    'Tanggal': tgl,
                    'Shift': shf,
                    'Supplier': sup,
                    'Jumlah Barang': jml_barang,
                    'Total Qty': tot_qty,
                    'Jumlah Harga Master': sum_harga_master,
                    'Jumlah Harga Beli Real': sum_harga_real,
                    'Harga Total Semua': tot_harga_semua,
                    'Selisih HPP': selisih_hpp,
                    'Keterangan': ket_text
                })
                
            rekap_df = pd.DataFrame(rekap_rows)
            rekap_df = rekap_df.sort_values(by=['Tanggal', 'Shift'], ascending=[False, True])
            
            st.subheader(f"Tabel Rekapan Pembelian / Supplier ({len(rekap_df)} Rekapan, {len(df_m)} Transaksi Mentah)")
            
            # Formatted display DataFrame
            display_rekap = rekap_df.copy()
            
            # Format number & currency
            display_rekap['Jumlah Barang'] = display_rekap['Jumlah Barang'].apply(lambda x: f"{x:,.0f} Macam")
            display_rekap['Total Qty'] = display_rekap['Total Qty'].apply(format_qty)
            display_rekap['Jumlah Harga Master'] = display_rekap['Jumlah Harga Master'].apply(lambda x: f"Rp {x:,.0f}")
            display_rekap['Jumlah Harga Beli Real'] = display_rekap['Jumlah Harga Beli Real'].apply(lambda x: f"Rp {x:,.0f}")
            display_rekap['Harga Total Semua'] = display_rekap['Harga Total Semua'].apply(lambda x: f"Rp {x:,.0f}")
            
            def format_selisih(val):
                if val > 0:
                    return f"🔴 +Rp {val:,.0f}"
                elif val < 0:
                    return f"🟢 -Rp {abs(val):,.0f}"
                return "Rp 0"
                
            display_rekap['Selisih HPP'] = display_rekap['Selisih HPP'].apply(format_selisih)
            
            st.dataframe(display_rekap, use_container_width=True, hide_index=True)
            
            # Export CSV for Rekapan
            csv_rekap = rekap_df.to_csv(index=False).encode('utf-8')
            col_exp1, _ = st.columns([1, 1])
            with col_exp1:
                st.download_button(
                    label="📥 Export ke CSV (Rekapan Pembelian Supplier)",
                    data=csv_rekap,
                    file_name=f"Rekapan_Pembelian_Supplier_{start_date}_sd_{end_date}.csv",
                    mime="text/csv",
                )
                
            # Detail expander
            with st.expander("🔍 Lihat Rincian Semua Item Barang (Detail Mentah)"):
                detail_df = df_m[['tanggal', 'shift', 'supplier', 'nama_barang', 'qty', 'harga_master', 'harga_real', 'total_harga', 'keterangan']].copy()
                detail_df = detail_df.sort_values(by=['tanggal', 'shift'], ascending=[False, True])
                for c in ['harga_master', 'harga_real', 'total_harga']:
                    detail_df[c] = detail_df[c].apply(lambda x: f"Rp {x:,.0f}")
                st.dataframe(detail_df, use_container_width=True, hide_index=True)
