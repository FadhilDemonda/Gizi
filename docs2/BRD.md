# Dokumen Kebutuhan Bisnis (BRD)
## CGIZI — Migrasi Antarmuka ke React dengan Google Sheets

| Atribut | Nilai |
|---|---|
| Versi | 1.0 Draft |
| Tanggal | 5 Oktober 2026 |
| Pemilik proses | Instalasi Gizi RS An-Nisa (perlu konfirmasi) |
| Status | Baseline reverse-engineered, menunggu validasi stakeholder |
| Sistem sumber | Aplikasi Streamlit pada repository ini |

## 1. Ringkasan Eksekutif

CGIZI mendukung pengelolaan persediaan bahan makanan Instalasi Gizi RS An-Nisa: data master barang dan dokter, penerimaan barang, pengeluaran untuk pasien/dokter/manajemen, pemantauan stok, laporan, serta audit aktivitas. Persistensi saat ini menggunakan beberapa tab Google Sheets melalui backend Python `gspread`; antarmuka saat ini menggunakan Streamlit.

Tujuan inisiatif ini adalah mengganti pengalaman antarmuka menjadi aplikasi React tanpa memindahkan penyimpanan dari Google Sheets pada fase awal. Rekomendasi bisnis/teknis adalah React sebagai klien web, API Python sebagai lapisan server, dan Google Sheets hanya diakses oleh API menggunakan kredensial service account. Browser tidak boleh terhubung langsung ke Sheets atau menerima private key.

Migrasi harus mempertahankan alur kerja dan aturan hitung yang sudah dipakai, sambil mengurangi risiko yang terlihat pada implementasi: validasi transaksi tidak terpusat di server API (karena UI dan logika berjalan dalam satu aplikasi), identifikasi baris transaksi belum seragam, serta pembaruan stok dan ledger menggunakan beberapa penulisan sheet yang tidak membentuk transaksi database penuh.

## 2. Latar Belakang dan Kondisi Saat Ini

### 2.1 Kondisi teramati

- `app.py` mengarahkan pengguna ke dashboard, analisis stok, penerimaan barang, tiga jenis pengeluaran, master barang/dokter, dan laporan.
- `data/sheets_repository.py` membaca dan menyimpan tab Google Sheets; pembacaan memakai cache Streamlit dan penyimpanan mengganti isi worksheet melalui clear lalu tulis DataFrame.
- Tab yang diharapkan health check: `master_barang`, `master_dokter`, `stok_masuk`, `pengeluaran_pasien`, `pengeluaran_dokter`, `pengeluaran_manajemen`, dan `log`.
- Master barang pada health check mensyaratkan `kode_barang`, `nama_barang`, `kategori`, `satuan`, `stok_sekarang`, `stok_minimum`, `harga_master`, dan `status`. Alur aplikasi juga memakai `supplier` serta dapat menambah `harga_real`.
- Penerimaan merekam `tanggal`, `shift`, `kategori`, `petugas`, `supplier`, `nama_barang`, `qty`, `harga_master`, `harga_real`, `total_harga`, `keterangan`, dan `sisa_qty`.
- Pengeluaran menulis baris barang fisik, dengan antara lain `tanggal`, `shift`, `kategori`, `kategori_freetext`, `nama_barang`, `supplier`, `qty`, harga, nilai total, dan keterangan.
- Alur pengeluaran pasien/koreksi menggunakan `sisa_qty` pada penerimaan untuk penyesuaian FIFO. Pengeluaran paket Snack/Buah/Roti diurai menjadi item fisik sebelum ditulis.
- Tidak ditemukan kontrak API atau autentikasi pengguna formal pada baseline; nama petugas pada beberapa formulir dimasukkan sebagai teks.

### 2.2 Masalah bisnis yang hendak ditangani

- UI Streamlit membatasi fleksibilitas pengalaman kerja, navigasi dan interaksi data yang lebih kaya.
- Pemisahan frontend dan backend diperlukan untuk mendukung pengembangan UI mandiri, namun tanpa membocorkan kredensial Google.
- Aturan stok harus dijalankan oleh server untuk mencegah klien melewati validasi.
- Operasi multi-tab dan konkurensi perlu dibuat lebih terkendali dan dapat diaudit.
- Spesifikasi dan skema perlu diseragamkan karena sebagian dokumen/kode menyebut nama kolom berbeda (`id_barang`/`kode_barang`, `stok_minimal`/`stok_minimum`, dan `jumlah`/`qty`).

## 3. Tujuan Bisnis

1. Mempertahankan proses pencatatan stok dan transaksi yang berjalan saat ini saat UI dimigrasikan.
2. Menyediakan UI React yang responsif untuk petugas gudang/distribusi dan pembaca laporan.
3. Memastikan aturan validasi, kalkulasi, identitas petugas, dan audit dijalankan pada backend.
4. Mempertahankan Google Sheets sebagai penyimpanan untuk fase awal, dengan semua akses privat melalui backend.
5. Menurunkan risiko salah hitung, duplikasi akibat pengiriman ulang, kehilangan jejak koreksi, dan penulisan stok berdasarkan data kedaluwarsa.
6. Menyediakan jalur evolusi ke database transaksional bila volume atau kebutuhan konsistensi melebihi kemampuan Sheets.

## 4. Bukan Tujuan

- Mengganti Google Sheets pada fase pertama.
- Mengubah kebijakan pengadaan, resep/menu gizi, alokasi biaya rumah sakit, atau proses persetujuan yang belum disepakati.
- Menyediakan integrasi HIS/EHR, billing pasien, barcode, multi-rumah-sakit, atau aplikasi mobile native.
- Mengklaim konsistensi transaksi setara database relasional selama Sheets masih menjadi penyimpanan.
- Menghapus aplikasi Streamlit sebelum pengganti lulus UAT dan rekonsiliasi data.

## 5. Pemangku Kepentingan dan Kebutuhan

| Pemangku kepentingan | Tanggung jawab | Kebutuhan bisnis |
|---|---|---|
| Petugas logistik gizi | Master barang dan penerimaan | Input cepat, supplier jelas, jumlah/harga akurat, peringatan selisih HPP |
| Petugas distribusi | Pengeluaran harian | Pencatatan multi-item, distribusi pasien/dokter/unit, validasi stok dan paket |
| Kepala Instalasi Gizi | Pengawasan operasional | Stok kritis, nilai persediaan, ringkasan konsumsi, laporan yang dapat diekspor |
| Admin/Tim DTO | Operasional aplikasi | Konektivitas, konfigurasi, audit, diagnosis kegagalan, prosedur pemulihan |
| Pemilik spreadsheet | Pengelolaan data | Akses service account terbatas, tab/header stabil, backup dan kontrol perubahan |

Peran dan hak akses di tabel ini merupakan sasaran, bukan bukti bahwa sistem legacy sudah menerapkan autentikasi/otorisasi.

## 6. Proses Bisnis Sasaran

### 6.1 Penerimaan barang

1. Petugas terautentikasi membuka form penerimaan, menentukan tanggal/shift, supplier, keterangan nota, dan item.
2. Sistem menampilkan HPP master serta harga beli aktual dan selisihnya.
3. Backend memvalidasi petugas, supplier, item aktif, jumlah positif, harga yang valid, dan permintaan duplikat.
4. Backend membaca ulang data yang diperlukan, menyusun ledger penerimaan dan saldo stok baru, lalu mengirim perubahan secara terkoordinasi.
5. Sistem mengembalikan nomor transaksi dan mencatat audit; kegagalan parsial harus dapat diidentifikasi dan direkonsiliasi.

### 6.2 Pengeluaran

1. Petugas memilih alur Pasien, Dokter, atau Manajemen, kategori/tujuan, tanggal/shift, dan item.
2. Untuk pasien, masukan jumlah pasien menurut kelas/ruangan diproses dengan aturan alokasi yang harus dikonfirmasi terhadap kode aktual dan disajikan kembali untuk persetujuan sebelum simpan.
3. Paket Snack/Buah/Roti diurai di server menjadi kebutuhan bahan fisik; paket virtual tidak menjadi item stok.
4. Backend menggabungkan kebutuhan per item/supplier, memvalidasi saldo terbaru dan mengecualikan item Bahan Bebas sesuai aturan.
5. Backend mencatat baris ledger, mengurangi stok, memperbarui FIFO bila diwajibkan, dan merekam aktor serta audit.

### 6.3 Koreksi/penghapusan transaksi

1. Pengguna berwenang mencari transaksi dan mengajukan perubahan dengan alasan.
2. Backend menghitung delta antara nilai lama dan baru; perubahan stok dan FIFO mengikuti delta, bukan menimpa saldo secara buta.
3. Perubahan memiliki jejak siapa/kapan/alasan dan dapat direkonsiliasi. Rekomendasi produk adalah void/reversal daripada penghapusan permanen.
4. Hak mengoreksi atau membatalkan transaksi harus dikonfirmasi dalam UAT.

### 6.4 Pelaporan

Pengguna memilih tanggal/periode, kategori, supplier, barang, tujuan, atau petugas. Sistem menyajikan stok, pergerakan masuk/keluar, nilai, status, dan ekspor sesuai hak akses. Rumus saldo pembukaan/penutupan harus direkonsiliasi dengan spreadsheet sebelum dijadikan laporan resmi.

## 7. Aturan Bisnis Baseline

- Jumlah penerimaan dan pengeluaran yang disimpan harus positif; nilai input nol/kosong ditolak bila transaksi membutuhkan item.
- Stok item terpantau tidak boleh turun di bawah nol melalui alur pengeluaran normal.
- Bahan Bebas dikecualikan dari peringatan/pembatasan stok berdasarkan kombinasi flag `status` dan/atau minimum nol yang dipakai kode. Kriteria final harus diseragamkan.
- Status stok di kode legacy membedakan Habis/Kritis, Mendekati Min (ambang 1,25 kali minimum), Aman, dan Bahan Bebas; detail batas nol/minimum perlu validasi dengan pemilik proses.
- Selisih harga beli terhadap HPP ditampilkan saat penerimaan.
- Paket virtual diurai menjadi item fisik dan supplier yang bersangkutan; seluruh komponen divalidasi.
- Setiap perubahan data harus menyertakan identitas petugas terautentikasi dan dicatat pada audit log.
- Satuan fraksional dipertahankan pada presisi dua desimal/kelipatan 0,05 bila berlaku; validasi unit bisnis diperlukan.
- Format tampilan mata uang adalah Rupiah; tanggal/waktu disimpan dengan format baku dan zona waktu yang disepakati.

## 8. Ruang Lingkup

### Termasuk fase migrasi

- Master barang dan master dokter.
- Penerimaan stok dan riwayat/koreksi penerimaan.
- Pengeluaran pasien, dokter, dan manajemen.
- Konfigurasi/penguraian paket yang sekarang tersedia pada form.
- Dashboard, analisis stok, laporan harian, riwayat pengeluaran/harga, ekspor, dan refresh data.
- Backend API, autentikasi/otorisasi minimum, audit, pengujian, deployment, backup, serta rekonsiliasi.

### Tidak termasuk kecuali disetujui

- Migrasi penyimpanan ke DB baru.
- Sinkronisasi klinis atau otomatisasi pembelian.
- Alur approval berjenjang, costing resep, dan pelaporan regulator.
- Perubahan struktur spreadsheet destruktif tanpa pemetaan dan backup.

## 9. Ukuran Keberhasilan

- Seluruh skenario UAT prioritas Must lulus dan total saldo master cocok dengan rekonsiliasi sebelum cutover.
- Tidak ada private key/service-account credential pada bundle frontend, source map publik, browser storage, atau log.
- Tidak ada transaksi normal yang menyimpan jumlah negatif atau melebihi stok terpantau pada pemeriksaan pra-simpan.
- Setiap mutasi mempunyai aktor terverifikasi, timestamp, ID unik/idempotency key, dan catatan audit.
- 100% tab dan header yang disepakati lulus pemeriksaan skema sebelum cutover.
- Target kinerja awal: p95 API baca umum < 2,5 detik di jaringan RS untuk dataset operasional yang disepakati; target perlu diukur dengan spreadsheet aktual.
- Ada prosedur backup/restore dan latihan pemulihan yang berhasil sebelum sistem lama dipensiunkan.
- Pengguna kunci menyelesaikan alur kerja utama tanpa pencatatan ganda antara aplikasi baru dan lama setelah periode cutover.

## 10. Risiko dan Mitigasi

| Risiko | Dampak | Mitigasi |
|---|---|---|
| Sheets bukan database transaksional; dua request bersamaan mengubah stok | Stok hilang/oversell | Backend menjadi satu pintu, serialisasi mutasi untuk MVP satu replika, batch update, idempotency, pemeriksaan ulang dan rekonsiliasi; rencanakan DB relasional jika beban meningkat |
| Penulisan multi-tab gagal sebagian | Ledger dan saldo tidak cocok | Gunakan satu permintaan batch Sheets bila memungkinkan, catat status operasi, buat rekonsiliasi dan prosedur kompensasi; uji kegagalan jaringan |
| Header/ID legacy tidak konsisten | Data salah dipetakan | Inventarisasi workbook aktual, schema contract, backup, dry-run dan laporan mapping sebelum migrasi |
| Kredensial bocor ke browser/repository | Akses tidak sah ke data | Simpan secret hanya pada secret manager/runtime backend, rotasi kunci yang terlanjur terpapar, verifikasi `.gitignore` dan artefak build |
| Cache stale | Saldo/stock status salah | Cache baca pendek/berdasarkan domain; invalidasi setelah write; refresh membaca sumber; jangan cache validasi final transaksi |
| Transaksi historis tidak memiliki ID stabil | Koreksi salah baris/duplikat | Tetapkan ID baru, strategi ID legacy, checksum/identitas komposit sementara, hindari destructive rewrite tanpa audit |
| Perubahan workflow mengejutkan pengguna | Kesalahan input saat operasional | Prototipe, UAT bersama petugas, pelatihan, pilot paralel dengan kontrol dan cutoff yang jelas |

## 11. Asumsi dan Keputusan Terbuka

1. Apakah React dan backend akan di-host pada jaringan/akun cloud RS, dan apakah sudah ada domain/TLS/SSO?
2. Apakah tetap memakai service account spreadsheet yang sekarang atau membuat akun khusus API dengan akses minimum? Rekomendasi: khusus API dan rotasi bila secret pernah masuk repository.
3. Apa header/tab, formula, validation rules, named ranges, proteksi, dan ukuran data aktual pada spreadsheet produksi?
4. Apakah satu bahan bisa memiliki beberapa baris supplier dan apakah saldo disimpan per supplier atau per barang?
5. Definisi final Bahan Bebas: flag `status`, `stok_minimum=0`, atau keduanya?
6. Formula alokasi pasien per kelas, aturan pembulatan, dan komponen paket mana yang disimpan/persisten?
7. Siapa boleh menambah master, mengoreksi/membatalkan transaksi, mengekspor laporan, dan mengelola pengguna?
8. Apakah saldo stok harus selalu konsisten real-time untuk banyak petugas serentak? Jika ya, Sheets mungkin tidak memadai sebagai sumber transaksi utama.
9. Zona waktu bisnis, kalender, format tanggal, retensi audit, target RPO/RTO, serta jadwal backup?

## 12. Kriteria Persetujuan BRD

BRD dapat disetujui setelah Kepala Instalasi Gizi, perwakilan logistik/distribusi, DTO/IT, dan pemilik spreadsheet memvalidasi proses, definisi data, prioritas, batas konsistensi, serta jawaban atas keputusan terbuka yang memengaruhi UAT dan cutover.
