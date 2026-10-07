import streamlit as st
import datetime
import pandas as pd
from data.sheets_repository import (
    get_sheet_data, save_data, SHEET_MASTER, SHEET_STOK_MASUK, SHEET_LOG,
    SHEET_PENGELUARAN_PASIEN, SHEET_PENGELUARAN_DOKTER, SHEET_PENGELUARAN_MANAJEMEN, SHEET_PENGELUARAN_KARYAWAN
)
from views.transaksi import extract_unique_suppliers, match_supplier
from views.pengeluaran_common import show_toast

def parse_date_range(date_val, default_date):
    """Bantu parsing rentang tanggal agar tidak error saat rentang belum lengkap."""
    if isinstance(date_val, (tuple, list)):
        if len(date_val) == 2:
            return date_val[0], date_val[1]
        elif len(date_val) == 1:
            return date_val[0], date_val[0]
        else:
            return default_date, default_date
    elif isinstance(date_val, (datetime.date, datetime.datetime)):
        return date_val, date_val
    return default_date, default_date

def find_master_index(master_df, item_name, item_supp):
    """Cari indeks baris master barang yang sesuai dengan prioritas nama_barang dan supplier."""
    idx_list = []
    if item_supp and str(item_supp).strip() not in ["-", "[Sesuai Paket]", ""]:
        idx_list = master_df.index[
            (master_df['nama_barang'].astype(str).str.strip().str.lower() == str(item_name).strip().lower()) & 
            (master_df['supplier'].astype(str).str.strip().str.lower() == str(item_supp).strip().lower())
        ].tolist()
    if not idx_list:
        idx_list = master_df.index[
            master_df['nama_barang'].astype(str).str.strip().str.lower() == str(item_name).strip().lower()
        ].tolist()
    return idx_list[0] if idx_list else None

def load_all_pengeluaran_df():
    """Memuat dan menyatukan seluruh riwayat pengeluaran (Pasien, Dokter, Manajemen) ke dalam satu DataFrame."""
    trx_pasien = get_sheet_data(SHEET_PENGELUARAN_PASIEN)
    trx_dokter = get_sheet_data(SHEET_PENGELUARAN_DOKTER)
    trx_manajemen = get_sheet_data(SHEET_PENGELUARAN_MANAJEMEN)
    trx_karyawan = get_sheet_data(SHEET_PENGELUARAN_KARYAWAN)
    
    rows = []
    
    if not trx_pasien.empty and 'tanggal' in trx_pasien.columns:
        for idx, r in trx_pasien.iterrows():
            qty = pd.to_numeric(str(r.get('qty', 0)).replace(',', '.'), errors='coerce') or 0.0
            p_val = pd.to_numeric(str(r.get('harga_real', 0)).replace(',', '.'), errors='coerce') or 0.0
            tot = pd.to_numeric(str(r.get('total_harga', qty * p_val)).replace(',', '.'), errors='coerce') or (qty * p_val)
            pas = pd.to_numeric(str(r.get('jumlah_pasien', 1)).replace(',', '.'), errors='coerce') or 1
            rows.append({
                '_id': f"PASIEN_{idx}",
                '_cat_type': 'PASIEN',
                '_orig_idx': idx,
                'sumber': '🛏️ Pasien',
                'tanggal': str(r.get('tanggal', ''))[:10],
                'shift': str(r.get('shift', '-')),
                'kategori': str(r.get('kategori', '-')),
                'tujuan': f"{int(pas)} Pasien" if pas > 0 else "-",
                'nama_barang': str(r.get('nama_barang', '')),
                'supplier': str(r.get('supplier', '-')),
                'satuan': str(r.get('satuan', 'Pcs')),
                'qty': float(qty),
                'harga_real': float(p_val),
                'total_harga': float(tot),
                'jumlah_pasien': int(pas),
                'keterangan': str(r.get('keterangan', '')) if pd.notna(r.get('keterangan')) and str(r.get('keterangan')).strip() not in ['nan', 'None'] else "",
                'hapus': False
            })
            
    if not trx_dokter.empty and 'tanggal' in trx_dokter.columns:
        for idx, r in trx_dokter.iterrows():
            qty = pd.to_numeric(str(r.get('qty', 0)).replace(',', '.'), errors='coerce') or 0.0
            p_val = pd.to_numeric(str(r.get('harga_real', 0)).replace(',', '.'), errors='coerce') or 0.0
            tot = pd.to_numeric(str(r.get('total_harga', qty * p_val)).replace(',', '.'), errors='coerce') or (qty * p_val)
            rows.append({
                '_id': f"DOKTER_{idx}",
                '_cat_type': 'DOKTER',
                '_orig_idx': idx,
                'sumber': '🩺 Dokter',
                'tanggal': str(r.get('tanggal', ''))[:10],
                'shift': str(r.get('shift', '-')),
                'kategori': str(r.get('kategori', '-')),
                'tujuan': str(r.get('kategori_freetext', '-')),
                'nama_barang': str(r.get('nama_barang', '')),
                'supplier': str(r.get('supplier', '-')),
                'satuan': str(r.get('satuan', 'Pcs')),
                'qty': float(qty),
                'harga_real': float(p_val),
                'total_harga': float(tot),
                'jumlah_pasien': 0,
                'keterangan': str(r.get('keterangan', '')) if pd.notna(r.get('keterangan')) and str(r.get('keterangan')).strip() not in ['nan', 'None'] else "",
                'hapus': False
            })

    if not trx_manajemen.empty and 'tanggal' in trx_manajemen.columns:
        for idx, r in trx_manajemen.iterrows():
            qty = pd.to_numeric(str(r.get('qty', 0)).replace(',', '.'), errors='coerce') or 0.0
            p_val = pd.to_numeric(str(r.get('harga_real', 0)).replace(',', '.'), errors='coerce') or 0.0
            tot = pd.to_numeric(str(r.get('total_harga', qty * p_val)).replace(',', '.'), errors='coerce') or (qty * p_val)
            rows.append({
                '_id': f"MANAJEMEN_{idx}",
                '_cat_type': 'MANAJEMEN',
                '_orig_idx': idx,
                'sumber': '🏢 Manajemen',
                'tanggal': str(r.get('tanggal', ''))[:10],
                'shift': str(r.get('shift', '-')),
                'kategori': str(r.get('kategori', '-')),
                'tujuan': str(r.get('kategori_freetext', '-')),
                'nama_barang': str(r.get('nama_barang', '')),
                'supplier': str(r.get('supplier', '-')),
                'satuan': str(r.get('satuan', 'Pcs')),
                'qty': float(qty),
                'harga_real': float(p_val),
                'total_harga': float(tot),
                'jumlah_pasien': 0,
                'keterangan': str(r.get('keterangan', '')) if pd.notna(r.get('keterangan')) and str(r.get('keterangan')).strip() not in ['nan', 'None'] else "",
                'hapus': False
            })

    if not trx_karyawan.empty and 'tanggal' in trx_karyawan.columns:
        for idx, r in trx_karyawan.iterrows():
            qty = pd.to_numeric(str(r.get('qty', 0)).replace(',', '.'), errors='coerce') or 0.0
            p_val = pd.to_numeric(str(r.get('harga_real', 0)).replace(',', '.'), errors='coerce') or 0.0
            tot = pd.to_numeric(str(r.get('total_harga', qty * p_val)).replace(',', '.'), errors='coerce') or (qty * p_val)
            rows.append({
                '_id': f"KARYAWAN_{idx}",
                '_cat_type': 'KARYAWAN',
                '_orig_idx': idx,
                'sumber': '👥 Karyawan',
                'tanggal': str(r.get('tanggal', ''))[:10],
                'shift': str(r.get('shift', '-')),
                'kategori': str(r.get('kategori', '-')),
                'tujuan': str(r.get('kategori_freetext', '-')),
                'nama_barang': str(r.get('nama_barang', '')),
                'supplier': str(r.get('supplier', '-')),
                'satuan': str(r.get('satuan', 'Pcs')),
                'qty': float(qty),
                'harga_real': float(p_val),
                'total_harga': float(tot),
                'jumlah_pasien': 0,
                'keterangan': str(r.get('keterangan', '')) if pd.notna(r.get('keterangan')) and str(r.get('keterangan')).strip() not in ['nan', 'None'] else "",
                'hapus': False
            })
            
    if not rows:
        return pd.DataFrame(columns=[
            '_id', '_cat_type', '_orig_idx', 'sumber', 'tanggal', 'shift', 'kategori',
            'tujuan', 'nama_barang', 'supplier', 'satuan', 'qty', 'harga_real',
            'total_harga', 'jumlah_pasien', 'keterangan', 'hapus'
        ])
    return pd.DataFrame(rows)

def execute_unified_pengeluaran_save(items_by_cat, master_df):
    """
    Eksekusi penyimpanan koreksi/penghapusan pengeluaran terpadu (Pasien, Dokter, Manajemen):
    1. Update/hapus baris di sheet pengeluaran terkait.
    2. Menyesuaikan stok fisik di SHEET_MASTER (kembalikan stok jika dihapus/qty turun, potong jika naik).
    3. Untuk Pasien: Menyesuaikan FIFO sisa_qty di SHEET_STOK_MASUK.
    4. Mencatat log ke SHEET_LOG.
    """
    master_current = get_sheet_data(SHEET_MASTER)
    if master_current.empty:
        master_current = master_df.copy()

    stok_masuk_current = get_sheet_data(SHEET_STOK_MASUK)
    if not stok_masuk_current.empty:
        if 'sisa_qty' not in stok_masuk_current.columns:
            stok_masuk_current['sisa_qty'] = stok_masuk_current['qty'].copy() if 'qty' in stok_masuk_current.columns else 0.0
        else:
            stok_masuk_current['sisa_qty'] = pd.to_numeric(
                stok_masuk_current['sisa_qty'].apply(lambda x: str(x).replace(',', '.') if isinstance(x, str) else x),
                errors='coerce'
            ).fillna(0.0)

    log_entries = []
    master_changed = False
    stok_masuk_changed = False
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    total_processed = 0
    total_deleted = 0

    category_sheet_map = {
        'PASIEN': SHEET_PENGELUARAN_PASIEN,
        'DOKTER': SHEET_PENGELUARAN_DOKTER,
        'MANAJEMEN': SHEET_PENGELUARAN_MANAJEMEN,
        'KARYAWAN': SHEET_PENGELUARAN_KARYAWAN
    }

    for cat_type, items_to_process in items_by_cat.items():
        if not items_to_process:
            continue
        sheet_name = category_sheet_map[cat_type]
        trx_current = get_sheet_data(sheet_name)
        indices_to_drop = []

        for item in items_to_process:
            orig_idx = item['orig_idx']
            item_name = item['nama_barang']
            old_q = float(item['old_qty'])
            old_p = float(item['old_price'])
            old_total = float(item['old_total'])
            item_supp = str(item.get('supplier', '-')).strip()
            kat_label = str(item.get('kategori', '-')).strip()

            if item.get('is_deleted', False):
                indices_to_drop.append(orig_idx)
                total_deleted += 1

                # Kembalikan stok fisik ke master
                m_idx = find_master_index(master_current, item_name, item_supp)
                if m_idx is not None and old_q > 0:
                    cur_stok = float(pd.to_numeric(master_current.at[m_idx, 'stok_sekarang'], errors='coerce')) if pd.notna(master_current.at[m_idx, 'stok_sekarang']) else 0.0
                    master_current.at[m_idx, 'stok_sekarang'] = cur_stok + old_q
                    master_changed = True

                # Kembalikan FIFO stok_masuk jika pasien
                if cat_type == 'PASIEN' and not stok_masuk_current.empty and 'nama_barang' in stok_masuk_current.columns and old_q > 0:
                    mask_f = (stok_masuk_current['nama_barang'].astype(str).str.strip().str.lower() == item_name.strip().lower())
                    if item_supp and item_supp != "-":
                        m_fifo_s = stok_masuk_current[mask_f & (stok_masuk_current['supplier'].astype(str).str.strip().str.lower() == item_supp.lower())]
                        m_fifo = m_fifo_s if not m_fifo_s.empty else stok_masuk_current[mask_f]
                    else:
                        m_fifo = stok_masuk_current[mask_f]

                    if not m_fifo.empty:
                        m_fifo_copy = m_fifo.copy()
                        m_fifo_copy['dt_temp'] = pd.to_datetime(m_fifo_copy['tanggal'], errors='coerce')
                        sorted_b_indices = m_fifo_copy.sort_values(by=['dt_temp'], ascending=False, na_position='first').index.tolist()

                        rem_to_return = old_q
                        for b_idx in sorted_b_indices:
                            if rem_to_return <= 0:
                                break
                            orig_b_qty = float(stok_masuk_current.at[b_idx, 'qty']) if pd.notna(stok_masuk_current.at[b_idx, 'qty']) else 999999.0
                            cur_b_sisa = float(stok_masuk_current.at[b_idx, 'sisa_qty'])
                            can_add = max(0.0, orig_b_qty - cur_b_sisa)
                            add_amt = min(rem_to_return, can_add) if can_add > 0 else rem_to_return
                            stok_masuk_current.at[b_idx, 'sisa_qty'] = cur_b_sisa + add_amt
                            rem_to_return -= add_amt
                            stok_masuk_changed = True

                        if rem_to_return > 0 and sorted_b_indices:
                            latest_b = sorted_b_indices[0]
                            stok_masuk_current.at[latest_b, 'sisa_qty'] = float(stok_masuk_current.at[latest_b, 'sisa_qty']) + rem_to_return
                            stok_masuk_changed = True

                log_entries.append({
                    "tanggal": now_str,
                    "aksi": f"HAPUS_PENGELUARAN_{cat_type}",
                    "keterangan": f"Hapus {item_name} ({kat_label}) [{item_supp}]: Qty {old_q:g}, Biaya Rp {old_total:,.0f}"
                })
                total_processed += 1
                continue

            # Jika diedit
            new_q = float(item['new_qty'])
            new_p = float(item['new_price'])
            new_tot = new_q * new_p
            new_ket = str(item.get('new_ket', '')).strip()
            qty_diff = new_q - old_q

            if orig_idx in trx_current.index:
                trx_current.at[orig_idx, 'qty'] = new_q
                trx_current.at[orig_idx, 'harga_real'] = new_p
                trx_current.at[orig_idx, 'total_harga'] = new_tot
                trx_current.at[orig_idx, 'keterangan'] = new_ket

                if cat_type == 'PASIEN' and 'jumlah_pasien' in trx_current.columns:
                    trx_current.at[orig_idx, 'jumlah_pasien'] = float(item.get('new_pasien', 1.0))

            if qty_diff != 0:
                m_idx = find_master_index(master_current, item_name, item_supp)
                if m_idx is not None:
                    cur_stok = float(pd.to_numeric(master_current.at[m_idx, 'stok_sekarang'], errors='coerce')) if pd.notna(master_current.at[m_idx, 'stok_sekarang']) else 0.0
                    master_current.at[m_idx, 'stok_sekarang'] = max(0.0, cur_stok - qty_diff)
                    master_changed = True

                if cat_type == 'PASIEN' and not stok_masuk_current.empty and 'nama_barang' in stok_masuk_current.columns:
                    mask_f = (stok_masuk_current['nama_barang'].astype(str).str.strip().str.lower() == item_name.strip().lower())
                    if item_supp and item_supp != "-":
                        m_fifo_s = stok_masuk_current[mask_f & (stok_masuk_current['supplier'].astype(str).str.strip().str.lower() == item_supp.lower())]
                        m_fifo = m_fifo_s if not m_fifo_s.empty else stok_masuk_current[mask_f]
                    else:
                        m_fifo = stok_masuk_current[mask_f]

                    if not m_fifo.empty:
                        m_fifo_copy = m_fifo.copy()
                        m_fifo_copy['dt_temp'] = pd.to_datetime(m_fifo_copy['tanggal'], errors='coerce')

                        if qty_diff > 0:
                            rem_deduct = qty_diff
                            sorted_oldest = m_fifo_copy.sort_values(by=['dt_temp'], ascending=True, na_position='last').index.tolist()
                            for b_idx in sorted_oldest:
                                if rem_deduct <= 0:
                                    break
                                cur_sisa = float(stok_masuk_current.at[b_idx, 'sisa_qty'])
                                if cur_sisa > 0:
                                    take = min(rem_deduct, cur_sisa)
                                    stok_masuk_current.at[b_idx, 'sisa_qty'] = cur_sisa - take
                                    rem_deduct -= take
                                    stok_masuk_changed = True
                        else:
                            rem_return = abs(qty_diff)
                            sorted_newest = m_fifo_copy.sort_values(by=['dt_temp'], ascending=False, na_position='first').index.tolist()
                            for b_idx in sorted_newest:
                                if rem_return <= 0:
                                    break
                                orig_b_qty = float(stok_masuk_current.at[b_idx, 'qty']) if pd.notna(stok_masuk_current.at[b_idx, 'qty']) else 999999.0
                                cur_b_sisa = float(stok_masuk_current.at[b_idx, 'sisa_qty'])
                                can_add = max(0.0, orig_b_qty - cur_b_sisa)
                                add_amt = min(rem_return, can_add) if can_add > 0 else rem_return
                                stok_masuk_current.at[b_idx, 'sisa_qty'] = cur_b_sisa + add_amt
                                rem_return -= add_amt
                                stok_masuk_changed = True

                            if rem_return > 0 and sorted_newest:
                                latest_b = sorted_newest[0]
                                stok_masuk_current.at[latest_b, 'sisa_qty'] = float(stok_masuk_current.at[latest_b, 'sisa_qty']) + rem_return
                                stok_masuk_changed = True

            log_entries.append({
                "tanggal": now_str,
                "aksi": f"KOREKSI_PENGELUARAN_{cat_type}",
                "keterangan": f"Koreksi {item_name} ({kat_label}): Qty {old_q:g} -> {new_q:g}, Harga Rp {old_p:,.0f} -> Rp {new_p:,.0f}"
            })
            total_processed += 1

        if indices_to_drop:
            trx_current = trx_current.drop(index=indices_to_drop).reset_index(drop=True)
        save_data(trx_current, sheet_name)

    if master_changed:
        save_data(master_current, SHEET_MASTER)
    if stok_masuk_changed and not stok_masuk_current.empty:
        save_data(stok_masuk_current, SHEET_STOK_MASUK)
    if log_entries:
        crud_log_df = get_sheet_data(SHEET_LOG)
        new_log_df = pd.DataFrame(log_entries)
        crud_log_df = pd.concat([crud_log_df, new_log_df], ignore_index=True)
        save_data(crud_log_df, SHEET_LOG)

    msg = f"Berhasil menyimpan perubahan ({total_processed} baris diproses"
    if total_deleted > 0:
        msg += f", {total_deleted} baris dihapus"
    msg += ")!"
    st.session_state['toast_msg_riwayat_pengeluaran'] = msg
    st.rerun()

def execute_koreksi_pembelian_save(items_to_save, master_df):
    """Menyimpan pembaruan koreksi riwayat harga (stok masuk) dan penyesuaian master barang."""
    trx_masuk_current = get_sheet_data(SHEET_STOK_MASUK)
    master_current = master_df.copy()
    master_changed = False
    log_entries = []
    indices_to_drop = []
    
    for item in items_to_save:
        o_idx = item['orig_idx']
        item_name = item['nama_barang']
        supp_name = item['supplier']
        old_q = float(item['old_qty'])
        old_p = float(item['old_price'])
        old_tot = float(item['old_total'])
        
        if item.get('is_deleted', False):
            indices_to_drop.append(o_idx)
            # Potong stok master yang pernah ditambah saat barang masuk
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
                cur_stok = float(pd.to_numeric(master_current.at[m_idx, 'stok_sekarang'], errors='coerce')) if pd.notna(master_current.at[m_idx, 'stok_sekarang']) else 0.0
                master_current.at[m_idx, 'stok_sekarang'] = max(0.0, cur_stok - old_q)
                master_changed = True
            log_entries.append({
                "tanggal": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "aksi": "HAPUS_STOK_MASUK",
                "keterangan": f"Hapus Pembelian {item_name} ({supp_name}): Qty {old_q:g}, Nilai Rp {old_tot:,.0f}"
            })
            continue

        new_q = float(item['new_qty'])
        new_p = float(item['new_price'])
        new_tot = float(item['new_total'])
        new_ket = item['keterangan']
        upd_hpp = item.get('update_hpp', False)
        
        if o_idx in trx_masuk_current.index:
            trx_masuk_current.at[o_idx, 'qty'] = new_q
            trx_masuk_current.at[o_idx, 'harga_real'] = new_p
            trx_masuk_current.at[o_idx, 'total_harga'] = new_tot
            trx_masuk_current.at[o_idx, 'keterangan'] = new_ket
            if 'sisa_qty' in trx_masuk_current.columns:
                curr_sisa = float(trx_masuk_current.at[o_idx, 'sisa_qty']) if pd.notna(trx_masuk_current.at[o_idx, 'sisa_qty']) else old_q
                trx_masuk_current.at[o_idx, 'sisa_qty'] = max(0.0, curr_sisa + (new_q - old_q))
                
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
                
        log_entries.append({
            "tanggal": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "aksi": "KOREKSI_HARGA_STOK_MASUK",
            "keterangan": f"Koreksi {item_name} ({supp_name}): Harga Rp {old_p:,.0f} -> Rp {new_p:,.0f} (Qty: {old_q} -> {new_q})"
        })

    if indices_to_drop:
        trx_masuk_current = trx_masuk_current.drop(index=indices_to_drop).reset_index(drop=True)

    save_data(trx_masuk_current, SHEET_STOK_MASUK)
    if master_changed:
        save_data(master_current, SHEET_MASTER)
    if log_entries:
        crud_log_df = get_sheet_data(SHEET_LOG)
        new_log_df = pd.DataFrame(log_entries)
        crud_log_df = pd.concat([crud_log_df, new_log_df], ignore_index=True)
        save_data(crud_log_df, SHEET_LOG)
        
    st.session_state['toast_msg_riwayat_pengeluaran'] = f"Berhasil menyimpan perubahan riwayat harga ({len(items_to_save)} baris diproses)!"
    st.rerun()

def render_riwayat_pengeluaran_excel(master_df):
    """Tampilan Tabel Excel Terpadu untuk Riwayat Pengeluaran (Pasien, Dokter, Manajemen)."""
    today = datetime.date.today()
    all_trx = load_all_pengeluaran_df()

    with st.container(border=True):
        c1, c2, c3, c4, c5 = st.columns([1.3, 1.2, 1.4, 1.2, 1.4])
        with c1:
            date_range = st.date_input("📅 Rentang Tanggal:", value=(today, today), key="rwe_date_range")
            k_start, k_end = parse_date_range(date_range, today)
        with c2:
            sumber_opts = ["Semua Pengeluaran", "🛏️ Pasien", "🩺 Dokter", "🏢 Manajemen", "👥 Karyawan"]
            sel_sumber = st.selectbox("📂 Sumber Pengeluaran:", sumber_opts, key="rwe_sel_sumber")

        # Ambil opsi kategori secara dinamis sesuai pilihan Sumber Pengeluaran
        if sel_sumber == "🛏️ Pasien":
            df_for_cat = all_trx[all_trx['sumber'] == "🛏️ Pasien"]
        elif sel_sumber == "🩺 Dokter":
            df_for_cat = all_trx[all_trx['sumber'] == "🩺 Dokter"]
        elif sel_sumber == "🏢 Manajemen":
            df_for_cat = all_trx[all_trx['sumber'] == "🏢 Manajemen"]
        elif sel_sumber == "👥 Karyawan":
            df_for_cat = all_trx[all_trx['sumber'] == "👥 Karyawan"]
        else:
            df_for_cat = all_trx

        raw_kategori_list = [
            str(k).strip() for k in df_for_cat['kategori'].dropna().unique() 
            if str(k).strip() and str(k).strip().lower() not in ['nan', 'none', '-']
        ]
        kategori_options = sorted(list(dict.fromkeys(raw_kategori_list)))

        with c3:
            sel_kats = st.multiselect(
                "🏷️ Filter Kategori:",
                options=kategori_options,
                default=[],
                placeholder="Semua Kategori...",
                key=f"rwe_sel_kats_{sel_sumber}"
            )
        with c4:
            raw_sups = extract_unique_suppliers(pd.concat([master_df, all_trx], ignore_index=True))
            sel_sup = st.selectbox("🏢 Filter Supplier:", ["Semua Supplier"] + raw_sups, key="rwe_sel_sup")
        with c5:
            search_q = st.text_input("🔍 Cari Barang / Tujuan / Ket:", placeholder="Ketik kata kunci...", key="rwe_search_q")

    if all_trx.empty:
        st.info("ℹ️ Belum ada data transaksi pengeluaran yang tersimpan.")
        return

    df_filtered = all_trx.copy()
    df_filtered['parsed_date'] = pd.to_datetime(df_filtered['tanggal'], errors='coerce').dt.date

    mask = (df_filtered['parsed_date'] >= k_start) & (df_filtered['parsed_date'] <= k_end)
    if sel_sumber != "Semua Pengeluaran":
        mask = mask & (df_filtered['sumber'] == sel_sumber)
    if sel_kats:
        mask = mask & (df_filtered['kategori'].astype(str).str.strip().isin(sel_kats))
    if sel_sup != "Semua Supplier":
        mask = mask & df_filtered['supplier'].apply(lambda x: match_supplier(x, sel_sup))
    if search_q:
        q_mask = (
            df_filtered['nama_barang'].astype(str).str.contains(search_q, case=False, na=False) |
            df_filtered['tujuan'].astype(str).str.contains(search_q, case=False, na=False) |
            df_filtered['kategori'].astype(str).str.contains(search_q, case=False, na=False) |
            df_filtered['keterangan'].astype(str).str.contains(search_q, case=False, na=False)
        )
        mask = mask & q_mask

    if sel_sumber == "Semua Pengeluaran":
        cat_order_map = {'PASIEN': 1, 'DOKTER': 2, 'MANAJEMEN': 3, 'KARYAWAN': 4}
        filtered_data = df_filtered[mask].copy()
        filtered_data['_sort_rank'] = filtered_data['_cat_type'].map(cat_order_map).fillna(99)
        filtered_data = filtered_data.sort_values(by=['_sort_rank', 'tanggal'], ascending=[True, False]).drop(columns=['_sort_rank'])
    else:
        filtered_data = df_filtered[mask].copy().sort_values(by='tanggal', ascending=False)
    tgl_info = k_start.strftime('%d %b %Y') if k_start == k_end else f"{k_start.strftime('%d %b %Y')} s/d {k_end.strftime('%d %b %Y')}"

    if filtered_data.empty:
        st.info(f"ℹ️ Tidak ditemukan riwayat pengeluaran pada periode **{tgl_info}** dengan filter yang dipilih.")
        return

    st.markdown("<br>", unsafe_allow_html=True)
    with st.container(border=True):
        col_t, col_exp = st.columns([3, 1])
        with col_t:
            st.markdown(f"#### 📊 Tabel Excel Riwayat Pengeluaran ({len(filtered_data)} Baris)")
            st.caption("Klik sel **Qty Keluar**, **Harga Real**, **Jml Pasien**, atau **Keterangan** untuk mengedit langsung. Centang kolom **Hapus** untuk menghapus transaksi:")
        # Penyesuaian kolom & konfigurasi berdasarkan Sumber Pengeluaran
        if sel_sumber == "🛏️ Pasien":
            cols_to_display = [
                'tanggal', 'shift', 'kategori', 'nama_barang', 
                'supplier', 'satuan', 'qty', 'harga_real', 'total_harga', 
                'jumlah_pasien', 'keterangan', 'hapus'
            ]
            column_config = {
                "tanggal": st.column_config.TextColumn("Tanggal", disabled=True, width="small"),
                "shift": st.column_config.TextColumn("Shift", disabled=True, width="small"),
                "kategori": st.column_config.TextColumn("Kelas Pasien", disabled=True, width="medium"),
                "nama_barang": st.column_config.TextColumn("Nama Barang", disabled=True, width="medium"),
                "supplier": st.column_config.TextColumn("Supplier", disabled=True, width="small"),
                "satuan": st.column_config.TextColumn("Satuan", disabled=True, width="small"),
                "qty": st.column_config.NumberColumn("Qty Keluar", min_value=0.0, step=0.05, format="%.2f", required=True),
                "harga_real": st.column_config.NumberColumn("Harga Real (Rp)", min_value=0, step=100, format="Rp %d", required=True),
                "total_harga": st.column_config.NumberColumn("Total Biaya (Rp)", format="Rp %d", disabled=True),
                "jumlah_pasien": st.column_config.NumberColumn("Jml Pasien", min_value=1, step=1, format="%d", required=True),
                "keterangan": st.column_config.TextColumn("Keterangan / Catatan"),
                "hapus": st.column_config.CheckboxColumn("Hapus 🗑️", help="Centang untuk menandai transaksi ini dihapus", default=False)
            }
        elif sel_sumber == "🩺 Dokter":
            cols_to_display = [
                'tanggal', 'shift', 'kategori', 'tujuan', 'nama_barang', 
                'supplier', 'satuan', 'qty', 'harga_real', 'total_harga', 
                'keterangan', 'hapus'
            ]
            column_config = {
                "tanggal": st.column_config.TextColumn("Tanggal", disabled=True, width="small"),
                "shift": st.column_config.TextColumn("Shift", disabled=True, width="small"),
                "kategori": st.column_config.TextColumn("Kategori", disabled=True, width="medium"),
                "tujuan": st.column_config.TextColumn("👨‍⚕️ Nama Dokter", disabled=True, width="medium"),
                "nama_barang": st.column_config.TextColumn("Nama Barang", disabled=True, width="medium"),
                "supplier": st.column_config.TextColumn("Supplier", disabled=True, width="small"),
                "satuan": st.column_config.TextColumn("Satuan", disabled=True, width="small"),
                "qty": st.column_config.NumberColumn("Qty Keluar", min_value=0.0, step=0.05, format="%.2f", required=True),
                "harga_real": st.column_config.NumberColumn("Harga Real (Rp)", min_value=0, step=100, format="Rp %d", required=True),
                "total_harga": st.column_config.NumberColumn("Total Biaya (Rp)", format="Rp %d", disabled=True),
                "keterangan": st.column_config.TextColumn("Keterangan / Catatan"),
                "hapus": st.column_config.CheckboxColumn("Hapus 🗑️", help="Centang untuk menandai transaksi ini dihapus", default=False)
            }
        elif sel_sumber == "🏢 Manajemen":
            cols_to_display = [
                'tanggal', 'shift', 'kategori', 'tujuan', 'nama_barang', 
                'supplier', 'satuan', 'qty', 'harga_real', 'total_harga', 
                'keterangan', 'hapus'
            ]
            column_config = {
                "tanggal": st.column_config.TextColumn("Tanggal", disabled=True, width="small"),
                "shift": st.column_config.TextColumn("Shift", disabled=True, width="small"),
                "kategori": st.column_config.TextColumn("Kategori", disabled=True, width="medium"),
                "tujuan": st.column_config.TextColumn("🏢 Keperluan / Divisi", disabled=True, width="medium"),
                "nama_barang": st.column_config.TextColumn("Nama Barang", disabled=True, width="medium"),
                "supplier": st.column_config.TextColumn("Supplier", disabled=True, width="small"),
                "satuan": st.column_config.TextColumn("Satuan", disabled=True, width="small"),
                "qty": st.column_config.NumberColumn("Qty Keluar", min_value=0.0, step=0.05, format="%.2f", required=True),
                "harga_real": st.column_config.NumberColumn("Harga Real (Rp)", min_value=0, step=100, format="Rp %d", required=True),
                "total_harga": st.column_config.NumberColumn("Total Biaya (Rp)", format="Rp %d", disabled=True),
                "keterangan": st.column_config.TextColumn("Keterangan / Catatan"),
                "hapus": st.column_config.CheckboxColumn("Hapus 🗑️", help="Centang untuk menandai transaksi ini dihapus", default=False)
            }
        elif sel_sumber == "👥 Karyawan":
            cols_to_display = [
                'tanggal', 'shift', 'kategori', 'tujuan', 'nama_barang', 
                'supplier', 'satuan', 'qty', 'harga_real', 'total_harga', 
                'keterangan', 'hapus'
            ]
            column_config = {
                "tanggal": st.column_config.TextColumn("Tanggal", disabled=True, width="small"),
                "shift": st.column_config.TextColumn("Shift", disabled=True, width="small"),
                "kategori": st.column_config.TextColumn("Kategori", disabled=True, width="medium"),
                "tujuan": st.column_config.TextColumn("👥 Nama Karyawan", disabled=True, width="medium"),
                "nama_barang": st.column_config.TextColumn("Nama Barang", disabled=True, width="medium"),
                "supplier": st.column_config.TextColumn("Supplier", disabled=True, width="small"),
                "satuan": st.column_config.TextColumn("Satuan", disabled=True, width="small"),
                "qty": st.column_config.NumberColumn("Qty Keluar", min_value=0.0, step=0.05, format="%.2f", required=True),
                "harga_real": st.column_config.NumberColumn("Harga Real (Rp)", min_value=0, step=100, format="Rp %d", required=True),
                "total_harga": st.column_config.NumberColumn("Total Biaya (Rp)", format="Rp %d", disabled=True),
                "keterangan": st.column_config.TextColumn("Keterangan / Catatan"),
                "hapus": st.column_config.CheckboxColumn("Hapus 🗑️", help="Centang untuk menandai transaksi ini dihapus", default=False)
            }
        else:
            cols_to_display = [
                'sumber', 'tanggal', 'shift', 'kategori', 'tujuan', 'nama_barang', 
                'supplier', 'satuan', 'qty', 'harga_real', 'total_harga', 
                'jumlah_pasien', 'keterangan', 'hapus'
            ]
            column_config = {
                "sumber": st.column_config.TextColumn("Sumber", disabled=True, width="small"),
                "tanggal": st.column_config.TextColumn("Tanggal", disabled=True, width="small"),
                "shift": st.column_config.TextColumn("Shift", disabled=True, width="small"),
                "kategori": st.column_config.TextColumn("Kategori / Kelas", disabled=True, width="medium"),
                "tujuan": st.column_config.TextColumn("Dokter / Tujuan", disabled=True, width="medium"),
                "nama_barang": st.column_config.TextColumn("Nama Barang", disabled=True, width="medium"),
                "supplier": st.column_config.TextColumn("Supplier", disabled=True, width="small"),
                "satuan": st.column_config.TextColumn("Satuan", disabled=True, width="small"),
                "qty": st.column_config.NumberColumn("Qty Keluar", min_value=0.0, step=0.05, format="%.2f", required=True),
                "harga_real": st.column_config.NumberColumn("Harga Real (Rp)", min_value=0, step=100, format="Rp %d", required=True),
                "total_harga": st.column_config.NumberColumn("Total Biaya (Rp)", format="Rp %d", disabled=True),
                "jumlah_pasien": st.column_config.NumberColumn("Jml Pasien", min_value=0, step=1, format="%d"),
                "keterangan": st.column_config.TextColumn("Keterangan / Catatan"),
                "hapus": st.column_config.CheckboxColumn("Hapus 🗑️", help="Centang untuk menandai transaksi ini dihapus", default=False)
            }

        # Siapkan dataframe untuk data editor
        df_editor_input = filtered_data.copy()
        df_editor_input = df_editor_input.set_index('_id')
        df_editor_input = df_editor_input[cols_to_display]

        with col_exp:
            csv_cols = [c for c in cols_to_display if c != 'hapus']
            csv_export = filtered_data[csv_cols]
            st.download_button(
                label=f"📥 Export Excel/CSV ({len(filtered_data)})",
                data=csv_export.to_csv(index=False).encode('utf-8'),
                file_name=f"Riwayat_Pengeluaran_{k_start}_sd_{k_end}.csv",
                mime="text/csv",
                use_container_width=True
            )

        kat_tag = "_".join(sorted(sel_kats)) if sel_kats else "all"
        editor_key = f"editor_pengeluaran_{k_start}_{k_end}_{sel_sumber}_{kat_tag}"

        # Sinkronisasi otomatis total_harga jika user mengubah harga_real atau qty di sel editor
        if editor_key in st.session_state and isinstance(st.session_state[editor_key], dict):
            edited_rows = st.session_state[editor_key].get('edited_rows', {})
            for row_pos_str, changes in list(edited_rows.items()):
                try:
                    row_pos = int(row_pos_str)
                    if 0 <= row_pos < len(df_editor_input):
                        orig_r = df_editor_input.iloc[row_pos]
                        q_val = float(changes.get('qty', orig_r.get('qty', 0)))
                        p_val = float(changes.get('harga_real', orig_r.get('harga_real', 0)))
                        changes['total_harga'] = q_val * p_val
                except (ValueError, TypeError, IndexError):
                    pass

        edited_df = st.data_editor(
            df_editor_input,
            use_container_width=True,
            hide_index=True,
            num_rows="dynamic",
            key=editor_key,
            column_config=column_config
        )

        # Pastikan nilai total_harga selalu tersinkronisasi dengan qty * harga_real
        edited_df['total_harga'] = edited_df['qty'] * edited_df['harga_real']

        # Analisis perubahan dan deteksi baris yang dihapus/diedit
        items_to_save_by_cat = {'PASIEN': [], 'DOKTER': [], 'MANAJEMEN': [], 'KARYAWAN': []}
        grand_old_total = float(df_editor_input['total_harga'].sum())
        grand_new_total = 0.0
        changed_count = 0
        deleted_count = 0

        # Baris yang dihapus via keyboard delete di data editor (hilang dari edited_df.index)
        deleted_ids_keyboard = set(df_editor_input.index) - set(edited_df.index)

        for _id, orig_row in df_editor_input.iterrows():
            c_type = filtered_data.loc[filtered_data['_id'] == _id, '_cat_type'].iloc[0]
            o_idx = int(filtered_data.loc[filtered_data['_id'] == _id, '_orig_idx'].iloc[0])
            
            old_q = float(orig_row['qty'])
            old_p = float(orig_row['harga_real'])
            old_tot = old_q * old_p
            old_pas = float(orig_row['jumlah_pasien']) if 'jumlah_pasien' in orig_row else float(filtered_data.loc[filtered_data['_id'] == _id, 'jumlah_pasien'].iloc[0])
            old_ket = str(orig_row['keterangan']).strip()

            if _id in deleted_ids_keyboard:
                # Dihapus lewat tombol delete baris
                deleted_count += 1
                items_to_save_by_cat[c_type].append({
                    'orig_idx': o_idx,
                    'nama_barang': orig_row['nama_barang'],
                    'supplier': orig_row['supplier'],
                    'kategori': orig_row['kategori'],
                    'old_qty': old_q,
                    'new_qty': 0.0,
                    'old_price': old_p,
                    'new_price': 0.0,
                    'old_total': old_tot,
                    'new_total': 0.0,
                    'new_pasien': 0,
                    'new_ket': '',
                    'is_deleted': True
                })
                continue

            # Ambil data terkini dari edited_df
            cur_row = edited_df.loc[_id]
            is_checked_del = bool(cur_row.get('hapus', False))

            if is_checked_del:
                deleted_count += 1
                items_to_save_by_cat[c_type].append({
                    'orig_idx': o_idx,
                    'nama_barang': orig_row['nama_barang'],
                    'supplier': orig_row['supplier'],
                    'kategori': orig_row['kategori'],
                    'old_qty': old_q,
                    'new_qty': 0.0,
                    'old_price': old_p,
                    'new_price': 0.0,
                    'old_total': old_tot,
                    'new_total': 0.0,
                    'new_pasien': 0,
                    'new_ket': '',
                    'is_deleted': True
                })
                continue

            cur_q = float(cur_row['qty'])
            cur_p = float(cur_row['harga_real'])
            cur_tot = cur_q * cur_p
            cur_pas = float(cur_row['jumlah_pasien']) if 'jumlah_pasien' in cur_row else old_pas
            cur_ket = str(cur_row.get('keterangan', '')).strip()

            grand_new_total += cur_tot

            is_modified = (
                abs(cur_q - old_q) > 1e-4 or
                abs(cur_p - old_p) > 1e-4 or
                abs(cur_pas - old_pas) > 1e-4 or
                cur_ket != old_ket
            )

            if is_modified:
                changed_count += 1
                items_to_save_by_cat[c_type].append({
                    'orig_idx': o_idx,
                    'nama_barang': orig_row['nama_barang'],
                    'supplier': orig_row['supplier'],
                    'kategori': orig_row['kategori'],
                    'old_qty': old_q,
                    'new_qty': cur_q,
                    'old_price': old_p,
                    'new_price': cur_p,
                    'old_total': old_tot,
                    'new_total': cur_tot,
                    'new_pasien': cur_pas,
                    'new_ket': cur_ket,
                    'is_deleted': False
                })

        total_actions = changed_count + deleted_count
        diff_total = grand_new_total - grand_old_total

        st.divider()
        col_calc, col_sub = st.columns([3, 1.4])
        with col_calc:
            if diff_total < 0:
                diff_tag = f"🟩 Hemat Rp {abs(diff_total):,.0f}"
            elif diff_total > 0:
                diff_tag = f"🟥 Naik +Rp {diff_total:,.0f}"
            else:
                diff_tag = "⚖️ Tetap"
            st.info(f"**Total Semula:** Rp {grand_old_total:,.0f} ➡️ **Total Baru:** Rp {grand_new_total:,.0f} &nbsp;|&nbsp; **{diff_tag}** ({changed_count} diubah, {deleted_count} dihapus)")

        with col_sub:
            btn_save = st.button("💾 Simpan Perubahan ke Database", type="primary", use_container_width=True, key="btn_save_rwe", disabled=(total_actions == 0))

        if btn_save:
            with st.spinner(f"Menyimpan pembaruan ({total_actions} baris diproses)..."):
                try:
                    execute_unified_pengeluaran_save(items_to_save_by_cat, master_df)
                except Exception as e:
                    st.error(f"Gagal menyimpan perubahan: {e}")

def render_riwayat_harga_excel(master_df):
    """Tampilan Tabel Excel untuk Riwayat Harga / Pembelian (Stok Masuk)."""
    today = datetime.date.today()
    trx_masuk_df = get_sheet_data(SHEET_STOK_MASUK)

    with st.container(border=True):
        c1, c2, c3 = st.columns([1.5, 1.5, 1.5])
        with c1:
            date_range = st.date_input("📅 Tanggal Pembelian:", value=(today, today), key="rhe_date_range")
            k_start, k_end = parse_date_range(date_range, today)
        with c2:
            raw_sups = extract_unique_suppliers(master_df)
            k_sup_opts = ["Semua Supplier"] + raw_sups
            selected_k_sup = st.selectbox("🏢 Filter Supplier:", k_sup_opts, key="rhe_filter_sup")
        with c3:
            k_search = st.text_input("🔍 Cari Barang / Nota:", placeholder="Ketik nama barang atau nota...", key="rhe_search_q")

    if trx_masuk_df.empty or 'tanggal' not in trx_masuk_df.columns:
        st.info("ℹ️ Belum ada data transaksi stok masuk / pembelian yang tersimpan.")
        return

    df_trx = trx_masuk_df.copy()
    df_trx['_orig_idx'] = df_trx.index
    df_trx['parsed_date'] = pd.to_datetime(df_trx['tanggal'], errors='coerce').dt.date

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
    tgl_info = k_start.strftime('%d %b %Y') if k_start == k_end else f"{k_start.strftime('%d %b %Y')} s/d {k_end.strftime('%d %b %Y')}"

    if filtered_trx.empty:
        st.info(f"ℹ️ Tidak ditemukan transaksi pembelian dari **{selected_k_sup}** pada periode **{tgl_info}**.")
        return

    st.markdown("<br>", unsafe_allow_html=True)
    with st.container(border=True):
        col_t, col_exp = st.columns([3, 1])
        with col_t:
            st.markdown(f"#### 🏷️ Tabel Excel Riwayat Harga & Pembelian ({len(filtered_trx)} Baris)")
            st.caption("Klik sel **Qty Masuk**, **Harga Real Beli**, atau **Keterangan** untuk mengedit langsung. Centang **Hapus** untuk menghapus riwayat:")
        with col_exp:
            csv_export = filtered_trx.drop(columns=['_orig_idx', 'parsed_date'], errors='ignore')
            st.download_button(
                label=f"📥 Export Excel/CSV ({len(filtered_trx)})",
                data=csv_export.to_csv(index=False).encode('utf-8'),
                file_name=f"Riwayat_Pembelian_{k_start}_sd_{k_end}.csv",
                mime="text/csv",
                use_container_width=True
            )

        df_editor_input = filtered_trx.copy()
        df_editor_input['hapus'] = False
        df_editor_input = df_editor_input.set_index('_orig_idx')

        cols_display = [
            'tanggal', 'shift', 'supplier', 'nama_barang', 'qty',
            'harga_master', 'harga_real', 'total_harga', 'keterangan', 'hapus'
        ]
        existing_cols = [c for c in cols_display if c in df_editor_input.columns]
        df_editor_input = df_editor_input[existing_cols]

        editor_key = f"editor_harga_{k_start}_{k_end}_{selected_k_sup}"

        # Sinkronisasi otomatis total_harga jika user mengubah harga_real atau qty di sel editor
        if editor_key in st.session_state and isinstance(st.session_state[editor_key], dict):
            edited_rows = st.session_state[editor_key].get('edited_rows', {})
            for row_pos_str, changes in list(edited_rows.items()):
                try:
                    row_pos = int(row_pos_str)
                    if 0 <= row_pos < len(df_editor_input):
                        orig_r = df_editor_input.iloc[row_pos]
                        q_val = float(changes.get('qty', orig_r.get('qty', 0)))
                        p_val = float(changes.get('harga_real', orig_r.get('harga_real', 0)))
                        changes['total_harga'] = q_val * p_val
                except (ValueError, TypeError, IndexError):
                    pass

        edited_df = st.data_editor(
            df_editor_input,
            use_container_width=True,
            hide_index=True,
            num_rows="dynamic",
            key=editor_key,
            column_config={
                "tanggal": st.column_config.TextColumn("Tanggal", disabled=True, width="small"),
                "shift": st.column_config.TextColumn("Shift", disabled=True, width="small"),
                "supplier": st.column_config.TextColumn("Supplier", disabled=True, width="medium"),
                "nama_barang": st.column_config.TextColumn("Nama Barang", disabled=True, width="medium"),
                "qty": st.column_config.NumberColumn("Qty Masuk", min_value=0.0, step=0.05, format="%.2f", required=True),
                "harga_master": st.column_config.NumberColumn("HPP Master (Rp)", format="Rp %d", disabled=True),
                "harga_real": st.column_config.NumberColumn("Harga Real Beli (Rp)", min_value=0, step=100, format="Rp %d", required=True),
                "total_harga": st.column_config.NumberColumn("Total Beli (Rp)", format="Rp %d", disabled=True),
                "keterangan": st.column_config.TextColumn("Nota / Keterangan"),
                "hapus": st.column_config.CheckboxColumn("Hapus 🗑️", help="Centang untuk menghapus transaksi ini", default=False)
            }
        )

        # Pastikan nilai total_harga selalu tersinkronisasi dengan qty * harga_real
        edited_df['total_harga'] = edited_df['qty'] * edited_df['harga_real']

        items_to_save = []
        grand_old_total = float(df_editor_input['total_harga'].sum()) if 'total_harga' in df_editor_input.columns else 0.0
        grand_new_total = 0.0
        changed_count = 0
        deleted_count = 0

        deleted_indices_keyboard = set(df_editor_input.index) - set(edited_df.index)

        for o_idx, orig_row in df_editor_input.iterrows():
            old_q = float(orig_row['qty']) if pd.notna(orig_row['qty']) else 0.0
            old_p = float(orig_row['harga_real']) if pd.notna(orig_row['harga_real']) else 0.0
            old_tot = old_q * old_p
            old_ket = str(orig_row.get('keterangan', '')).strip()

            if o_idx in deleted_indices_keyboard:
                deleted_count += 1
                items_to_save.append({
                    'orig_idx': o_idx,
                    'nama_barang': orig_row['nama_barang'],
                    'supplier': orig_row['supplier'],
                    'old_qty': old_q,
                    'new_qty': 0.0,
                    'old_price': old_p,
                    'new_price': 0.0,
                    'old_total': old_tot,
                    'new_total': 0.0,
                    'keterangan': '',
                    'is_deleted': True
                })
                continue

            cur_row = edited_df.loc[o_idx]
            is_checked_del = bool(cur_row.get('hapus', False))

            if is_checked_del:
                deleted_count += 1
                items_to_save.append({
                    'orig_idx': o_idx,
                    'nama_barang': orig_row['nama_barang'],
                    'supplier': orig_row['supplier'],
                    'old_qty': old_q,
                    'new_qty': 0.0,
                    'old_price': old_p,
                    'new_price': 0.0,
                    'old_total': old_tot,
                    'new_total': 0.0,
                    'keterangan': '',
                    'is_deleted': True
                })
                continue

            cur_q = float(cur_row['qty'])
            cur_p = float(cur_row['harga_real'])
            cur_tot = cur_q * cur_p
            cur_ket = str(cur_row.get('keterangan', '')).strip()

            grand_new_total += cur_tot

            is_modified = (
                abs(cur_q - old_q) > 1e-4 or
                abs(cur_p - old_p) > 1e-4 or
                cur_ket != old_ket
            )

            if is_modified:
                changed_count += 1
                items_to_save.append({
                    'orig_idx': o_idx,
                    'nama_barang': orig_row['nama_barang'],
                    'supplier': orig_row['supplier'],
                    'old_qty': old_q,
                    'new_qty': cur_q,
                    'old_price': old_p,
                    'new_price': cur_p,
                    'old_total': old_tot,
                    'new_total': cur_tot,
                    'keterangan': cur_ket,
                    'is_deleted': False
                })

        total_actions = changed_count + deleted_count
        diff_total = grand_new_total - grand_old_total

        st.divider()
        col_calc, col_opt, col_sub = st.columns([2.5, 1.5, 1.5])
        with col_calc:
            if diff_total < 0:
                diff_tag = f"🟩 Hemat Rp {abs(diff_total):,.0f}"
            elif diff_total > 0:
                diff_tag = f"🟥 Naik +Rp {diff_total:,.0f}"
            else:
                diff_tag = "⚖️ Tetap"
            st.info(f"**Total Semula:** Rp {grand_old_total:,.0f} ➡️ **Total Baru:** Rp {grand_new_total:,.0f} &nbsp;|&nbsp; **{diff_tag}** ({changed_count} diubah, {deleted_count} dihapus)")

        with col_opt:
            update_hpp_master = st.checkbox(
                "🔄 Sekaligus update HPP Master",
                value=False,
                key="rhe_update_hpp_master",
                help="Jika dicentang, harga real baru yang diubah akan otomatis dijadikan harga acuan HPP di Master Barang."
            )

        with col_sub:
            btn_save = st.button("💾 Simpan Perubahan Harga", type="primary", use_container_width=True, key="btn_save_rhe", disabled=(total_actions == 0))

        if btn_save:
            for it in items_to_save:
                it['update_hpp'] = update_hpp_master
            with st.spinner(f"Menyimpan pembaruan ({total_actions} baris diproses)..."):
                try:
                    execute_koreksi_pembelian_save(items_to_save, master_df)
                except Exception as e:
                    st.error(f"Gagal menyimpan perubahan harga: {e}")

def show_riwayat_pengeluaran():
    """Halaman tunggal Riwayat Data & Koreksi dengan 2 paginasi/tab Excel: Riwayat Pengeluaran & Riwayat Harga."""
    st.title("📋 Riwayat Data & Koreksi (Excel View)")
    st.caption("Kelola, koreksi harga/qty, atau hapus data riwayat transaksi pengeluaran dan harga pembelian dengan antarmuka tabel spreadsheet interaktif:")

    if 'toast_msg_riwayat_pengeluaran' in st.session_state:
        show_toast(st.session_state.pop('toast_msg_riwayat_pengeluaran'))

    master_df = get_sheet_data(SHEET_MASTER)

    tab_pengeluaran, tab_harga = st.tabs([
        "📤 1. Riwayat Pengeluaran (Pasien, Dokter, Manajemen)",
        "🏷️ 2. Riwayat Harga (Pembelian / Stok Masuk)"
    ])

    with tab_pengeluaran:
        render_riwayat_pengeluaran_excel(master_df)

    with tab_harga:
        render_riwayat_harga_excel(master_df)
