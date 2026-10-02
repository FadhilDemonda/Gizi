"""
==========================================================
STOK GIZI RS AN-NISA - HEALTH CHECK & PRE-FLIGHT TEST
==========================================================
Script ini TIDAK mengubah data apapun di Google Sheets.
Hanya membaca dan memvalidasi integritas seluruh komponen.

Cara pakai:
    python tests/health_check.py

Hasil: Laporan lengkap di terminal dengan status PASS / FAIL / WARN
==========================================================
"""

import sys
import os
import time

# Tambahkan root project ke path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import toml
import gspread
import pandas as pd

# ============================
# KONFIGURASI
# ============================
SECRETS_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".streamlit", "secrets.toml")

REQUIRED_TABS = [
    "master_barang",
    "master_dokter",
    "stok_masuk",
    "pengeluaran_pasien",
    "pengeluaran_dokter",
    "pengeluaran_manajemen",
    "log"
]

MASTER_REQUIRED_COLUMNS = [
    "kode_barang", "nama_barang", "kategori", "satuan",
    "stok_sekarang", "stok_minimum", "harga_master", "status"
]

TRX_REQUIRED_COLUMNS = {
    "stok_masuk": ["tanggal", "nama_barang", "qty", "harga_real"],
    "pengeluaran_pasien": ["tanggal", "nama_barang", "qty"],
    "pengeluaran_dokter": ["tanggal", "nama_barang", "qty"],
    "pengeluaran_manajemen": ["tanggal", "nama_barang", "qty"],
}

# ============================
# UTILITIES
# ============================
passed = 0
failed = 0
warnings = 0

def ok(msg):
    global passed
    passed += 1
    print(f"  [PASS]  {msg}")

def fail(msg):
    global failed
    failed += 1
    print(f"  [FAIL]  {msg}")

def warn(msg):
    global warnings
    warnings += 1
    print(f"  [WARN]  {msg}")

def info(msg):
    print(f"  [INFO]  {msg}")

def section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

def safe_float(val):
    try:
        if pd.isna(val) or val == "":
            return 0.0
        return float(str(val).replace(',', '.'))
    except Exception:
        return 0.0

# ============================
# TESTS
# ============================

def test_secrets_file():
    section("1. CEK KONFIGURASI (secrets.toml)")
    if not os.path.exists(SECRETS_PATH):
        fail(f"File secrets.toml TIDAK ditemukan di {SECRETS_PATH}")
        return None
    ok("File secrets.toml ditemukan")
    try:
        secrets = toml.load(SECRETS_PATH)
    except Exception as e:
        fail(f"Gagal parse secrets.toml: {e}")
        return None
    ok("Format TOML valid")
    if "gcp_service_account" not in secrets:
        fail("Bagian [gcp_service_account] tidak ada")
        return None
    ok("Bagian [gcp_service_account] ada")
    if "google_sheets" not in secrets:
        fail("Bagian [google_sheets] tidak ada")
        return None
    ok("Bagian [google_sheets] ada")
    url = secrets.get("google_sheets", {}).get("url", "")
    if "docs.google.com/spreadsheets" not in url:
        fail(f"URL Google Sheets tidak valid: {url}")
        return None
    ok("URL Google Sheets valid")
    required_keys = ["type", "project_id", "private_key", "client_email"]
    for key in required_keys:
        if key not in secrets["gcp_service_account"]:
            fail(f"Key '{key}' tidak ada di [gcp_service_account]")
        else:
            ok(f"Key '{key}' tersedia")
    return secrets


def test_connection(secrets):
    section("2. CEK KONEKSI GOOGLE SHEETS API")
    try:
        start = time.time()
        gc = gspread.service_account_from_dict(secrets["gcp_service_account"])
        elapsed = time.time() - start
        ok(f"Autentikasi GCP berhasil ({elapsed:.1f}s)")
    except Exception as e:
        fail(f"Autentikasi GCP GAGAL: {e}")
        return None, None
    try:
        start = time.time()
        sh = gc.open_by_url(secrets["google_sheets"]["url"])
        elapsed = time.time() - start
        ok(f"Spreadsheet '{sh.title}' berhasil dibuka ({elapsed:.1f}s)")
    except Exception as e:
        fail(f"Gagal membuka spreadsheet: {e}")
        return None, None
    return gc, sh


def test_tabs(sh):
    section("3. CEK TAB/WORKSHEET YANG DIBUTUHKAN")
    existing_tabs = [ws.title for ws in sh.worksheets()]
    info(f"Tab yang ditemukan: {existing_tabs}")
    all_data = {}
    for tab in REQUIRED_TABS:
        if tab in existing_tabs:
            try:
                ws = sh.worksheet(tab)
                records = ws.get_all_records(numericise_ignore=["all"])
                df = pd.DataFrame(records)
                all_data[tab] = df
                ok(f"Tab '{tab}' -> {len(df)} baris data")
            except Exception as e:
                fail(f"Tab '{tab}' ada tapi gagal dibaca: {e}")
                all_data[tab] = pd.DataFrame()
        else:
            fail(f"Tab '{tab}' TIDAK ditemukan!")
            all_data[tab] = pd.DataFrame()
    return all_data


def test_master_integrity(all_data):
    section("4. CEK INTEGRITAS MASTER BARANG")
    df = all_data.get("master_barang", pd.DataFrame())
    if df.empty:
        fail("Master Barang kosong!")
        return
    ok(f"Master Barang memiliki {len(df)} item")
    for col in MASTER_REQUIRED_COLUMNS:
        if col in df.columns:
            ok(f"Kolom '{col}' ada")
        else:
            fail(f"Kolom '{col}' TIDAK ADA!")
    if "kode_barang" in df.columns:
        dupes = df[df["kode_barang"].duplicated(keep=False)]
        if len(dupes) > 0:
            fail(f"Ada {len(dupes)} kode barang DUPLIKAT: {dupes['kode_barang'].tolist()}")
        else:
            ok("Tidak ada kode barang duplikat")
    if "nama_barang" in df.columns:
        dupes = df[df["nama_barang"].duplicated(keep=False)]
        if len(dupes) > 0:
            fail(f"Ada {len(dupes)} nama barang DUPLIKAT: {dupes['nama_barang'].tolist()}")
        else:
            ok("Tidak ada nama barang duplikat")
    if "stok_sekarang" in df.columns:
        df["_stok_num"] = df["stok_sekarang"].apply(safe_float)
        negatif = df[df["_stok_num"] < 0]
        if len(negatif) > 0:
            fail(f"Ada {len(negatif)} barang dengan STOK NEGATIF:")
            for _, row in negatif.iterrows():
                print(f"         -> {row.get('nama_barang', '?')}: {row['_stok_num']}")
        else:
            ok("Tidak ada stok negatif")
    if "harga_master" in df.columns:
        df["_harga_num"] = df["harga_master"].apply(safe_float)
        nol_harga = df[df["_harga_num"] == 0]
        if len(nol_harga) > 0:
            warn(f"Ada {len(nol_harga)} barang dengan harga master Rp 0:")
            for _, row in nol_harga.iterrows():
                print(f"         -> {row.get('nama_barang', '?')}")
        else:
            ok("Semua barang memiliki harga master > 0")
    if "stok_minimum" in df.columns and "status" in df.columns:
        df["_min_num"] = df["stok_minimum"].apply(safe_float)
        zero_min = df[df["_min_num"] == 0]
        info(f"{len(zero_min)} barang memiliki stok_minimum = 0 (Bahan Bebas / Tidak Dimonitor)")
    if "nama_barang" in df.columns:
        empty_names = df[df["nama_barang"].astype(str).str.strip() == ""]
        if len(empty_names) > 0:
            fail(f"Ada {len(empty_names)} baris dengan nama barang KOSONG!")
        else:
            ok("Semua baris memiliki nama barang terisi")
    if "satuan" in df.columns:
        empty_satuan = df[df["satuan"].astype(str).str.strip() == ""]
        if len(empty_satuan) > 0:
            warn(f"Ada {len(empty_satuan)} barang TANPA satuan:")
            for _, row in empty_satuan.head(5).iterrows():
                print(f"         -> {row.get('nama_barang', '?')}")
        else:
            ok("Semua barang memiliki satuan terisi")
    if "kategori" in df.columns:
        empty_kat = df[df["kategori"].astype(str).str.strip() == ""]
        if len(empty_kat) > 0:
            warn(f"Ada {len(empty_kat)} barang TANPA kategori")
        else:
            ok("Semua barang memiliki kategori terisi")
        kats = df["kategori"].dropna().unique().tolist()
        kats = [k for k in kats if str(k).strip() != ""]
        info(f"Kategori ditemukan: {kats}")


def test_transaction_integrity(all_data):
    section("5. CEK INTEGRITAS DATA TRANSAKSI")
    master_df = all_data.get("master_barang", pd.DataFrame())
    master_items = master_df["nama_barang"].tolist() if "nama_barang" in master_df.columns else []
    for tab_name, required_cols in TRX_REQUIRED_COLUMNS.items():
        df = all_data.get(tab_name, pd.DataFrame())
        if df.empty:
            info(f"Tab '{tab_name}' kosong (belum ada transaksi)")
            continue
        ok(f"Tab '{tab_name}' -> {len(df)} transaksi")
        missing_cols = [c for c in required_cols if c not in df.columns]
        if missing_cols:
            fail(f"  Tab '{tab_name}' KEHILANGAN kolom: {missing_cols}")
        else:
            ok(f"  Semua kolom wajib tersedia")
        if "tanggal" in df.columns:
            df["_tgl"] = pd.to_datetime(df["tanggal"], errors="coerce")
            invalid_dates = df[df["_tgl"].isna()]
            if len(invalid_dates) > 0:
                warn(f"  {len(invalid_dates)} baris memiliki tanggal TIDAK VALID di '{tab_name}'")
            else:
                ok(f"  Semua tanggal valid")
            tgl_min = df["_tgl"].min()
            tgl_max = df["_tgl"].max()
            if pd.notna(tgl_min) and pd.notna(tgl_max):
                info(f"  Rentang data: {tgl_min.strftime('%Y-%m-%d')} s/d {tgl_max.strftime('%Y-%m-%d')}")
        if "nama_barang" in df.columns and master_items:
            trx_items = df["nama_barang"].unique().tolist()
            orphans = [item for item in trx_items if item not in master_items]
            if orphans:
                warn(f"  {len(orphans)} item transaksi TIDAK ADA di Master Barang:")
                for orphan in orphans[:10]:
                    print(f"         -> '{orphan}'")
            else:
                ok(f"  Semua item transaksi terdaftar di Master Barang")
        if "qty" in df.columns:
            df["_qty_num"] = df["qty"].apply(safe_float)
            neg_qty = df[df["_qty_num"] < 0]
            if len(neg_qty) > 0:
                fail(f"  {len(neg_qty)} transaksi memiliki qty NEGATIF di '{tab_name}'!")
            else:
                ok(f"  Tidak ada qty negatif")


def test_stock_calculation(all_data):
    section("6. CEK KONSISTENSI PERHITUNGAN STOK (SAMPLING)")
    master_df = all_data.get("master_barang", pd.DataFrame())
    masuk_df = all_data.get("stok_masuk", pd.DataFrame())
    pasien_df = all_data.get("pengeluaran_pasien", pd.DataFrame())
    dokter_df = all_data.get("pengeluaran_dokter", pd.DataFrame())
    manajemen_df = all_data.get("pengeluaran_manajemen", pd.DataFrame())
    if master_df.empty:
        warn("Master Barang kosong, tidak bisa cross-check stok")
        return
    if masuk_df.empty and pasien_df.empty and dokter_df.empty and manajemen_df.empty:
        info("Belum ada transaksi, skip cross-check stok")
        return
    def sum_qty(df, item_name):
        if df.empty or "nama_barang" not in df.columns or "qty" not in df.columns:
            return 0.0
        subset = df[df["nama_barang"] == item_name]
        return subset["qty"].apply(safe_float).sum()
    master_df["_stok_num"] = master_df["stok_sekarang"].apply(safe_float)
    sample_items = pd.concat([
        master_df.nlargest(5, "_stok_num"),
        master_df.nsmallest(5, "_stok_num")
    ]).drop_duplicates(subset=["nama_barang"])
    info(f"Melakukan spot-check pada {len(sample_items)} barang sampel...")
    anomaly_count = 0
    for _, row in sample_items.iterrows():
        nama = row["nama_barang"]
        stok_sekarang = safe_float(row["stok_sekarang"])
        total_masuk = sum_qty(masuk_df, nama)
        total_keluar = (
            sum_qty(pasien_df, nama) +
            sum_qty(dokter_df, nama) +
            sum_qty(manajemen_df, nama)
        )
        if stok_sekarang < 0:
            fail(f"  '{nama}': Stok negatif ({stok_sekarang})")
            anomaly_count += 1
        else:
            net = total_masuk - total_keluar
            info(f"  '{nama}': Stok={stok_sekarang}, Masuk={total_masuk}, Keluar={total_keluar}, Net Trx={net:.1f}")
    if anomaly_count == 0:
        ok("Tidak ditemukan anomali stok negatif pada sampel")


def test_master_dokter(all_data):
    section("7. CEK MASTER DOKTER")
    df = all_data.get("master_dokter", pd.DataFrame())
    if df.empty:
        warn("Master Dokter kosong")
        return
    ok(f"Master Dokter memiliki {len(df)} entri")
    if "nama_dokter" in df.columns:
        dupes = df[df["nama_dokter"].duplicated(keep=False)]
        if len(dupes) > 0:
            warn(f"Ada nama dokter duplikat: {dupes['nama_dokter'].tolist()}")
        else:
            ok("Tidak ada nama dokter duplikat")
    else:
        warn("Kolom 'nama_dokter' tidak ditemukan")


def test_python_imports():
    section("8. CEK IMPORT MODUL PYTHON (Syntax Check)")
    modules = [
        ("app", "app.py"),
        ("styles.theme", "styles/theme.py"),
        ("utils.state", "utils/state.py"),
        ("utils.validators", "utils/validators.py"),
        ("utils.formatting", "utils/formatting.py"),
        ("data.sheets_repository", "data/sheets_repository.py"),
        ("services.stock_service", "services/stock_service.py"),
        ("services.transaction_service", "services/transaction_service.py"),
        ("services.report_service", "services/report_service.py"),
        ("views.dashboard", "views/dashboard.py"),
        ("views.master_barang", "views/master_barang.py"),
        ("views.master_dokter", "views/master_dokter.py"),
        ("views.transaksi", "views/transaksi.py"),
        ("views.pengeluaran", "views/pengeluaran.py"),
        ("views.pengeluaran_pasien", "views/pengeluaran_pasien.py"),
        ("views.pengeluaran_dokter", "views/pengeluaran_dokter.py"),
        ("views.pengeluaran_common", "views/pengeluaran_common.py"),
        ("views.laporan_harian", "views/laporan_harian.py"),
        ("views.analisis_stok", "views/analisis_stok.py"),
        ("views.riwayat_pengeluaran", "views/riwayat_pengeluaran.py"),
    ]
    for mod_name, file_path in modules:
        full_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), file_path)
        if not os.path.exists(full_path):
            warn(f"File '{file_path}' tidak ada, skip")
            continue
        try:
            import py_compile
            py_compile.compile(full_path, doraise=True)
            ok(f"{file_path} -> syntax OK")
        except py_compile.PyCompileError as e:
            fail(f"{file_path} -> SYNTAX ERROR: {e}")


def test_business_rules(all_data):
    section("9. CEK ATURAN BISNIS")
    master_df = all_data.get("master_barang", pd.DataFrame())
    if master_df.empty:
        warn("Master Barang kosong, skip business rules")
        return
    if "stok_sekarang" in master_df.columns and "stok_minimum" in master_df.columns:
        master_df["_stok"] = master_df["stok_sekarang"].apply(safe_float)
        master_df["_min"] = master_df["stok_minimum"].apply(safe_float)
        if "status" in master_df.columns:
            monitored = master_df[master_df["status"].astype(str).str.upper().isin(["TRUE", "1", "YES", "T"])]
        else:
            monitored = master_df
        krisis = monitored[monitored["_stok"] < monitored["_min"]]
        mendekati = monitored[(monitored["_stok"] >= monitored["_min"]) & (monitored["_stok"] <= monitored["_min"] * 1.25)]
        aman = monitored[(monitored["_stok"] > monitored["_min"] * 1.25)]
        habis = krisis[krisis["_stok"] == 0]
        if len(habis) > 0:
            warn(f"STOK HABIS: {len(habis)} barang habis (stok = 0):")
            for _, row in habis.iterrows():
                print(f"         -> {row.get('nama_barang', '?')}")
        if len(krisis) > 0:
            warn(f"KRITIS: {len(krisis)} barang dengan stok di bawah minimum:")
            for _, row in krisis.head(10).iterrows():
                print(f"         -> {row.get('nama_barang', '?')}: {row['_stok']:.0f} / min {row['_min']:.0f}")
        info(f"Ringkasan Status Stok: Aman={len(aman)}, Mendekati={len(mendekati)}, Kritis={len(krisis)}")
    for tab_name in ["stok_masuk", "pengeluaran_dokter", "pengeluaran_manajemen"]:
        df = all_data.get(tab_name, pd.DataFrame())
        if df.empty or "total_harga" not in df.columns:
            continue
        df["_total"] = df["total_harga"].apply(safe_float)
        outliers = df[df["_total"] > 10_000_000]
        if len(outliers) > 0:
            warn(f"Tab '{tab_name}': {len(outliers)} transaksi dengan total > Rp 10.000.000 (perlu dicek manual)")
        else:
            ok(f"Tab '{tab_name}': Tidak ada transaksi dengan total harga janggal")


def test_edge_cases(all_data):
    section("10. SIMULASI EDGE CASE & POTENSI CRASH")
    master_df = all_data.get("master_barang", pd.DataFrame())
    if master_df.empty:
        warn("Master Barang kosong, skip edge case test")
        return
    items = master_df["nama_barang"].tolist() if "nama_barang" in master_df.columns else []
    if len(items) == 0:
        fail("item_options KOSONG -> selectbox di form akan crash!")
    else:
        ok(f"item_options tersedia ({len(items)} barang) -> selectbox aman")
    if "nama_barang" in master_df.columns:
        lower_names = [str(x).lower().strip() for x in items]
        case_dupes = set()
        for i, name in enumerate(lower_names):
            for j in range(i + 1, len(lower_names)):
                if name == lower_names[j] and items[i] != items[j]:
                    case_dupes.add((items[i], items[j]))
        if case_dupes:
            warn(f"Ada nama barang yang mirip (beda huruf besar/kecil):")
            for a, b in case_dupes:
                print(f"         -> '{a}' vs '{b}'")
        else:
            ok("Tidak ada ambiguitas nama barang (case-insensitive)")
    if "stok_minimum" in master_df.columns and "status" in master_df.columns:
        monitored_no_min = master_df[
            (master_df["status"].astype(str).str.upper().isin(["TRUE", "1", "YES", "T"])) &
            (master_df["stok_minimum"].apply(safe_float) == 0)
        ]
        if len(monitored_no_min) > 0:
            warn(f"{len(monitored_no_min)} barang berstatus 'Dimonitor' tapi stok_minimum = 0:")
            for _, row in monitored_no_min.head(5).iterrows():
                print(f"         -> {row.get('nama_barang', '?')}")
        else:
            ok("Semua barang termonitor memiliki stok_minimum > 0")
    if "nama_barang" in master_df.columns:
        problematic = master_df[master_df["nama_barang"].astype(str).str.contains(r'[<>{}|\\"]', regex=True, na=False)]
        if len(problematic) > 0:
            warn(f"{len(problematic)} nama barang mengandung karakter spesial:")
            for _, row in problematic.iterrows():
                print(f"         -> '{row['nama_barang']}'")
        else:
            ok("Tidak ada karakter spesial berbahaya di nama barang")
    if "harga_master" in master_df.columns:
        bad_prices = []
        for idx, val in master_df["harga_master"].items():
            try:
                float(str(val).replace(',', '.'))
            except ValueError:
                bad_prices.append((master_df.at[idx, "nama_barang"], val))
        if bad_prices:
            fail(f"{len(bad_prices)} barang memiliki harga_master yang TIDAK BISA dikonversi:")
            for name, val in bad_prices[:5]:
                print(f"         -> '{name}': '{val}'")
        else:
            ok("Semua harga_master bisa dikonversi ke angka")


# ============================
# MAIN
# ============================
def main():
    print(f"\n{'='*60}")
    print(f"  STOK GIZI RS AN-NISA TANGERANG")
    print(f"  HEALTH CHECK & PRE-FLIGHT TEST")
    print(f"  Waktu: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")
    secrets = test_secrets_file()
    if not secrets:
        print(f"\n[STOP] Konfigurasi dasar gagal!")
        return
    gc, sh = test_connection(secrets)
    if not sh:
        print(f"\n[STOP] Koneksi ke Google Sheets gagal! Cek internet.")
        return
    all_data = test_tabs(sh)
    test_master_integrity(all_data)
    test_transaction_integrity(all_data)
    test_stock_calculation(all_data)
    test_master_dokter(all_data)
    test_python_imports()
    test_business_rules(all_data)
    test_edge_cases(all_data)

    section("RINGKASAN HASIL")
    total = passed + failed + warnings
    print(f"  Total pengecekan : {total}")
    print(f"  PASS (Lulus)     : {passed}")
    print(f"  WARN (Peringatan): {warnings}")
    print(f"  FAIL (Gagal)     : {failed}")
    print()
    if failed == 0 and warnings == 0:
        print(f"  SEMPURNA! Aplikasi siap digunakan oleh user.")
    elif failed == 0:
        print(f"  Aplikasi AMAN digunakan, tapi ada {warnings} peringatan ringan.")
        print(f"  Peringatan ini tidak akan menyebabkan crash, tapi sebaiknya diperbaiki.")
    else:
        print(f"  Ada {failed} MASALAH yang harus diperbaiki sebelum go-live!")
        print(f"  Hubungi Tim DTO untuk penanganan.")
    print(f"\n{'='*60}\n")


if __name__ == "__main__":
    main()
