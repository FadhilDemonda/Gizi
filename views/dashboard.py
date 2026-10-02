import streamlit as st
import pandas as pd
import datetime
import plotly.express as px
from data.sheets_repository import (
    get_sheet_data, SHEET_MASTER, SHEET_STOK_MASUK, 
    SHEET_PENGELUARAN_PASIEN, SHEET_PENGELUARAN_DOKTER, SHEET_PENGELUARAN_MANAJEMEN
)

from views.transaksi import extract_unique_suppliers, match_supplier

@st.dialog("Pilih Banyak Barang Sekaligus 🛒")
def dashboard_item_selector_dialog(master_df, current_items=None, default_supplier=None):
    if current_items is None: 
        current_items = []
    st.markdown("Filter & pilih barang-barang yang ingin dianalisis:")
    
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
            key="dash_dlg_supp_filter"
        )
    with c_f2:
        search_q = st.text_input("🔍 Cari Barang:", placeholder="Ketik nama atau kode barang...", key="dash_dlg_search_input")

    # Filter berdasarkan Supplier
    if selected_supplier and selected_supplier != "Semua Supplier" and 'supplier' in master_df.columns:
        supplier_df = master_df[master_df['supplier'].apply(lambda x: match_supplier(x, selected_supplier))]
    else:
        supplier_df = master_df

    # 2. Filter Kategori (Bahan Basah, Bahan Kering, Alat, dll)
    if 'kategori' in master_df.columns:
        categories = master_df['kategori'].dropna().unique().tolist()
        categories = [c for c in categories if str(c).strip() != '']
        
        uniq_sup_items = supplier_df['nama_barang'].dropna().unique().tolist()
        cat_options = [f"Semua ({len(uniq_sup_items)})"]
        for c in categories:
            count = len(supplier_df[supplier_df['kategori'] == c]['nama_barang'].dropna().unique())
            cat_options.append(f"{c} ({count})")
            
        selected_cat = st.pills("KATEGORI:", cat_options, default=cat_options[0], key=f"dash_dlg_cat_pills_{selected_supplier}")
        
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
        
    filtered_df = filtered_df.drop_duplicates(subset=['nama_barang'])
    filtered_items = [str(x).strip() for x in filtered_df['nama_barang'].dropna().unique() if str(x).strip()]
        
    if 'dash_dialog_set' not in st.session_state:
        st.session_state['dash_dialog_set'] = set(current_items)
            
    st.markdown(f"<div style='font-size:0.85rem; color:gray; font-weight:600;'>Ringkasan Terpilih: {len(st.session_state['dash_dialog_set'])} barang secara keseluruhan</div>", unsafe_allow_html=True)
    
    c_btn1, c_btn2 = st.columns(2)
    with c_btn1:
        if st.button("☑️ Pilih Semua (Filter Saat Ini)", use_container_width=True, key="dash_dlg_sel_all"):
            st.session_state['dash_dialog_set'].update(filtered_items)
            st.rerun()
    with c_btn2:
        if st.button("🔲 Kosongkan Semua", use_container_width=True, key="dash_dlg_clr_all"):
            st.session_state['dash_dialog_set'].clear()
            st.rerun()
            
    new_dialog_set = set([x for x in st.session_state['dash_dialog_set'] if x not in filtered_items])
    
    with st.container(height=350, border=True):
        if not filtered_items:
            st.info("Tidak ada barang yang cocok dengan filter.")
        else:
            cols = st.columns(3)
            for i, item in enumerate(filtered_items):
                with cols[i % 3]:
                    is_checked = st.checkbox(
                        item, 
                        value=(item in st.session_state['dash_dialog_set']),
                        key=f"chk_dash_dlg_{i}_{item}"
                    )
                    if is_checked:
                        new_dialog_set.add(item)
                        
    st.session_state['dash_dialog_set'] = new_dialog_set
    
    if st.button("➕ Terapkan Pilihan", type="primary", use_container_width=True, key="dash_dlg_apply"):
        st.session_state['dash_selected_items'] = list(st.session_state['dash_dialog_set'])
        del st.session_state['dash_dialog_set']
        st.rerun()

def show_dashboard():
    st.header("📊 Dashboard Utama")
    st.caption("Lacak jejak masuk-keluarnya suatu barang secara spesifik untuk mengetahui siapa yang menggunakannya.")
    
    master_df = get_sheet_data(SHEET_MASTER)
    if master_df.empty:
        st.warning("Data Master Barang tidak ditemukan.")
        return
        
    col_sup, col_item, col_date = st.columns([1.2, 1.5, 1.5])
    
    with col_sup:
        all_dfs_sup = [master_df, get_sheet_data(SHEET_STOK_MASUK), get_sheet_data(SHEET_PENGELUARAN_PASIEN), get_sheet_data(SHEET_PENGELUARAN_DOKTER), get_sheet_data(SHEET_PENGELUARAN_MANAJEMEN)]
        supp_list = extract_unique_suppliers(pd.concat([d for d in all_dfs_sup if not d.empty and isinstance(d, pd.DataFrame)], ignore_index=True))
        sup_options = ["Semua Supplier"] + supp_list
        selected_sup = st.selectbox("🏢 Filter Supplier:", sup_options, index=0, key="dash_main_sup")
        
    if selected_sup != "Semua Supplier" and 'supplier' in master_df.columns:
        filtered_master = master_df[master_df['supplier'].apply(lambda x: match_supplier(x, selected_sup))]
    else:
        filtered_master = master_df
        
    item_list = [str(x).strip() for x in filtered_master['nama_barang'].dropna().unique() if str(x).strip()]
    
    with col_item:
        st.markdown("<div style='margin-bottom: 2px; font-size: 14px;'>🔍 Pilih Barang untuk Dianalisis:</div>", unsafe_allow_html=True)
        
        if 'dash_selected_items' not in st.session_state:
            st.session_state['dash_selected_items'] = item_list.copy() if item_list else []
            
        selected_items = [x for x in st.session_state['dash_selected_items'] if x in item_list]
        if not selected_items and item_list:
            selected_items = item_list.copy()
            st.session_state['dash_selected_items'] = selected_items
        
        btn_label = f"🛒 Terpilih {len(selected_items)} Barang" if selected_items else "🔍 Pilih Barang..."
        if st.button(btn_label, use_container_width=True, key="btn_open_dash_dialog"):
            if 'dash_dialog_set' in st.session_state:
                del st.session_state['dash_dialog_set']
            dashboard_item_selector_dialog(master_df, selected_items, default_supplier=selected_sup)
        
    with col_date:
        today = datetime.date.today()
        default_start = today - datetime.timedelta(days=7) if today.day <= 3 else today.replace(day=1)
        date_range = st.date_input("📅 Rentang Waktu Analisis:", value=(default_start, today))
        
    if len(date_range) != 2:
        st.warning("Silakan lengkapi rentang tanggal (Mulai - Akhir) untuk melihat analisis.")
        return
        
    if not selected_items:
        st.info("👆 Silakan pilih minimal 1 barang untuk dianalisis.")
        return
        
    start_date, end_date = date_range
        
    # Summarize master info for selected items
    selected_master = master_df[master_df['nama_barang'].isin(selected_items)].copy()
    if selected_sup != "Semua Supplier" and 'supplier' in selected_master.columns:
        selected_master = selected_master[selected_master['supplier'].apply(lambda x: match_supplier(x, selected_sup))]
    
    selected_master['stok_sekarang'] = pd.to_numeric(selected_master['stok_sekarang'], errors='coerce').fillna(0).clip(lower=0)
    total_stok_sekarang = float(selected_master['stok_sekarang'].sum())
    
    st.markdown("---")
    
    # LOAD ALL TRANSACTIONS
    df_masuk = get_sheet_data(SHEET_STOK_MASUK)
    df_pasien = get_sheet_data(SHEET_PENGELUARAN_PASIEN)
    df_dokter = get_sheet_data(SHEET_PENGELUARAN_DOKTER)
    df_manajemen = get_sheet_data(SHEET_PENGELUARAN_MANAJEMEN)
    
    def filter_by_date(df):
        if df.empty or 'tanggal' not in df.columns:
            return df
        df_copy = df.copy()
        df_copy['date_only'] = pd.to_datetime(df_copy['tanggal'], errors='coerce').dt.date
        mask = (df_copy['date_only'] >= start_date) & (df_copy['date_only'] <= end_date)
        return df_copy[mask].drop(columns=['date_only'])

    df_masuk = filter_by_date(df_masuk)
    df_pasien = filter_by_date(df_pasien)
    df_dokter = filter_by_date(df_dokter)
    df_manajemen = filter_by_date(df_manajemen)
    
    def filter_dash_by_sup(df, target_sup):
        if df.empty or target_sup == "Semua Supplier":
            return df
        target_clean = str(target_sup).strip().lower()
        def check_row(row):
            val = row.get('supplier')
            if (pd.isna(val) or str(val).strip() in ['', 'Unknown', '-', 'nan', 'None']) and 'keterangan' in row and '| Supplier:' in str(row.get('keterangan', '')):
                val = str(row['keterangan']).split('| Supplier:')[1].split('|')[0].strip()
            if not val or pd.isna(val):
                return False
            val_str = str(val).strip().lower()
            val_parts = [p.strip().lower() for p in val_str.split(';')]
            return (target_clean in val_parts) or (target_clean == val_str)
        return df[df.apply(check_row, axis=1)]

    # Normalize supplier column in df_masuk if needed
    if not df_masuk.empty and 'total_harga' in df_masuk.columns:
        if 'supplier' not in df_masuk.columns:
            df_masuk['supplier'] = df_masuk['keterangan'].apply(lambda x: x.split('| Supplier:')[1].split('|')[0].strip() if '| Supplier:' in str(x) else 'Unknown')
        else:
            df_masuk['supplier'] = df_masuk.apply(
                lambda row: row['keterangan'].split('| Supplier:')[1].split('|')[0].strip()
                if (pd.isna(row['supplier']) or str(row['supplier']).strip() in ['', 'Unknown']) and '| Supplier:' in str(row['keterangan'])
                else row['supplier'],
                axis=1
            )
        df_masuk['supplier'] = df_masuk['supplier'].fillna('Unknown').replace('', 'Unknown')

    # FILTER BY ITEMS
    hist_masuk = df_masuk[df_masuk['nama_barang'].isin(selected_items)] if not df_masuk.empty and 'nama_barang' in df_masuk.columns else pd.DataFrame()
    hist_pasien = df_pasien[df_pasien['nama_barang'].isin(selected_items)] if not df_pasien.empty and 'nama_barang' in df_pasien.columns else pd.DataFrame()
    hist_dokter = df_dokter[df_dokter['nama_barang'].isin(selected_items)] if not df_dokter.empty and 'nama_barang' in df_dokter.columns else pd.DataFrame()
    hist_manajemen = df_manajemen[df_manajemen['nama_barang'].isin(selected_items)] if not df_manajemen.empty and 'nama_barang' in df_manajemen.columns else pd.DataFrame()
    
    # FILTER BY SUPPLIER (Pengeluaran & Belanja)
    if selected_sup != "Semua Supplier":
        hist_masuk = filter_dash_by_sup(hist_masuk, selected_sup)
        hist_pasien = filter_dash_by_sup(hist_pasien, selected_sup)
        hist_dokter = filter_dash_by_sup(hist_dokter, selected_sup)
        hist_manajemen = filter_dash_by_sup(hist_manajemen, selected_sup)

    # TAG THE SOURCES
    if not hist_pasien.empty: hist_pasien['Sumber'] = 'Pasien'
    if not hist_dokter.empty: hist_dokter['Sumber'] = 'Dokter'
    if not hist_manajemen.empty: hist_manajemen['Sumber'] = 'Manajemen'
    
    # COMBINE PENGELUARAN
    dfs_keluar = []
    if not hist_pasien.empty: dfs_keluar.append(hist_pasien)
    if not hist_dokter.empty: dfs_keluar.append(hist_dokter)
    if not hist_manajemen.empty: dfs_keluar.append(hist_manajemen)
    
    hist_keluar = pd.concat(dfs_keluar, ignore_index=True) if dfs_keluar else pd.DataFrame()

    total_masuk = hist_masuk['qty'].sum() if not hist_masuk.empty else 0
    total_keluar_qty = hist_keluar['qty'].sum() if not hist_keluar.empty else 0
    
    total_pengeluaran = hist_keluar['total_harga'].sum() if not hist_keluar.empty and 'total_harga' in hist_keluar.columns else 0
    total_belanja_masuk = hist_masuk['total_harga'].sum() if not hist_masuk.empty and 'total_harga' in hist_masuk.columns else 0
    grand_total_pengeluaran = total_pengeluaran + total_belanja_masuk
    
    jml_supplier = hist_masuk['supplier'].nunique() if not hist_masuk.empty and 'supplier' in hist_masuk.columns else 0
    jml_trx_masuk = len(hist_masuk) if not hist_masuk.empty else 0
    
    total_hpp = (hist_keluar['qty'] * hist_keluar['harga_master']).sum() if not hist_keluar.empty and 'harga_master' in hist_keluar.columns and 'qty' in hist_keluar.columns else 0
    total_margin = total_pengeluaran - total_hpp
    
    def format_qty(val):
        try:
            s = f"{float(val):,.2f}"
            if '.' in s:
                s = s.rstrip('0').rstrip('.')
            return s
        except:
            return val
            
    m1, m2, m3 = st.columns(3)
    m1.metric("Stok Fisik Gudang", f"{format_qty(total_stok_sekarang)} Qty")
    m2.metric("Volume Masuk", f"{format_qty(total_masuk)} Qty")
    m3.metric("Volume Keluar", f"{format_qty(total_keluar_qty)} Qty")
    
    st.markdown("---")
    st.markdown("<br>", unsafe_allow_html=True)
    
    # RANGKUMAN FINANSIAL & ENTITAS
    col_fin, col_layanan = st.columns([1.8, 3.2])
    
    with col_fin:
        with st.container(border=True):
            st.markdown("##### 💰 Total Semua Pengeluaran")
            st.metric("Total Keseluruhan", f"Rp {grand_total_pengeluaran:,.0f}")
            st.caption(f"Layanan: Rp {total_pengeluaran:,.0f} • Belanja: Rp {total_belanja_masuk:,.0f}")
            
    with col_layanan:
        with st.container(border=True):
            st.markdown("##### 👥 3 Kategori Layanan & Supplier")
            if not hist_pasien.empty:
                if 'jumlah_pasien' in hist_pasien.columns:
                    # Parse to numeric and fillna with 1 just in case, then group by transaction
                    hp = hist_pasien.copy()
                    hp['jumlah_pasien'] = pd.to_numeric(hp['jumlah_pasien'], errors='coerce').fillna(1)
                    jml_pasien = hp.groupby('tanggal')['jumlah_pasien'].first().sum()
                else:
                    jml_pasien = hist_pasien['kategori_freetext'].nunique() if 'kategori_freetext' in hist_pasien.columns else 0
            else:
                jml_pasien = 0
                
            jml_dokter = hist_dokter['kategori_freetext'].nunique() if not hist_dokter.empty and 'kategori_freetext' in hist_dokter.columns else 0
            jml_manajemen = hist_manajemen['kategori_freetext'].nunique() if not hist_manajemen.empty and 'kategori_freetext' in hist_manajemen.columns else 0
            
            cost_pasien = hist_pasien['total_harga'].sum() if not hist_pasien.empty and 'total_harga' in hist_pasien.columns else 0
            cost_dokter = hist_dokter['total_harga'].sum() if not hist_dokter.empty and 'total_harga' in hist_dokter.columns else 0
            cost_manajemen = hist_manajemen['total_harga'].sum() if not hist_manajemen.empty and 'total_harga' in hist_manajemen.columns else 0
            
            total_entitas = jml_pasien + jml_dokter + jml_manajemen + jml_supplier
            
            e1, e2, e3, e4 = st.columns(4)
            with e1:
                st.metric("Pasien", f"{jml_pasien} ")
                st.caption(f"Rp {cost_pasien:,.0f}")
            with e2:
                st.metric("Dokter", f"{jml_dokter} ")
                st.caption(f"Rp {cost_dokter:,.0f}")
            with e3:
                st.metric("Manajemen", f"{jml_manajemen} ")
                st.caption(f"Rp {cost_manajemen:,.0f}")
            with e4:
                st.metric("Supplier", f"{jml_supplier} ")
                st.caption(f"Rp {total_belanja_masuk:,.0f}")
            
    st.markdown("<br>", unsafe_allow_html=True)
    
    # VISUALISASI CHART
    col_chart, col_data = st.columns([1, 1.5])
    
    with col_chart:
        st.subheader("Distribusi Biaya Pengeluaran")
        pie_list = []
        if not hist_keluar.empty and 'total_harga' in hist_keluar.columns:
            pie_keluar = hist_keluar.groupby('Sumber')['total_harga'].sum().reset_index()
            pie_list.append(pie_keluar)
        if total_belanja_masuk > 0:
            pie_list.append(pd.DataFrame([{'Sumber': 'Supplier', 'total_harga': total_belanja_masuk}]))
            
        if pie_list:
            pie_data = pd.concat(pie_list, ignore_index=True)
            fig = px.pie(pie_data, values='total_harga', names='Sumber', hole=0.4, 
                         color_discrete_sequence=px.colors.qualitative.Pastel)
            fig.update_layout(margin=dict(t=0, b=0, l=0, r=0))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Belum ada data biaya pengeluaran untuk dianalisis.")
            
    with col_data:
        st.subheader("Top Kategori (Berdasarkan Biaya)")
        if not hist_keluar.empty and 'kategori' in hist_keluar.columns and 'total_harga' in hist_keluar.columns:
            top_cats = hist_keluar.groupby(['kategori', 'Sumber'])['total_harga'].sum().reset_index()
            top_cats = top_cats.sort_values(by='total_harga', ascending=False).head(25)
            
            fig_bar = px.bar(
                top_cats, 
                x='total_harga', 
                y='kategori', 
                color='Sumber',
                orientation='h',
                color_discrete_sequence=px.colors.qualitative.Pastel,
                text='total_harga'
            )
            fig_bar.update_traces(texttemplate='Rp %{text:,.0f}', textposition='outside')
            fig_bar.update_layout(
                yaxis={'categoryorder':'total ascending'},
                margin=dict(t=0, b=50, l=0, r=0),
                xaxis_title="Total Biaya (Rp)",
                yaxis_title="",
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=-0.3,
                    xanchor="right",
                    x=1
                )
            )
            st.plotly_chart(fig_bar, use_container_width=True)
        else:
            st.info("Belum ada riwayat biaya kategori yang memakai barang ini.")

    st.divider()
    
    st.subheader("📥 Total Belanja per Supplier (Stok Masuk)")
    if not hist_masuk.empty and 'total_harga' in hist_masuk.columns:
        supplier_data = hist_masuk.groupby('supplier')['total_harga'].sum().reset_index()
        supplier_data = supplier_data.sort_values(by='total_harga', ascending=False).head(20)
        
        fig_sup = px.bar(
            supplier_data,
            x='supplier',
            y='total_harga',
            color='supplier',
            text='total_harga',
            color_discrete_sequence=px.colors.qualitative.Pastel
        )
        fig_sup.update_traces(texttemplate='Rp %{text:,.0f}', textposition='outside')
        fig_sup.update_layout(
            margin=dict(t=20, b=0, l=0, r=0),
            xaxis_title="",
            yaxis_title="Biaya Belanja (Rp)",
            showlegend=False
        )
        st.plotly_chart(fig_sup, use_container_width=True)
    else:
        st.info("Belum ada riwayat belanja/stok masuk untuk dianalisis supplier-nya.")

    st.divider()
    
    st.subheader("Perbandingan Volume Qty (Masuk vs Keluar)")
    agg_masuk = hist_masuk.groupby('nama_barang')['qty'].sum().reset_index() if not hist_masuk.empty else pd.DataFrame(columns=['nama_barang', 'qty'])
    if not agg_masuk.empty: agg_masuk['Tipe'] = 'Masuk'
    
    agg_keluar = hist_keluar.groupby('nama_barang')['qty'].sum().reset_index() if not hist_keluar.empty else pd.DataFrame(columns=['nama_barang', 'qty'])
    if not agg_keluar.empty:
        agg_keluar['qty'] = -agg_keluar['qty']
        agg_keluar['Tipe'] = 'Keluar'
    
    df_compare = pd.concat([agg_masuk, agg_keluar])
    if not df_compare.empty and df_compare['qty'].abs().sum() > 0:
        # Limit max 25 barang paling aktif
        top_active_items = df_compare.groupby('nama_barang')['qty'].apply(lambda x: x.abs().sum()).sort_values(ascending=False).head(25).index
        df_compare = df_compare[df_compare['nama_barang'].isin(top_active_items)]
        
        df_compare['qty_abs'] = df_compare['qty'].abs()
        fig_compare = px.bar(
            df_compare,
            x='nama_barang',
            y='qty',
            color='Tipe',
            barmode='relative',
            color_discrete_map={'Masuk': '#2e7d32', 'Keluar': '#c62828'},
            text='qty_abs'
        )
        fig_compare.update_traces(texttemplate='%{text:,.0f}', textposition='auto')
        fig_compare.update_layout(
            margin=dict(t=10, b=0, l=0, r=0), 
            xaxis_title="Nama Barang (Top 25)", 
            yaxis_title="Total Qty (Masuk = Positif, Keluar = Negatif)"
        )
        st.plotly_chart(fig_compare, use_container_width=True)
    else:
        st.info("Belum ada data masuk atau keluar untuk rentang waktu dan barang yang dipilih.")

    st.divider()
    tab_rangkuman, tab_masuk, tab_keluar = st.tabs(["📊 Tabel Rangkuman Analisis", "📥 Riwayat Belanja / Masuk", "📤 Riwayat Pemakaian / Keluar"])
    
    with tab_rangkuman:
        # === BUILD THE SUMMARY TABLE ===
        # 1. Total Qty (stok gudang) - gabungkan per nama_barang agar baris tidak dobel
        summary_master = selected_master.copy()
        summary_master['stok_sekarang'] = pd.to_numeric(summary_master['stok_sekarang'], errors='coerce').fillna(0).clip(lower=0)
        summary_df = summary_master.groupby('nama_barang', as_index=False)['stok_sekarang'].sum()
        summary_df.rename(columns={'nama_barang': 'BARANG', 'stok_sekarang': 'TOTAL QTY'}, inplace=True)
        
        # 2. Masuk metrics
        if not hist_masuk.empty:
            hm = hist_masuk.copy()
            hm['qty'] = pd.to_numeric(hm['qty'], errors='coerce').fillna(0)
            hm['total_harga'] = pd.to_numeric(hm['total_harga'], errors='coerce').fillna(0)
            hm['harga_master'] = pd.to_numeric(hm['harga_master'], errors='coerce').fillna(0)
            hm['pembelian_hpp'] = hm['qty'] * hm['harga_master']
            
            masuk_grp = hm.groupby('nama_barang').agg(
                TOTAL_QTY_MASUK=('qty', 'sum'),
                TOTAL_PEMBELIAN=('total_harga', 'sum'),
                TOTAL_PEMBELIAN_HPP=('pembelian_hpp', 'sum')
            ).reset_index()
            masuk_grp.rename(columns={'nama_barang': 'BARANG', 'TOTAL_QTY_MASUK': 'TOTAL QTY MASUK', 'TOTAL_PEMBELIAN': 'TOTAL PEMBELIAN', 'TOTAL_PEMBELIAN_HPP': 'TOTAL PEMBELIAN BERDASARKAN HPP'}, inplace=True)
            summary_df = pd.merge(summary_df, masuk_grp, on='BARANG', how='left')
        else:
            summary_df['TOTAL QTY MASUK'] = 0
            summary_df['TOTAL PEMBELIAN'] = 0
            summary_df['TOTAL PEMBELIAN BERDASARKAN HPP'] = 0
            
        # 3. Keluar metrics
        if not hist_keluar.empty:
            hk = hist_keluar.copy()
            hk['qty'] = pd.to_numeric(hk['qty'], errors='coerce').fillna(0)
            hk['total_harga'] = pd.to_numeric(hk['total_harga'], errors='coerce').fillna(0)
            
            keluar_grp = hk.groupby('nama_barang').agg(
                TOTAL_QTY_KELUAR=('qty', 'sum'),
                TOTAL_PENGELUARAN=('total_harga', 'sum')
            ).reset_index()
            keluar_grp.rename(columns={'nama_barang': 'BARANG', 'TOTAL_QTY_KELUAR': 'TOTAL QTY KELUAR', 'TOTAL_PENGELUARAN': 'TOTAL PENGELUARAN'}, inplace=True)
            summary_df = pd.merge(summary_df, keluar_grp, on='BARANG', how='left')
        else:
            summary_df['TOTAL QTY KELUAR'] = 0
            summary_df['TOTAL PENGELUARAN'] = 0
            
        # Fill NAs
        for col in ['TOTAL QTY MASUK', 'TOTAL QTY KELUAR', 'TOTAL PEMBELIAN', 'TOTAL PEMBELIAN BERDASARKAN HPP', 'TOTAL PENGELUARAN']:
            summary_df[col] = summary_df[col].fillna(0)
            
        # 4. Status Rugi
        summary_df['STATUS RUGI DENGAN HPP'] = summary_df['TOTAL PEMBELIAN BERDASARKAN HPP'] - summary_df['TOTAL PEMBELIAN']
        
        # Format the dataframe
        disp_summary = summary_df.copy()
        format_cols = ['TOTAL QTY', 'TOTAL QTY MASUK', 'TOTAL QTY KELUAR']
        rp_cols = ['TOTAL PEMBELIAN', 'TOTAL PEMBELIAN BERDASARKAN HPP', 'TOTAL PENGELUARAN', 'STATUS RUGI DENGAN HPP']
        
        for c in format_cols:
            disp_summary[c] = disp_summary[c].apply(lambda x: format_qty(x) if pd.notnull(x) else "0")
        for c in rp_cols:
            disp_summary[c] = disp_summary[c].apply(lambda x: f"Rp {x:,.0f}" if pd.notnull(x) else "Rp 0")
            
        st.dataframe(disp_summary, use_container_width=True, hide_index=True)
    
    with tab_masuk:
        if not hist_masuk.empty:
            cols_m = ['tanggal', 'shift', 'supplier', 'nama_barang', 'qty', 'harga_master', 'harga_real', 'total_harga', 'keterangan']
            avail_m = [c for c in cols_m if c in hist_masuk.columns]
            display_masuk = hist_masuk[avail_m].copy()
            for c in ['harga_master', 'harga_real', 'total_harga']:
                if c in display_masuk.columns:
                    display_masuk[c] = display_masuk[c].apply(lambda x: f"Rp {float(x):,.0f}" if pd.notna(x) else "-")
            st.dataframe(display_masuk.sort_values('tanggal', ascending=False), use_container_width=True, hide_index=True)
        else:
            st.info("Belum ada riwayat pembelian untuk barang & supplier terpilih.")
            
    with tab_keluar:
        if not hist_keluar.empty:
            cols_to_show = ['tanggal', 'Sumber', 'supplier', 'nama_barang', 'kategori', 'kategori_freetext', 'qty', 'total_harga', 'keterangan']
            if 'jumlah_pasien' in hist_keluar.columns:
                cols_to_show.insert(7, 'jumlah_pasien')
            avail_k = [c for c in cols_to_show if c in hist_keluar.columns]
            display_keluar = hist_keluar[avail_k].copy()
            if 'total_harga' in display_keluar.columns:
                display_keluar['total_harga'] = display_keluar['total_harga'].apply(lambda x: f"Rp {float(x):,.0f}" if pd.notna(x) else "-")
            st.dataframe(display_keluar.sort_values('tanggal', ascending=False), use_container_width=True, hide_index=True)
        else:
            st.info("Belum ada riwayat pemakaian untuk barang & supplier terpilih.")
