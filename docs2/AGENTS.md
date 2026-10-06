# AGENTS.md — Panduan Pekerjaan Migrasi CGIZI

## 1. Tujuan dan Status

Panduan ini berlaku untuk pekerjaan yang terkait migrasi CGIZI menuju React frontend dengan backend API Python dan Google Sheets sebagai penyimpanan sementara. Ini adalah rancangan; aplikasi yang ada masih Streamlit. Jangan menganggap fitur/arsitektur target telah diimplementasikan.

## 2. Sumber Kebenaran

- Kode sumber dan workbook yang dikonfirmasi pemilik data lebih kuat daripada dokumen lama.
- Sebelum mengubah perilaku, baca implementasi dekat, tes terkait, dan schema/header workbook bila tersedia.
- Tandai fakta hasil pengamatan berbeda dari asumsi/keputusan desain; jangan mengarang kepastian dari nama fungsi atau dokumentasi.
- Nama kolom terlihat tidak konsisten: `kode_barang`/`id_barang`, `stok_minimum`/`stok_minimal`, `qty`/`jumlah`. Jangan rename header atau melakukan migrasi data destruktif tanpa mapping, backup, persetujuan, dan uji dry-run.

## 3. Batas Arsitektur

- Frontend React hanya berkomunikasi ke backend melalui API JSON HTTPS.
- Jangan pernah mengakses Google Sheets langsung dari browser.
- Service account, private key, token Google, kredensial dan URL konfigurasi privat hanya berada di runtime backend/secret manager; jangan commit, print, masukkan fixture, screenshot, atau dokumentasi.
- Domain services tidak mengimpor React, FastAPI, Streamlit, `gspread`, atau Google SDK; repository adapter mengisolasi akses persistence.
- Jangan memindahkan seluruh kode legacy sekaligus. Perubahan bertahap, mempertahankan aplikasi lama sampai cutover disetujui.

## 4. Aturan Integritas Transaksi

- Semua validasi final dilakukan di server, termasuk permission, actor, harga, jumlah gabungan per item, saldo terkini, paket, dan FIFO.
- Mutasi harus memiliki ID transaksi/operasi stabil, idempotency key, actor terautentikasi, timestamp server, correlation ID, dan audit.
- Jangan gunakan cache sebagai basis saldo final. Baca data terkini sebelum mutasi dan invalidasi cache setelah commit.
- Google Sheets bukan database transaksional. Jangan mengklaim atomicity/locking yang tidak dibuktikan. Hindari `clear()`/tulis ulang tab penuh untuk transaksi rutin.
- Gunakan batch API Sheets yang sesuai dan diuji. Tangani timeout ambigu, sebagian gagal, retry, konflik, serta rekonsiliasi tanpa membuat transaksi duplikat.
- Jika memakai lock in-process, dokumentasikan bahwa hanya aman dengan satu instance penulis dan semua writer lain dihentikan. Jangan menambah replica penulis tanpa koordinasi terdistribusi.
- Jangan menghapus transaksi tanpa jejak. Utamakan adjustment/reversal dengan alasan dan hak akses.
- Identitas barang harus menggunakan ID stabil; jangan menjadikan nama/supplier atau indeks baris sebagai kunci permanen.

## 5. Aturan Domain yang Harus Dipertahankan/Diverifikasi

- Pertahankan workflow Master Barang, Master Dokter, penerimaan, pengeluaran pasien/dokter/manajemen, riwayat, laporan, dan dashboard.
- Paket Snack/Buah/Roti diurai menjadi baris bahan fisik sebelum disimpan.
- Validasi seluruh kebutuhan paket dan baris bersama sebelum menulis apa pun.
- Perubahan pengeluaran pasien/koreksi dapat memengaruhi `sisa_qty` FIFO; verifikasi kode dan workbook.
- Pertahankan input fraksional dan presisi yang disepakati (baseline form memakai step 0,05/format dua desimal di beberapa tempat).
- Jangan ubah ambang stok, aturan Bahan Bebas, alokasi pasien, rounding, atau harga tanpa tes dan persetujuan domain owner.
- Sanitasi normalisasi angka dengan locale Indonesia; uang sebaiknya dihitung sebagai Decimal/integer rupiah pada API.

## 6. Keamanan dan Privasi

- Jangan percaya pada route guard/UI; server selalu menegakkan autentikasi dan otorisasi.
- Nama petugas harus berasal dari identity claim server, bukan teks bebas pada payload mutasi.
- Terapkan validasi tipe/ukuran input, output encoding, rate limits, CORS allowlist, TLS, proteksi CSRF sesuai mekanisme sesi, dan error yang tidak mengekspos detail internal.
- Ekspor CSV harus melindungi formula injection. Jangan log data pasien/secret yang tidak diperlukan.
- Jangan membuat test yang mengubah spreadsheet produksi. Gunakan mock atau workbook staging yang secara eksplisit disetujui.

## 7. Pengujian dan Verifikasi

### Legacy yang tetap menjadi baseline

Sesuai keadaan proyek saat ini, jalankan jika mengubah behavior legacy:

```powershell
python tests/whitebox_test.py
python tests/health_check.py
```

`health_check.py` dapat membaca konfigurasi/koneksi Sheets; jangan menjalankannya bila credential atau akses ke workbook tidak tersedia/diizinkan. Untuk compile Python legacy yang diubah:

```powershell
python -m py_compile app.py
python -m py_compile views/*.py
python -m py_compile services/*.py
python -m py_compile data/*.py
```

### Target migrasi (setelah toolchain dibuat)

- Backend: unit tests domain; API tests untuk auth, permission, validation, idempotency, dan response; repository tests dengan mock; integration tests memakai workbook staging.
- Frontend: lint, test fitur, production build, dan tes alur form/loading/error.
- Mutasi Sheets diuji dengan fixture/salinan, termasuk timeout ambigu, request bersamaan, kegagalan antar-tab, duplikasi dan konflik stok.
- UAT mencakup rekonsiliasi saldo dan ledger dengan pengguna Instalasi Gizi.
- Bila command/tool belum ada, laporkan sebagai belum tersedia; jangan mengarang hasil PASS.

## 8. Alur Perubahan

1. Identifikasi file/fitur dan formulasi hipotesis lokal sebelum edit.
2. Periksa aturan repo dan tes terdekat; jaga perubahan tetap sempit.
3. Untuk fitur API, tulis/ubah kontrak dan tes yang menguji perilaku sebelum menghubungkan Sheets produksi.
4. Untuk schema, buat mapping/validator read-only terlebih dahulu; jangan langsung rewrite workbook.
5. Setelah edit, jalankan satu validasi fokus segera, lalu tes terkait dan gate yang diwajibkan.
6. Periksa perubahan yang dibuat tanpa membuang perubahan lokal pengguna.
7. Jangan commit, mengganti branch, atau melakukan deploy/cutover tanpa permintaan eksplisit.

## 9. Dokumentasi

- Perubahan kebutuhan produk masuk ke `docs2/PRD.md`.
- Perubahan tujuan/proses bisnis masuk ke `docs2/BRD.md`.
- Keputusan batas komponen, API, storage, deployment atau migrasi masuk ke `docs2/ARCHITECTURE.md`.
- Perbarui tanggal/status/keputusan terbuka bila isi dokumen berubah.
- Jangan menyebut target sebagai kondisi implementasi aktual.
