# Dokumen Migrasi CGIZI

Dokumen ini menjadi baseline perencanaan migrasi CGIZI dari Streamlit ke React dengan Google Sheets tetap sebagai penyimpanan untuk tahap awal.

## Dokumen

- [BRD](BRD.md): kebutuhan dan proses bisnis, pemangku kepentingan, ruang lingkup, manfaat, risiko, dan ukuran keberhasilan.
- [PRD](PRD.md): kebutuhan produk, fitur, aturan bisnis, alur, kriteria penerimaan, dan prioritas.
- [Arsitektur](ARCHITECTURE.md): rancangan target React, API Python, integrasi Google Sheets, keamanan, deployment, dan migrasi.
- [Instruksi Agen](AGENTS.md): aturan kerja bagi agen AI/developer pada pekerjaan migrasi.

## Status dan sumber

Dokumen berstatus **draft untuk validasi pemilik proses**. Baseline legacy ditelusuri dari `app.py`, `views/`, `services/`, `data/sheets_repository.py`, `tests/health_check.py`, `requirements.txt`, `README.md`, dan dokumentasi yang ada. Kode yang ada masih merupakan aplikasi Streamlit; dokumen ini tidak mengklaim bahwa React/API sudah diimplementasikan.

Beberapa nama kolom/identitas pada dokumentasi lama tidak konsisten dengan kode. Skema Google Sheets aktual harus dikonfirmasi dengan pemilik spreadsheet dan health check sebelum kontrak API dibekukan. Lihat bagian asumsi dan keputusan terbuka di setiap dokumen.
