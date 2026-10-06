# Dokumen Kebutuhan Produk (PRD)
## CGIZI React — Pengelolaan Stok Instalasi Gizi

| Atribut | Nilai |
|---|---|
| Versi | 1.0 Draft |
| Tanggal | 5 Oktober 2026 |
| Status | Usulan produk, belum diimplementasikan |
| Platform target | Web: React frontend + Python API + Google Sheets |
| Dokumen terkait | [BRD](BRD.md), [Arsitektur](ARCHITECTURE.md) |

## 1. Visi Produk

Menyediakan aplikasi web operasional yang membantu petugas Instalasi Gizi mencatat dan mengawasi pergerakan bahan secara akurat, mudah diaudit, dan cepat digunakan, dengan Google Sheets tetap menjadi sumber penyimpanan pada tahap migrasi awal.

## 2. Persona dan Hak Akses Sasaran

| Persona | Hak yang diusulkan |
|---|---|
| Petugas Logistik | Lihat stok; kelola barang sesuai kewenangan; buat penerimaan; lihat riwayat penerimaan |
| Petugas Distribusi | Lihat stok; buat pengeluaran pasien/dokter/manajemen; lihat riwayat operasional |
| Kepala Instalasi | Lihat seluruh dashboard/laporan/ekspor; persetujuan koreksi bila kebijakan mengharuskan |
| Admin DTO | Kelola pengguna/konfigurasi, cek kesehatan koneksi, refresh/reconcile, tanpa menggunakan akun petugas operasional |

Autentikasi dan hak akses adalah kebutuhan target. Baseline tidak menunjukkan login formal; metode SSO RS vs akun aplikasi harus dipilih sebelum implementasi. Nama petugas tidak boleh menjadi teks bebas yang dianggap identitas terverifikasi.

## 3. Tujuan, Non-Tujuan, dan Prinsip

### Tujuan

- Memindahkan semua layar operasional yang relevan ke React.
- Menjadikan API Python pemilik validasi, aturan stok, akses data, dan audit.
- Mempertahankan tab Sheets dan format data selama tahap awal, dengan mapping yang tervalidasi.
- Menyediakan perilaku loading, empty, error, konfirmasi, dan hasil simpan yang jelas.
- Menjaga transaksi lama tetap dapat ditelusuri dan diekspor.

### Non-tujuan fase awal

- Mengubah kebijakan stok atau formula pasien tanpa persetujuan.
- Mengganti Sheets dengan PostgreSQL.
- Integrasi HIS, SSO tertentu sebelum mekanisme tersedia, notifikasi eksternal, atau aplikasi native.

### Prinsip produk

- Backend adalah otoritas final untuk validasi, hak akses, harga, dan saldo.
- Tidak ada mutasi sheet langsung dari React.
- Mutasi selalu eksplisit, idempotent, tercatat, dan dapat direkonsiliasi.
- Gunakan ID stabil; nama barang/supplier bukan primary key.
- Satuan, presisi, zona waktu, dan format data kanonik dinormalisasi di API.

## 4. Ruang Fitur dan Prioritas

Prioritas: **P0** wajib untuk operasional awal, **P1** penting setelah alur inti stabil, **P2** peningkatan.

| Modul | Cakupan | Prioritas |
|---|---|---|
| Autentikasi & shell aplikasi | Login, sesi, profil/peran, navigasi, logout | P0 |
| Dashboard | Ringkasan stok, item kritis, aktivitas terbaru, filter tanggal | P1 |
| Master Barang | Daftar, pencarian/filter, tambah, edit, aktif/nonaktif, detail stok | P0 |
| Master Dokter | CRUD roster dokter, poli/ruang, jadwal/status | P1 |
| Penerimaan | Input batch, supplier, qty, harga beli vs HPP, catatan, stok masuk | P0 |
| Pengeluaran pasien | Pasien per kelas/ruangan, item multi-baris, alokasi pratinjau, validasi | P0 |
| Pengeluaran dokter | Daftar dokter/roster, shift, alokasi satu atau banyak dokter | P0 |
| Pengeluaran manajemen | Kategori unit/acara, entri dinamis multi-item | P0 |
| Paket komposit | Definisi/pemilihan bahan Snack, Buah, Roti; uraikan sebelum simpan | P0 |
| Riwayat transaksi | Pencarian, filter, detail, ekspor, koreksi/void berwenang | P0 baca; P1 mutasi |
| Laporan harian | Saldo awal + masuk - keluar = saldo akhir; ekspor | P1 |
| Analisis stok | Status, nilai stok, per kategori, tren | P1 |
| Sinkronisasi/operasional | Health check, refresh, rekonsiliasi, status integrasi | P1 |

## 5. Kebutuhan Fungsional

### 5.1 Autentikasi dan navigasi

- **FR-AUTH-01 (P0):** Pengguna harus masuk sebelum membuka data atau menjalankan mutasi.
- **FR-AUTH-02 (P0):** Backend mengidentifikasi aktor dari sesi/token yang valid; field petugas pada transaksi berasal dari identitas tersebut.
- **FR-AUTH-03 (P0):** API memeriksa izin pada setiap operasi; menyembunyikan tombol di UI bukan pengamanan.
- **FR-NAV-01 (P0):** Aplikasi menyediakan navigasi konsisten ke Dashboard, Master, Transaksi, Riwayat, dan Laporan sesuai izin.
- **FR-NAV-02 (P0):** Refresh halaman tidak boleh menggandakan submit atau menghapus draft input yang belum dikirim tanpa peringatan.

### 5.2 Master Barang

- **FR-ITEM-01 (P0):** Daftar barang mendukung pencarian nama/kode serta filter kategori, supplier, status stok, dan aktif/nonaktif.
- **FR-ITEM-02 (P0):** Form barang menangani kode, nama, kategori, satuan, saldo awal bila diberi izin, stok minimum, HPP, supplier, dan status sesuai skema yang disetujui.
- **FR-ITEM-03 (P0):** API menolak kode duplikat, nama wajib kosong, nilai negatif yang tidak dibenarkan, dan kombinasi field tidak valid.
- **FR-ITEM-04 (P0):** Perubahan master/audit dicatat; koreksi saldo dilakukan lewat adjustment yang teridentifikasi, bukan edit saldo biasa tanpa alasan.
- **FR-ITEM-05 (P1):** Status stok ditampilkan memakai ambang yang dikonfirmasi: Habis, Kritis, Mendekati Min, Aman, Bahan Bebas.

### 5.3 Master Dokter

- **FR-DOC-01 (P1):** Pengguna berwenang dapat mengelola nama dokter, poli/ruangan, jadwal/shift, dan status aktif sesuai kolom workbook yang disepakati.
- **FR-DOC-02 (P1):** Daftar dokter aktif dapat dipakai untuk pengeluaran dokter; data tidak aktif tidak ditawarkan untuk transaksi baru.

### 5.4 Penerimaan Stok

- **FR-IN-01 (P0):** Pengguna dapat menginput satu atau banyak item untuk satu supplier/nota, tanggal, shift, dan keterangan.
- **FR-IN-02 (P0):** Tiap baris menampilkan HPP, harga beli aktual, selisih nilai/persentase, qty, dan subtotal.
- **FR-IN-03 (P0):** Qty harus lebih besar dari nol; harga tidak negatif; item dan supplier harus valid.
- **FR-IN-04 (P0):** Sebelum simpan, server membaca/menjamin keadaan terbaru dan membuat ledger penerimaan serta saldo baru; respons memberikan ID transaksi.
- **FR-IN-05 (P0):** Request memiliki idempotency key sehingga retry jaringan tidak membuat penerimaan ganda.
- **FR-IN-06 (P1):** Pengguna berizin dapat mengoreksi penerimaan dengan alasan; stok dan FIFO yang terdampak dihitung ulang sesuai kebijakan.

### 5.5 Pengeluaran Pasien

- **FR-OUT-PAT-01 (P0):** Form mendukung tanggal, shift, ruangan/tujuan, jumlah pasien menurut kelas yang berlaku, item, qty, satuan, dan keterangan.
- **FR-OUT-PAT-02 (P0):** Server menghitung alokasi menggunakan aturan proporsional legacy yang sudah diverifikasi; UI menunjukkan hasil per kelas dan total sebelum konfirmasi.
- **FR-OUT-PAT-03 (P0):** Pembagi nol, pasien nol, input negatif, presisi/rounding, dan batas stok ditangani deterministik.
- **FR-OUT-PAT-04 (P0):** Pengeluaran pasien memperbarui `sisa_qty` FIFO bila aturan bisnis yang berlaku mengharuskannya.

### 5.6 Pengeluaran Dokter dan Manajemen

- **FR-OUT-OTH-01 (P0):** Pengeluaran dokter mendukung distribusi kepada satu/lebih dokter berdasarkan roster dan shift/poli yang relevan.
- **FR-OUT-OTH-02 (P0):** Pengeluaran manajemen mendukung kategori/tujuan operasional dan keterangan bebas yang tervalidasi.
- **FR-OUT-OTH-03 (P0):** Beberapa item dapat diajukan sebagai satu batch dan ditampilkan sebagai ringkasan sebelum konfirmasi.

### 5.7 Paket komposit dan validasi stok

- **FR-PKG-01 (P0):** Paket Snack/Buah/Roti diurai server menjadi baris item fisik, qty komponen, supplier, dan nilai yang relevan sebelum disimpan.
- **FR-PKG-02 (P0):** Sistem menolak paket kosong/tidak lengkap; ringkasan dekomposisi ditampilkan kepada petugas.
- **FR-STK-01 (P0):** Server menggabungkan kebutuhan per item dan supplier, lalu memvalidasi stok terbaru agar beberapa baris tidak melewati saldo yang sama.
- **FR-STK-02 (P0):** Untuk barang terpantau, transaksi normal tidak menghasilkan stok negatif. Perilaku Bahan Bebas mengikuti definisi yang disahkan.
- **FR-STK-03 (P0):** Penolakan validasi tidak mengubah ledger, master, atau FIFO.
- **FR-STK-04 (P1):** Konflik perubahan data mengembalikan respons konflik yang dapat dimengerti; pengguna dapat memuat ulang dan meninjau ulang draft.

### 5.8 Riwayat, koreksi, audit, dan laporan

- **FR-HIST-01 (P0):** Riwayat menggabungkan penerimaan dan tiga jenis pengeluaran dengan filter tanggal, shift, kategori, item, supplier, tujuan, dan petugas bila kolom tersedia.
- **FR-HIST-02 (P0):** Filter pencarian literal tidak diperlakukan sebagai regex; paging server-side digunakan bila ukuran data menuntutnya.
- **FR-HIST-03 (P1):** Koreksi/pembatalan memerlukan izin, alasan, pratinjau dampak stok, dan catatan audit; gunakan reversal bila sesuai.
- **FR-AUD-01 (P0):** Semua mutasi merekam aktor, waktu server, aksi, entity/ID, nilai penting sebelum/sesudah, alasan, correlation ID, dan status operasi tanpa membocorkan secret.
- **FR-REP-01 (P1):** Laporan harian menunjukkan saldo awal, jumlah masuk, keluar, saldo akhir, serta nilai sesuai definisi bisnis dan dapat diekspor.
- **FR-REP-02 (P1):** Analisis menampilkan komposisi status stok, nilai persediaan, kategori, dan tren dengan definisi filter yang konsisten.
- **FR-EXP-01 (P1):** CSV/XLSX dibangkitkan backend atau dari dataset yang diotorisasi; formula spreadsheet tidak boleh diinjeksi dari teks user.
- **FR-SYNC-01 (P1):** Admin dapat menjalankan pemeriksaan koneksi/schema dan invalidasi cache; operasi tidak boleh diam-diam menulis ulang data.

## 6. Aturan dan Model Data

### 6.1 Tab legacy yang terlihat

`master_barang`, `master_dokter`, `stok_masuk`, `pengeluaran_pasien`, `pengeluaran_dokter`, `pengeluaran_manajemen`, `log`.

### 6.2 Kolom teramati dan catatan mapping

| Entitas | Kolom yang teramati dari kode/check | Catatan |
|---|---|---|
| Barang | `kode_barang`, `nama_barang`, `kategori`, `satuan`, `stok_sekarang`, `stok_minimum`, `harga_master`, `status`; juga dipakai: `supplier`, `harga_real` | Dokumen lama menyebut `id_barang`/`stok_minimal`; verifikasi header workbook |
| Stok masuk | `tanggal`, `shift`, `kategori`, `petugas`, `supplier`, `nama_barang`, `qty`, `harga_master`, `harga_real`, `total_harga`, `keterangan`, `sisa_qty` | `sisa_qty` digunakan untuk FIFO; ID baris tidak terlihat konsisten |
| Pengeluaran | `tanggal`, `shift`, `kategori`, kemungkinan `kategori_freetext`, `petugas`, `nama_barang`, `supplier`, `qty`, harga, `total_harga`, `keterangan`; pasien dapat memiliki tujuan/jumlah pasien | Skema berbeda per sheet dan harus dipetakan dari header aktual |
| Dokter | Tab `master_dokter`; kode merujuk roster dokter, poli, jadwal, status | Kolom persis belum diverifikasi |
| Audit | Tab `log` | Kolom persis belum diverifikasi; jangan anggap teks detail cukup sebagai audit terstruktur |

### 6.3 Aturan utama

- Jumlah dicatat positif; jenis transaksi menentukan arah mutasi.
- Semua kalkulasi uang memakai tipe decimal/representasi integer rupiah pada backend, bukan floating point binary untuk hasil finansial.
- Qty stok dapat fraksional sesuai satuan; aturan kelipatan dan precision disimpan per satuan atau dikonfirmasi.
- `kode_barang` atau ID stabil lain menjadi kunci; pencocokan nama/supplier hanya untuk kompatibilitas data lama.
- Jangan menyimpan virtual package sebagai stok fisik.
- Tanggal dan waktu disimpan ISO 8601; tampilan mengikuti zona waktu bisnis RS yang disepakati.
- Nilai kosong/NaN dari Sheets dinormalisasi di repository; API mengembalikan JSON bersih, bukan `NaN`.
- Status stok dan perlakuan `stok_minimum=0` harus diselaraskan karena terdapat variasi pada dokumen/kode legacy.

## 7. Alur UX dan Status

Setiap halaman mendukung status memuat, kosong, gagal memuat, stale/offline, sukses, validasi inline, dan konflik. Form transaksi memiliki draft lokal, ringkasan dampak, konfirmasi simpan, indikator proses, tombol yang tidak dapat dikirim berulang, serta nomor transaksi setelah sukses. Pesan error harus actionable dan tidak menampilkan traceback, credential, URL rahasia, atau isi response sensitif.

## 8. API Produk yang Diperlukan

Kontrak final dijelaskan pada [Arsitektur](ARCHITECTURE.md). Endpoint kebutuhan meliputi:

- `GET /api/v1/items`, `POST /api/v1/items`, `GET/PATCH /api/v1/items/{itemId}`
- `GET/POST/PATCH /api/v1/doctors` dan `/api/v1/doctors/{doctorId}`
- `POST /api/v1/inbound-transactions`
- `POST /api/v1/outbound-transactions` dengan `type=patient|doctor|management`
- `GET /api/v1/transactions` dan `GET /api/v1/transactions/{transactionId}`
- `POST /api/v1/transactions/{transactionId}/adjustments` atau `/void` untuk koreksi berizin
- `GET /api/v1/reports/daily`, `/api/v1/reports/stock`, `/api/v1/dashboard`
- `GET /api/v1/health/ready`, endpoint admin untuk schema/refresh/reconciliation sesuai otorisasi

Semua route tulis memvalidasi identitas/izin di server, memerlukan idempotency key, dan mengembalikan `requestId`/`operationId`.

## 9. Kebutuhan Nonfungsional

- **Keamanan:** TLS; credential Sheets hanya di backend; secret manager/environment terproteksi; CORS allowlist; autentikasi dan otorisasi server-side; rate limit; validasi/encoding output; tidak mencatat secret atau token.
- **Integritas:** validasi ulang sebelum mutasi; ID unik; idempotency; write batch; audit; rekonsiliasi; backup teruji; respons konflik yang tegas.
- **Kinerja:** target p95 baca <2,5 detik pada beban/data yang disepakati; tidak melakukan satu request Sheets per sel/baris; batching dan cache baca terukur.
- **Ketersediaan:** kegagalan Sheets ditampilkan sebagai layanan sementara tidak tersedia; jangan tampilkan saldo cache sebagai data terkini tanpa label timestamp.
- **Aksesibilitas/UX:** keyboard usable, label form, fokus modal, kontras, layout desktop dan tablet operasional; uji dengan petugas.
- **Observability:** log terstruktur, request/correlation ID, metrik latensi, error Sheets/quota, jumlah konflik/duplikasi; tanpa data sensitif yang tak diperlukan.
- **Kompatibilitas:** browser desktop/tablet yang disetujui RS; validasi ukuran dataset dan ekspor.

## 10. Kriteria Penerimaan (UAT)

- **AC-01 Penerimaan:** Dengan barang aktif dan saldo 50, petugas berwenang memasukkan qty 25. Sistem mencatat satu penerimaan, saldo menjadi 75, harga aktual dan selisih HPP tampil, dan audit memuat aktor. Pengiriman ulang dengan idempotency key yang sama tidak membuat baris kedua.
- **AC-02 Input invalid:** Qty nol/negatif, petugas tidak valid, atau supplier/item wajib yang kosong ditolak oleh API; tidak ada perubahan pada tab mana pun.
- **AC-03 Stok tidak cukup:** Saldo item terpantau 4 dan kebutuhan total 5. API menolak pengeluaran, memberi rincian kekurangan, dan tidak mengubah stok/ledger/FIFO.
- **AC-04 Agregasi multi-baris:** Dua baris untuk item yang sama masing-masing qty 3 dan saldo 5 harus ditolak berdasarkan total 6, bukan lolos secara terpisah.
- **AC-05 Paket:** Paket berisi 0,5 unit bahan A dan 1 unit bahan B untuk 10 paket menghasilkan masing-masing 5 dan 10 unit baris fisik, stok dikurangi dengan benar, virtual package tidak disimpan.
- **AC-06 FIFO/koreksi:** Pengeluaran pasien mengurangi lapisan penerimaan sesuai urutan kebijakan; koreksi menghitung delta dan saldo `sisa_qty` konsisten serta memiliki audit.
- **AC-07 Hak akses:** Pengguna hanya dapat melakukan aksi sesuai perannya walaupun memanggil API langsung.
- **AC-08 Konflik:** Dua permintaan bersamaan atas saldo terbatas tidak menghasilkan stok negatif atau pengeluaran ganda yang tidak terdeteksi; konflik/penolakan dapat ditelusuri.
- **AC-09 Laporan:** Hasil saldo awal + masuk - keluar cocok dengan rekonsiliasi manual pada sampel tanggal dan item yang disetujui.
- **AC-10 Kredensial:** Bundle, network calls browser, storage browser, error response, dan log frontend tidak memuat service account key atau token Google.
- **AC-11 Skema:** Mismatch nama/header kolom menghasilkan readiness check gagal yang menjelaskan kolom yang dibutuhkan, tanpa menulis ulang tab.

## 11. Telemetri Produk

Pantau adopsi per modul, durasi input/simpan, tingkat validasi gagal, retry/idempotency hit, konflik stok, error Sheets/quota, p95 latency, export, dan hasil rekonsiliasi. Jangan mengirim nama pasien atau detail sensitif ke analitik pihak ketiga. Data pasien/ruangan yang dicatat harus dibatasi sesuai kebutuhan bisnis dan kebijakan RS.

## 12. Rencana Rilis dan Keluar dari Legacy

1. **Discovery:** validasi proses, schema workbook, auth, volume, dan definisi laporan.
2. **Fondasi:** API read-only, mapping schema, auth, logging, contract tests, dan React shell.
3. **Pilot baca:** dashboard/master/history tanpa mutasi; cocokkan hasil dengan Streamlit.
4. **Pilot tulis:** penerimaan dan pengeluaran pada lingkungan/salinan spreadsheet dengan UAT, idempotency, failure injection, rekonsiliasi.
5. **Cutover terbatas:** backup snapshot; satu jalur mutasi resmi; batasi/disable mutasi legacy agar tidak ada dual writer; pantau dan punya rollback.
6. **Stabilisasi:** audit hasil, dukungan pengguna, tutup gap sebelum menonaktifkan Streamlit.

Tidak boleh menjalankan React dan Streamlit sebagai penulis aktif bersamaan tanpa mekanisme koordinasi yang diuji.

## 13. Keputusan Terbuka

SSO vs login aplikasi, matriks peran, schema tab aktual, ID transaksi dan barang, definisi stok bebas, aturan alokasi pasien, penyimpanan/pengelolaan komposisi paket, kewenangan koreksi, kebijakan ekspor, deployment, zona waktu, RPO/RTO, dan kapan beralih ke database transaksional.
