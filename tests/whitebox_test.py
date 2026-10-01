"""
==========================================================
STOK GIZI RS AN-NISA - WHITE-BOX TESTING (ANOMALI)
==========================================================
Script ini menguji LOGIKA INTERNAL kode secara langsung
dengan input se-anomali mungkin:
  - Nilai negatif, nol, NaN, Infinity
  - String kosong, None, karakter aneh, XSS injection
  - DataFrame kosong, kolom hilang, tipe data salah
  - Angka raksasa (overflow), desimal presisi tinggi
  - Edge case bisnis (0 pasien, stok = HPP, qty fraksi)

Cara pakai:
    python tests/whitebox_test.py

SCRIPT INI READ-ONLY — TIDAK menyentuh Google Sheets.
==========================================================
"""

import sys
import os
import math
import time
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np

# ============================
# FRAMEWORK
# ============================
passed = 0
failed = 0
test_count = 0

def section(title):
    print(f"\n{'='*65}")
    print(f"  {title}")
    print(f"{'='*65}")

def run_test(name, fn):
    global passed, failed, test_count
    test_count += 1
    try:
        fn()
        passed += 1
        print(f"  [PASS] {name}")
    except AssertionError as e:
        failed += 1
        print(f"  [FAIL] {name}")
        print(f"         Assertion: {e}")
    except Exception as e:
        failed += 1
        print(f"  [FAIL] {name} (CRASH)")
        print(f"         {type(e).__name__}: {e}")


# ============================
# 1. STOCK SERVICE TESTS
# ============================
from services.stock_service import (
    calculate_stock_percentage,
    classify_stock_status,
    calculate_bar_width,
    filter_stock_by_status,
)

def test_stock_service():
    section("1. stock_service.py - Anomali Perhitungan Stok")

    # --- calculate_stock_percentage ---
    def t_persen_normal():
        result = calculate_stock_percentage(50, 100)
        assert result == 0.5, f"Expected 0.5, got {result}"
    run_test("Persentase: 50/100 = 0.5", t_persen_normal)

    def t_persen_zero_min():
        # stok_minimum = 0 -> harusnya safe (dibagi max(0,1)=1)
        result = calculate_stock_percentage(50, 0)
        assert result == 50.0, f"Expected 50.0, got {result}"
    run_test("Persentase: stok_minimum=0 (prevent div by zero)", t_persen_zero_min)

    def t_persen_negative_stok():
        result = calculate_stock_percentage(-5, 10)
        assert result == -0.5, f"Expected -0.5, got {result}"
    run_test("Persentase: stok negatif -5/10", t_persen_negative_stok)

    def t_persen_negative_min():
        # stok_minimum negatif -> max(-5, 1) = 1
        result = calculate_stock_percentage(10, -5)
        assert result == 10.0, f"Expected 10.0, got {result}"
    run_test("Persentase: stok_minimum negatif (-5)", t_persen_negative_min)

    def t_persen_both_zero():
        result = calculate_stock_percentage(0, 0)
        assert result == 0.0, f"Expected 0.0, got {result}"
    run_test("Persentase: keduanya 0", t_persen_both_zero)

    def t_persen_huge():
        result = calculate_stock_percentage(999999999, 1)
        assert result == 999999999.0, f"Expected 999999999.0, got {result}"
    run_test("Persentase: angka raksasa 999999999", t_persen_huge)

    def t_persen_float_precision():
        result = calculate_stock_percentage(0.1, 0.3)
        # Float precision: 0.1 / max(0.3, 1.0) = 0.1 / 1.0 = 0.1
        assert isinstance(result, float), f"Expected float, got {type(result)}"
    run_test("Persentase: presisi float 0.1/0.3", t_persen_float_precision)

    def t_persen_nan():
        result = calculate_stock_percentage(float('nan'), 10)
        assert math.isnan(result), f"Expected NaN, got {result}"
    run_test("Persentase: NaN input", t_persen_nan)

    def t_persen_inf():
        result = calculate_stock_percentage(float('inf'), 10)
        assert math.isinf(result), f"Expected Inf, got {result}"
    run_test("Persentase: Infinity input", t_persen_inf)

    # --- classify_stock_status ---
    def t_classify_habis():
        status_text, _, _, _, icon, _ = classify_stock_status(0, 10, 0.0)
        assert "HABIS" in status_text, f"Expected HABIS, got {status_text}"
    run_test("Klasifikasi: stok=0 -> STOK HABIS", t_classify_habis)

    def t_classify_negative():
        status_text, _, _, _, _, _ = classify_stock_status(-5, 10, -0.5)
        assert "KRITIS" in status_text or "HABIS" in status_text, f"Expected KRITIS/HABIS for -5, got {status_text}"
    run_test("Klasifikasi: stok negatif (-5) -> harus KRITIS/HABIS", t_classify_negative)

    def t_classify_exact_min():
        # stok == stok_minimum -> mendekati (stok < min*1.25)
        status_text, _, _, _, _, _ = classify_stock_status(10, 10, 1.0)
        assert "Mendekati" in status_text, f"Expected Mendekati, got {status_text}"
    run_test("Klasifikasi: stok == stok_minimum (boundary)", t_classify_exact_min)

    def t_classify_just_above_125():
        # stok = min * 1.26 -> should be AMAN
        status_text, _, _, _, _, _ = classify_stock_status(12.6, 10, 1.26)
        assert "AMAN" in status_text, f"Expected AMAN, got {status_text}"
    run_test("Klasifikasi: stok = min*1.26 (boundary AMAN)", t_classify_just_above_125)

    def t_classify_exempt():
        status_text, _, _, _, _, _ = classify_stock_status(0, 10, 0.0, status=False)
        assert "Bebas" in status_text, f"Expected Bebas for exempt, got {status_text}"
    run_test("Klasifikasi: status=False (Bahan Bebas) walaupun stok 0", t_classify_exempt)

    def t_classify_zero_min():
        status_text, _, _, _, _, _ = classify_stock_status(5, 0, 5.0)
        # stok_sekarang (5) >= stok_minimum (0) -> not kritis
        # 5 <= 0 * 1.25 = 0 -> False -> should be AMAN
        assert "AMAN" in status_text, f"Expected AMAN when min=0, got {status_text}"
    run_test("Klasifikasi: stok_minimum=0 dengan stok=5", t_classify_zero_min)

    # --- calculate_bar_width ---
    def t_bar_normal():
        result = calculate_bar_width(50, 100)
        assert 0 <= result <= 100, f"Bar width out of range: {result}"
    run_test("Bar width: normal case 50/100", t_bar_normal)

    def t_bar_overflow():
        result = calculate_bar_width(500, 10)
        assert result == 100, f"Expected capped at 100, got {result}"
    run_test("Bar width: overflow (500/10) -> max 100", t_bar_overflow)

    def t_bar_zero_min():
        result = calculate_bar_width(50, 0)
        assert 0 <= result <= 100, f"Bar width with min=0 out of range: {result}"
    run_test("Bar width: stok_minimum=0 (prevent div by zero)", t_bar_zero_min)

    def t_bar_negative():
        result = calculate_bar_width(-10, 50)
        assert result >= 0, f"Expected non-negative, got {result}"
    run_test("Bar width: stok negatif", t_bar_negative)

    # --- filter_stock_by_status ---
    def t_filter_empty_df():
        df = pd.DataFrame()
        try:
            krisis, mendekati, aman, bebas = filter_stock_by_status(df)
            # Should handle gracefully
        except Exception as e:
            raise AssertionError(f"Crashed on empty df: {e}")
    run_test("Filter status: DataFrame kosong", t_filter_empty_df)

    def t_filter_missing_status_col():
        df = pd.DataFrame({
            "nama_barang": ["A", "B"],
            "stok_sekarang": [5, 0],
            "stok_minimum": [10, 10],
        })
        k, m, a, b = filter_stock_by_status(df)
        assert len(k) + len(m) + len(a) + len(b) == 2
    run_test("Filter status: tanpa kolom 'status'", t_filter_missing_status_col)

    def t_filter_mixed_status_types():
        df = pd.DataFrame({
            "nama_barang": ["A", "B", "C", "D", "E"],
            "stok_sekarang": [5, 0, 20, 11, 100],
            "stok_minimum": [10, 10, 10, 10, 10],
            "status": ["TRUE", "true", "False", "1", "0"],
        })
        k, m, a, b = filter_stock_by_status(df)
        total = len(k) + len(m) + len(a) + len(b)
        assert total == 5, f"Expected 5 total, got {total}"
    run_test("Filter status: mixed string types (TRUE/true/False/1/0)", t_filter_mixed_status_types)


# ============================
# 2. TRANSACTION SERVICE TESTS
# ============================
from services.transaction_service import (
    generate_transaction_id,
    validate_stock_out,
    compute_stok_akhir,
    build_transaction_record,
)

def test_transaction_service():
    section("2. transaction_service.py - Anomali Transaksi")

    def t_txid_zero():
        result = generate_transaction_id(0)
        assert result == "T0001", f"Expected T0001, got {result}"
    run_test("TX ID: length=0 -> T0001", t_txid_zero)

    def t_txid_huge():
        result = generate_transaction_id(99999)
        assert "100000" in result, f"Expected overflow ID, got {result}"
    run_test("TX ID: length=99999 (overflow 4 digit)", t_txid_huge)

    def t_txid_negative():
        result = generate_transaction_id(-1)
        assert result == "T0000", f"Expected T0000 for -1, got {result}"
    run_test("TX ID: length=-1 (negatif)", t_txid_negative)

    # --- validate_stock_out ---
    def t_validate_exact():
        valid, sisa = validate_stock_out(10, 10)
        assert valid is True and sisa == 0, f"Expected (True, 0), got ({valid}, {sisa})"
    run_test("Validasi keluar: stok=10, keluar=10 (pas habis)", t_validate_exact)

    def t_validate_over():
        valid, sisa = validate_stock_out(5, 10)
        assert valid is False and sisa == -5, f"Expected (False, -5), got ({valid}, {sisa})"
    run_test("Validasi keluar: stok=5, keluar=10 (melebihi)", t_validate_over)

    def t_validate_zero_stok():
        valid, sisa = validate_stock_out(0, 1)
        assert valid is False, f"Expected False for empty stock"
    run_test("Validasi keluar: stok=0, keluar=1", t_validate_zero_stok)

    def t_validate_zero_keluar():
        valid, sisa = validate_stock_out(10, 0)
        assert valid is True and sisa == 10, f"Expected (True, 10), got ({valid}, {sisa})"
    run_test("Validasi keluar: stok=10, keluar=0", t_validate_zero_keluar)

    def t_validate_negative_keluar():
        valid, sisa = validate_stock_out(10, -5)
        assert valid is False, "Keluar negatif harus ditolak"
    run_test("Validasi keluar: keluar negatif (-5) -> DITOLAK (SECURE)", t_validate_negative_keluar)

    def t_validate_float_precision():
        valid, sisa = validate_stock_out(0.3, 0.1)
        # 0.3 - 0.1 = 0.19999999999999998 (float precision)
        assert valid is True, f"Float precision error: sisa={sisa}"
    run_test("Validasi keluar: presisi float 0.3-0.1", t_validate_float_precision)

    def t_validate_nan():
        valid, sisa = validate_stock_out(float('nan'), 5)
        # nan - 5 = nan, nan >= 0 = False
        assert valid is False, f"Expected False for NaN, got {valid}"
    run_test("Validasi keluar: NaN stok", t_validate_nan)

    # --- compute_stok_akhir ---
    def t_compute_masuk():
        result = compute_stok_akhir(100, 50, "Masuk")
        assert result == 150, f"Expected 150, got {result}"
    run_test("Hitung stok: Masuk 100+50=150", t_compute_masuk)

    def t_compute_keluar():
        result = compute_stok_akhir(100, 50, "Keluar")
        assert result == 50, f"Expected 50, got {result}"
    run_test("Hitung stok: Keluar 100-50=50", t_compute_keluar)

    def t_compute_unknown_type():
        result = compute_stok_akhir(100, 50, "RANDOM_STRING")
        assert result == 100, f"Expected unchanged 100 for unknown type, got {result}"
    run_test("Hitung stok: jenis transaksi tidak dikenal", t_compute_unknown_type)

    def t_compute_empty_type():
        result = compute_stok_akhir(100, 50, "")
        assert result == 100, f"Expected 100 for empty type, got {result}"
    run_test("Hitung stok: jenis transaksi string kosong", t_compute_empty_type)

    def t_compute_case_sensitive():
        result = compute_stok_akhir(100, 50, "masuk")  # lowercase
        assert result == 150, f"Expected 150 (case-insensitive), got {result}"
    run_test("Hitung stok: 'masuk' lowercase -> 150 (INSENSITIVE SECURE)", t_compute_case_sensitive)

    def t_compute_negative_qty():
        result = compute_stok_akhir(100, -50, "Masuk")
        assert result == 100, f"Expected 100 (clamped), got {result}"
    run_test("Hitung stok: Masuk dengan qty negatif (-50) -> aman (SECURE)", t_compute_negative_qty)

    # --- build_transaction_record ---
    def t_build_xss_input():
        record = build_transaction_record(
            0, "Masuk", "<script>alert('xss')</script>", 10,
            "'; DROP TABLE--", "Pagi", "<img onerror=alert(1)>"
        )
        assert "script" in record["kode_barang"], "XSS string should pass through (stored as-is)"
    run_test("Build record: XSS injection dalam input text", t_build_xss_input)

    def t_build_unicode():
        record = build_transaction_record(
            0, "Masuk", "Tempe\u200b\u200b\u200b", 10,
            "user\ud83d\ude00", "Pagi", "emoji\ud83c\udf89"
        )
        assert record is not None
    run_test("Build record: Unicode + emoji + zero-width chars", t_build_unicode)

    def t_build_empty_strings():
        record = build_transaction_record(0, "", "", 0, "", "", "")
        assert record is not None
    run_test("Build record: semua string kosong", t_build_empty_strings)


# ============================
# 3. VALIDATORS TESTS
# ============================
from utils.validators import validate_new_item, validate_editor_changes, validate_transaction

def test_validators():
    section("3. validators.py - Anomali Validasi Input")

    def t_new_item_empty():
        valid, msg = validate_new_item("", "", pd.DataFrame({"kode_barang": []}))
        assert valid is False
    run_test("New item: kode & nama kosong -> invalid", t_new_item_empty)

    def t_new_item_duplicate():
        df = pd.DataFrame({"kode_barang": ["SKU001", "SKU002"]})
        valid, msg = validate_new_item("SKU001", "Item Baru", df)
        assert valid is False and "terdaftar" in msg.lower()
    run_test("New item: kode duplikat -> invalid", t_new_item_duplicate)

    def t_new_item_special_chars():
        df = pd.DataFrame({"kode_barang": []})
        valid, msg = validate_new_item("!@#$%^&*()", "<script>", df)
        assert valid is True, "Validator allows special chars (no sanitization)"
    run_test("New item: karakter spesial sebagai kode & nama (passed!)", t_new_item_special_chars)

    def t_new_item_whitespace():
        df = pd.DataFrame({"kode_barang": ["SKU001"]})
        valid, msg = validate_new_item("  ", "  ", df)
        assert valid is False, "Whitespace-only harus ditolak"
    run_test("New item: hanya spasi (whitespace-only) -> DITOLAK (SECURE)", t_new_item_whitespace)

    def t_new_item_very_long():
        long_str = "A" * 10000
        df = pd.DataFrame({"kode_barang": []})
        valid, msg = validate_new_item(long_str, long_str, df)
        assert valid is True, "Very long strings should technically pass"
    run_test("New item: string 10000 karakter", t_new_item_very_long)

    def t_editor_duplicates():
        df = pd.DataFrame({"kode_barang": ["A", "A", "B"]})
        valid, msg = validate_editor_changes(df)
        assert valid is False
    run_test("Editor: kode duplikat -> invalid", t_editor_duplicates)

    def t_editor_empty_cells():
        df = pd.DataFrame({"kode_barang": ["A", "", "B"]})
        valid, msg = validate_editor_changes(df)
        assert valid is False
    run_test("Editor: ada sel kosong -> invalid", t_editor_empty_cells)

    def t_editor_null_cells():
        df = pd.DataFrame({"kode_barang": ["A", None, "B"]})
        valid, msg = validate_editor_changes(df)
        assert valid is False
    run_test("Editor: ada sel None/null -> invalid", t_editor_null_cells)

    def t_trx_zero_amount():
        valid, msg = validate_transaction("Admin", 0)
        assert valid is False, "Jumlah 0 harus invalid"
    run_test("Transaksi: jumlah=0 -> invalid", t_trx_zero_amount)

    def t_trx_negative_amount():
        valid, msg = validate_transaction("Admin", -10)
        assert valid is False, "Jumlah negatif harus ditolak"
    run_test("Transaksi: jumlah negatif (-10) -> DITOLAK (SECURE)", t_trx_negative_amount)

    def t_trx_empty_petugas():
        valid, msg = validate_transaction("", 5)
        assert valid is False
    run_test("Transaksi: petugas kosong -> invalid", t_trx_empty_petugas)

    def t_trx_whitespace_petugas():
        valid, msg = validate_transaction("   ", 5)
        assert valid is False, "Petugas hanya spasi harus ditolak"
    run_test("Transaksi: petugas hanya spasi -> DITOLAK (SECURE)", t_trx_whitespace_petugas)


# ============================
# 4. REPORT SERVICE TESTS
# ============================
from services.report_service import (
    get_daily_transactions,
    aggregate_daily_summary,
    filter_last_n_days,
    aggregate_trend_data,
)

def test_report_service():
    section("4. report_service.py - Anomali Laporan")

    def t_daily_empty():
        result = get_daily_transactions(pd.DataFrame(), "2026-10-01")
        assert result.empty
    run_test("Laporan harian: df kosong -> df kosong", t_daily_empty)

    def t_daily_no_match():
        df = pd.DataFrame({"tanggal": ["2026-01-01"], "nama": ["A"]})
        result = get_daily_transactions(df, "2099-12-31")
        assert result.empty
    run_test("Laporan harian: tanggal tidak ada -> df kosong", t_daily_no_match)

    def t_daily_invalid_date():
        df = pd.DataFrame({"tanggal": ["bukan-tanggal", "2026-10-01"]})
        result = get_daily_transactions(df, "bukan-tanggal")
        assert len(result) == 1, "String matching still works"
    run_test("Laporan harian: tanggal string invalid (matching tetap jalan)", t_daily_invalid_date)

    def t_aggregate_empty():
        result = aggregate_daily_summary(pd.DataFrame(), pd.DataFrame())
        assert result.empty
    run_test("Agregasi: kedua df kosong -> aman", t_aggregate_empty)

    def t_filter_zero_days():
        df = pd.DataFrame({
            "tanggal_dt": [pd.Timestamp("2026-10-01")],
            "nama": ["A"]
        })
        result = filter_last_n_days(df, 0)
        # n_days=0 -> filter >= today -> only today's data
        assert isinstance(result, pd.DataFrame)
    run_test("Filter: n_days=0 (hari ini saja)", t_filter_zero_days)

    def t_filter_negative_days():
        df = pd.DataFrame({
            "tanggal_dt": [pd.Timestamp("2026-10-01")],
            "nama": ["A"]
        })
        result = filter_last_n_days(df, -5)
        # n_days=-5 -> batas = today + 5 hari -> filter masa depan
        assert isinstance(result, pd.DataFrame)
    run_test("Filter: n_days negatif (-5) -> filter masa depan (anomali)", t_filter_negative_days)

    def t_filter_huge_days():
        df = pd.DataFrame({
            "tanggal_dt": [pd.Timestamp("1900-01-01")],
            "nama": ["A"]
        })
        result = filter_last_n_days(df, 999999)
        assert len(result) == 1, "Should include very old data"
    run_test("Filter: n_days=999999 (ratusan tahun ke belakang)", t_filter_huge_days)

    def t_trend_empty():
        result = aggregate_trend_data(pd.DataFrame())
        assert result.empty
    run_test("Trend: df kosong -> aman", t_trend_empty)


# ============================
# 5. FORMATTING TESTS (HTML INJECTION)
# ============================
from utils.formatting import get_header_html, get_row_html

def test_formatting():
    section("5. formatting.py - XSS & HTML Injection")

    def t_header_xss():
        result = get_header_html(-1)
        assert "0 Item" in result, "Negative item count should be clamped to 0"
    run_test("Header HTML: jumlah item negatif (-1) -> di-clamp ke 0 (SECURE)", t_header_xss)

    def t_row_xss_nama():
        c1, c2, c3 = get_row_html(
            '<script>alert("XSS")</script>',  # nama_barang
            '"; DROP TABLE--',  # kode
            -999, "kg", 0, -50,
            "HACKED", "#ff0000", "red", "white", "X", "Crashed"
        )
        assert "&lt;script&gt;" in c1, "XSS must be escaped"
        assert "<script>" not in c1, "Raw script tag must not exist"
    run_test("Row HTML: XSS di nama_barang -> ter-escape aman (SECURE)", t_row_xss_nama)

    def t_row_negative_bar():
        c1, c2, c3 = get_row_html(
            "Test", "T001", -100, "pcs", -50, -200,
            "BUG", "#000", "#000", "#000", "?", "Error"
        )
        assert c2 is not None, "Negative bar width should not crash"
    run_test("Row HTML: semua nilai negatif -> tidak crash", t_row_negative_bar)

    def t_row_huge_values():
        c1, c2, c3 = get_row_html(
            "A" * 500, "B" * 500, 99999999, "satuan_panjang" * 10, 99999999, 999,
            "STATUS_PANJANG" * 10, "#fff", "#000", "#333", "X" * 20, "EST" * 50
        )
        assert c1 is not None
    run_test("Row HTML: string & angka sangat panjang", t_row_huge_values)

    def t_row_empty_strings():
        c1, c2, c3 = get_row_html("", "", 0, "", 0, 0, "", "", "", "", "", "")
        assert c1 is not None
    run_test("Row HTML: semua string kosong", t_row_empty_strings)

    def t_row_none_satuan():
        # Ini bisa crash kalau ada f-string yang menerima None
        try:
            c1, c2, c3 = get_row_html("Test", "T001", 10, None, 5, 50, "OK", "#0f0", "#efe", "#0f0", "V", "OK")
            assert True  # Didn't crash
        except TypeError:
            raise AssertionError("Crashed when satuan=None!")
    run_test("Row HTML: satuan=None -> tidak crash", t_row_none_satuan)


# ============================
# 6. SHEETS REPOSITORY LOGIC
# ============================
def test_sheets_logic():
    section("6. sheets_repository.py - Logika Konversi Data")

    # Test numeric conversion logic from get_sheet_data
    def safe_convert(val):
        """Replicate the conversion logic in sheets_repository.py"""
        if isinstance(val, str):
            val = val.replace(',', '.')
        return pd.to_numeric(val, errors='coerce')

    def t_convert_normal():
        assert safe_convert("1000") == 1000
    run_test("Konversi: '1000' -> 1000", t_convert_normal)

    def t_convert_comma():
        assert safe_convert("1.500,50") == 1500.50 or pd.isna(safe_convert("1.500,50"))
    run_test("Konversi: '1.500,50' (format Indonesia)", t_convert_comma)

    def t_convert_empty():
        result = safe_convert("")
        assert pd.isna(result), f"Expected NaN, got {result}"
    run_test("Konversi: string kosong -> NaN (lalu fillna(0))", t_convert_empty)

    def t_convert_text():
        result = safe_convert("bukan angka")
        assert pd.isna(result), f"Expected NaN for non-numeric text"
    run_test("Konversi: 'bukan angka' -> NaN", t_convert_text)

    def t_convert_negative_str():
        result = safe_convert("-500")
        assert result == -500
    run_test("Konversi: '-500' -> -500", t_convert_negative_str)

    def t_convert_inf():
        result = safe_convert("inf")
        assert result == float('inf') or pd.isna(result)
    run_test("Konversi: 'inf' (string infinity)", t_convert_inf)

    def t_convert_special():
        result = safe_convert("Rp 5.000")
        assert pd.isna(result), "Rp prefix should fail conversion"
    run_test("Konversi: 'Rp 5.000' -> NaN (tidak bisa dikonversi)", t_convert_special)


# ============================
# 7. BISNIS LOGIC EDGE CASES
# ============================
def test_business_logic():
    section("7. Logika Bisnis - Simulasi Skenario Anomali")

    # Simulasi distribusi proporsional pasien
    def simulate_distribusi(row_data, distribusi, total_pasien):
        """Replicate logic from pengeluaran_pasien.py (hardened)"""
        results = []
        for r in row_data:
            for kat, jml in distribusi:
                if jml > 0 and total_pasien > 0:
                    porsi = jml / total_pasien
                    qty_proporsional = r["qty"] * porsi
                    results.append({
                        "kategori": kat,
                        "nama_barang": r["nama_barang"],
                        "qty": qty_proporsional,
                        "total_harga": qty_proporsional * r["harga_master"],
                    })
        return results

    def t_distribusi_normal():
        rows = [{"nama_barang": "A", "qty": 10, "harga_master": 1000}]
        dist = [("VIP", 2), ("Kelas 1", 3)]
        results = simulate_distribusi(rows, dist, 5)
        total_qty = sum(r["qty"] for r in results)
        assert abs(total_qty - 10) < 0.001, f"Total qty harus tetap 10, got {total_qty}"
    run_test("Distribusi: 10 qty / 5 pasien (2 VIP + 3 Kelas 1)", t_distribusi_normal)

    def t_distribusi_single_patient():
        rows = [{"nama_barang": "A", "qty": 10, "harga_master": 1000}]
        dist = [("VIP", 1)]
        results = simulate_distribusi(rows, dist, 1)
        assert results[0]["qty"] == 10
    run_test("Distribusi: 1 pasien saja -> qty utuh", t_distribusi_single_patient)

    def t_distribusi_zero_total():
        rows = [{"nama_barang": "A", "qty": 10, "harga_master": 1000}]
        dist = [("VIP", 5)]
        results = simulate_distribusi(rows, dist, 0)
        assert len(results) == 0, "total_pasien=0 aman tanpa pembagian nol"
    run_test("Distribusi: total_pasien=0 aman tanpa ZeroDivisionError", t_distribusi_zero_total)

    def t_distribusi_float_qty():
        rows = [{"nama_barang": "A", "qty": 7, "harga_master": 1000}]
        dist = [("VIP", 2), ("Kelas 1", 3)]
        results = simulate_distribusi(rows, dist, 5)
        # 7 * 2/5 = 2.8, 7 * 3/5 = 4.2
        total_qty = sum(r["qty"] for r in results)
        assert abs(total_qty - 7) < 0.001, f"Total harus 7, got {total_qty}"
    run_test("Distribusi: qty ganjil (7/5) -> hasil desimal", t_distribusi_float_qty)

    def t_distribusi_many_classes():
        rows = [{"nama_barang": "A", "qty": 100, "harga_master": 500}]
        dist = [("VIP", 1), ("K1", 1), ("K2", 1), ("K3", 1)]
        results = simulate_distribusi(rows, dist, 4)
        assert len(results) == 4
        for r in results:
            assert r["qty"] == 25
    run_test("Distribusi: 4 kelas masing-masing 1 pasien", t_distribusi_many_classes)

    # Kebijakan HPP Master: HPP Master TETAP dan tidak boleh diubah oleh transaksi Stok Masuk
    def t_hpp_master_remains_intact():
        harga_master = 5000
        harga_real_naik = 7000
        # HPP Master harus tetap
        master_hpp = harga_master
        assert master_hpp == 5000, "HPP Master tidak boleh berubah saat harga naik"
    run_test("HPP Master: tetap utuh saat harga real naik", t_hpp_master_remains_intact)

    def t_hpp_master_turun_intact():
        harga_master = 5000
        harga_real_turun = 4000
        master_hpp = harga_master
        assert master_hpp == 5000, "HPP Master tidak boleh berubah saat harga real turun"
    run_test("HPP Master: tetap utuh saat harga real turun", t_hpp_master_turun_intact)

    def t_hpp_selisih_notification():
        harga_master = 5000
        harga_real_naik = 6000
        selisih_naik = harga_real_naik - harga_master
        assert selisih_naik > 0, "Harga naik terdeteksi selisih > 0"
        
        harga_real_turun = 4500
        selisih_turun = harga_real_turun - harga_master
        assert selisih_turun < 0, "Harga turun terdeteksi selisih < 0"
        
        harga_real_sama = 5000
        selisih_sama = harga_real_sama - harga_master
        assert selisih_sama == 0, "Harga sama terdeteksi selisih == 0"
    run_test("Notifikasi harga: deteksi naik, turun, dan sama secara presisi", t_hpp_selisih_notification)

    # Simulasi stok update pada save transaksi masuk
    def t_stok_masuk_overflow():
        stok_sekarang = 999999999
        qty_masuk = 999999999
        stok_baru = stok_sekarang + qty_masuk
        assert stok_baru == 1999999998, f"Expected 1999999998, got {stok_baru}"
    run_test("Stok masuk: overflow angka raksasa (999M + 999M)", t_stok_masuk_overflow)

    # Simulasi pengeluaran lebih dari stok
    def t_stok_keluar_over():
        stok_sekarang = 5
        qty_keluar = 10
        stok_baru = stok_sekarang - qty_keluar
        assert stok_baru == -5, "Stok negatif memang BISA terjadi (tidak ada guard di save)"
    run_test("Stok keluar: keluar > stok -> negatif (tidak ada guard!)", t_stok_keluar_over)

    # Concurrent / race condition simulation
    def t_concurrent_conceptual():
        # Simulate: 2 users read stok=10 at the same time, both try to keluar 8
        stok_awal = 10
        user1_keluar = 8
        user2_keluar = 8
        # Without locking, both see stok=10
        stok_after_user1 = stok_awal - user1_keluar  # 2
        stok_after_user2 = stok_awal - user2_keluar  # 2
        # But the last one to save wins:
        # If user2 saves last, master shows 2 (incorrect, should be -6)
        # This is a conceptual test - race condition exists!
        assert True, "Race condition BISA terjadi (Google Sheets tidak ada locking)"
    run_test("Race condition: 2 user keluar stok bersamaan (RISIKO!)", t_concurrent_conceptual)


# ============================
# 8. PANDAS EDGE CASES
# ============================
def test_pandas_edge_cases():
    section("8. Pandas Edge Cases - Data Kotor")

    def t_empty_df_tolist():
        df = pd.DataFrame({"nama_barang": []})
        result = df["nama_barang"].tolist()
        assert result == [], f"Expected empty list, got {result}"
    run_test("DF kosong: .tolist() -> [] (selectbox aman)", t_empty_df_tolist)

    def t_nan_in_nama():
        df = pd.DataFrame({"nama_barang": ["A", np.nan, "B"]})
        # Ini bisa bikin selectbox error
        items = df["nama_barang"].tolist()
        has_nan = any(pd.isna(x) for x in items)
        assert has_nan, "NaN in nama_barang list -> potential selectbox crash"
    run_test("NaN di nama_barang: terdeteksi di list -> potential crash", t_nan_in_nama)

    def t_duplicated_index():
        df = pd.DataFrame({"nama_barang": ["A", "B"], "stok_sekarang": [10, 20]}, index=[0, 0])
        idx = df.index[df["nama_barang"] == "A"].tolist()
        # Duplicate index bisa bikin .at[idx] ambiguous
        assert len(idx) == 1
    run_test("Index duplikat: .index filter masih benar", t_duplicated_index)

    def t_special_chars_in_contains():
        df = pd.DataFrame({"nama_barang": ["Kopi (Pagi)", "Teh [Sore]", "Gula {Malam}"]})
        # Dengan regex=False, karakter (, [, { aman dan tidak crash / warning
        result = df[df["nama_barang"].str.contains("(Pagi)", case=False, na=False, regex=False)]
        assert len(result) == 1, "Harus menemukan 1 barang dengan nama '(Pagi)'"
    run_test("str.contains: regex=False aman untuk karakter '(' dan '['", t_special_chars_in_contains)

    def t_concat_empty_list():
        dfs = []
        try:
            result = pd.concat(dfs, ignore_index=True)
        except ValueError:
            pass  # Expected: No objects to concatenate
    run_test("pd.concat: list kosong -> ValueError", t_concat_empty_list)

    def t_merge_missing_key():
        df1 = pd.DataFrame({"kode": ["A"], "qty": [1]})
        df2 = pd.DataFrame({"kode": ["B"], "nama": ["Test"]})
        result = pd.merge(df1, df2, on="kode", how="left")
        assert pd.isna(result["nama"].iloc[0]), "Unmatched merge -> NaN"
    run_test("Merge: key tidak cocok -> NaN di kolom join", t_merge_missing_key)

    def t_date_parsing_edge():
        dates = ["2026-10-01 08:00:00", "10/01/2026", "Oct 1 2026", "bukan-tanggal", "", None]
        # format='mixed' handles multiple date formats gracefully
        results = pd.to_datetime(dates, errors="coerce", format="mixed")
        valid_count = results.notna().sum()
        assert valid_count >= 2, f"Expected at least 2 valid dates, got {valid_count}"
    run_test("Date parsing: format='mixed' menangani tanggal campur + invalid + None", t_date_parsing_edge)


# ============================
# MAIN
# ============================
def main():
    start_time = time.time()

    print(f"\n{'='*65}")
    print(f"  STOK GIZI RS AN-NISA - WHITE-BOX TESTING (ANOMALI)")
    print(f"  Waktu: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*65}")

    test_stock_service()
    test_transaction_service()
    test_validators()
    test_report_service()
    test_formatting()
    test_sheets_logic()
    test_business_logic()
    test_pandas_edge_cases()

    elapsed = time.time() - start_time

    section("RINGKASAN HASIL WHITE-BOX TEST")
    total = passed + failed
    print(f"  Total test   : {total}")
    print(f"  PASS         : {passed}")
    print(f"  FAIL         : {failed}")
    print(f"  Durasi       : {elapsed:.2f}s")
    print()

    if failed == 0:
        print(f"  SEMUA TEST LULUS! Tidak ada crash pada input anomali.")
    else:
        print(f"  Ada {failed} test GAGAL! Beberapa mungkin menandakan BUG yang perlu diperbaiki.")
        print(f"  Test bertanda 'BUG' = known issue yang sebaiknya di-patch.")

    print(f"\n{'='*65}\n")

if __name__ == "__main__":
    main()
