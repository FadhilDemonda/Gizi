# Stok-Gizi App (Refactored V3.0)

Aplikasi manajemen inventaris makanan dan stok gudang berarsitektur modular yang ditenagai oleh Python, Streamlit, dan Google Sheets.

## Struktur Direktori

Aplikasi ini telah direfaktor dari sebuah file monolitik menjadi beberapa layer untuk memudahkan *maintenance* dan pemisahan tugas (Separation of Concerns):

*   `app.py`: Sebagai *entry point* (titik masuk utama) dan pengatur *routing* sidebar. Di sini tidak ada logika bisnis, hanya navigasi ke tiap *page*.
*   `pages/`: Berisi UI Streamlit untuk masing-masing halaman (Dashboard, Master Barang, Transaksi, Laporan, dsb).
*   `services/`: Inti logika bisnis aplikasi. Berisi kalkulasi matematis (stok krisis, *bar width*, *trend*). Tidak mengandung UI (Streamlit) atau pembacaan *database*.
*   `data/`: Data Access Layer (DAL). `sheets_repository.py` bertanggung jawab langsung untuk semua urusan membaca (Load) dan menulis (Save) ke Google Sheets.
*   `utils/`: Modul *helper* dan bantuan teknis (Validasi data, injeksi HTML, pengelola *Session State*).
*   `styles/`: Penyuntik CSS global (*custom styling* dan pemilihan warna *button*).
*   `tests/`: Kumpulan *Unit Tests* (pytest) untuk memverifikasi logika bisnis pada folder `services/`.

## Cara Setup

1.  **Clone / Download Repository**
2.  **Buat Virtual Environment & Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
3.  **Setup Google Cloud Service Account:**
    *   Siapkan Google Cloud Service Account dan unduh JSON key.
    *   Buat sebuah Google Sheets dengan nama tab: `master_barang` dan `transaksi`.
    *   *Share* (Bagikan) spreadsheet Anda ke alamat email Service Account sebagai *Editor*.
4.  **Konfigurasi Secrets:**
    *   Buka folder `.streamlit`.
    *   Ubah/copy file `secrets.toml.example` menjadi `secrets.toml`.
    *   Masukkan URL Spreadsheet Anda dan detail kredensial Service Account Anda sesuai panduan di dalamnya.

## Cara Menjalankan Aplikasi Lokal

Setelah semua dependensi terinstall dan kredensial disetel:

```bash
streamlit run app.py
```
