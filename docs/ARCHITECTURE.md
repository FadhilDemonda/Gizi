# Architecture Document
## CGIZI — Sistem Informasi Manajemen Stok Gizi RS An-Nisa

---

### 1. Overview & Architectural Style
CGIZI is structured as a **Layered Monolithic Web Application** built atop the Streamlit reactive UI runtime. The application enforces a strict separation of concerns into four core layers:
1. **Presentation / UI Layer (`views/`, `styles/`)**: Streamlit components handling reactive state rendering, widget callbacks, and DOM CSS injection.
2. **Business Logic / Domain Service Layer (`services/`)**: Pure functions isolated from Streamlit APIs, computing stock mathematics, status thresholds, batch allocations, and report aggregations.
3. **Data Access / Repository Layer (`data/sheets_repository.py`)**: Gateway abstraction encapsulating Google Sheets API calls (`gspread` and `gspread-dataframe`), session caching (`@st.cache_data`), and bulk dataframe serialization.
4. **Cross-Cutting Utilities (`utils/`)**: Reusable input validators, security sanitizers, number/currency formatters, and session state initializers.

```
+-------------------------------------------------------------------+
|               Presentation Layer (views/*.py, app.py)             |
|  - Dashboard, Master Data, Transaksi, Pengeluaran, Laporan, Sync  |
+---------------------------------+---------------------------------+
                                  |
                                  v
+---------------------------------+---------------------------------+
|               Domain Service Layer (services/*.py)                |
|  - stock_service.py       - transaction_service.py                |
|  - report_service.py                                              |
+---------------------------------+---------------------------------+
                                  |
                                  v
+---------------------------------+---------------------------------+
|             Data Repository Layer (data/sheets_repository.py)     |
|  - get_sheet_data, update_sheet_data, append_rows, log_activity   |
+---------------------------------+---------------------------------+
                                  |
                                  v
+---------------------------------+---------------------------------+
|               Google Sheets Cloud Database (External)             |
|  - master_barang, master_dokter, stok_masuk, pengeluaran_*, log   |
+-------------------------------------------------------------------+
```

---

### 2. Tech Stack Table

| Layer | Technology | Version / Spec | Purpose in CGIZI |
|---|---|---|---|
| **Language Runtime** | Python | `>=3.10, 3.11` (devcontainer) | Core execution engine |
| **Web UI Framework** | Streamlit | `>=1.30.0` (`requirements.txt`) | Reactive single-page web framework and widget orchestration |
| **Data Processing** | Pandas | `>=2.0.0` (`requirements.txt`) | In-memory tabular calculations, joins, aggregations, and filtering |
| **Visualization** | Plotly | `>=5.18.0` (`requirements.txt`) | Interactive analytical charts in Dashboard and Analisis Stok |
| **Persistence Client** | gspread | `>=5.12.0` (`requirements.txt`) | Google Sheets API v4 Python wrapper |
| **Dataframe Adapter** | gspread-dataframe | `>=3.3.1` (`requirements.txt`) | High-speed 2D batch serialization between Pandas and Sheets |
| **Authentication Client**| google-auth | `>=2.25.0` (`requirements.txt`) | GCP Service Account OAuth2 token negotiation |
| **Testing** | Standalone PyUnit | Standard Library + Whitebox | 92 unit and anomaly tests in `tests/whitebox_test.py` |
| **Configuration** | TOML | `.streamlit/secrets.toml` | GCP service account credentials and spreadsheet ID |

---

### 3. System Context Diagram (C4 Level 1)

```mermaid
flowchart TD
    subgraph Users ["Hospital Actors"]
        A[Petugas Logistik Gizi]
        B[Petugas Distribusi / Penyaji]
        C[Kepala Instalasi Gizi]
        D[Admin IT / Tim DTO]
    end

    subgraph System ["CGIZI Application Boundary"]
        APP["Streamlit Application Runtime (Port 8501)"]
    end

    subgraph External ["External Services"]
        GCP["Google Cloud Platform Identity (OAuth2)"]
        SHEETS[("Google Sheets Spreadsheet API v4: Stok Gizi RS An-Nisa")]
    end

    A -->|Inbound Receipts & Master Catalog| APP
    B -->|Meal Allocations & Package Distributions| APP
    C -->|Review Reports & Stock Valuation| APP
    D -->|Cache Flush & Health Audits| APP

    APP -->|Service Account Token Exchange| GCP
    APP -->|Read Dataframes / Write Batch Ranges| SHEETS
```

---

### 4. Component / Layer Diagram (C4 Level 2)

```mermaid
graph TD
    subgraph Presentation ["Presentation Layer (views/)"]
        APP["app.py:main (Router)"]
        V_DASH["dashboard.py"]
        V_BRG["master_barang.py"]
        V_DOC["master_dokter.py"]
        V_TRX["transaksi.py"]
        V_PAS["pengeluaran_pasien.py"]
        V_DOK["pengeluaran_dokter.py"]
        V_MAN["pengeluaran_common.py"]
        V_RIW["riwayat_pengeluaran.py"]
        V_LAP["laporan_harian.py"]
        V_ANL["analisis_stok.py"]
        V_SNC["sinkronisasi.py"]
    end

    subgraph Services ["Domain Logic Layer (services/)"]
        S_STK["stock_service.py"]
        S_TRX["transaction_service.py"]
        S_REP["report_service.py"]
    end

    subgraph Utilities ["Utilities (utils/ & styles/)"]
        U_VAL["utils/validators.py"]
        U_FMT["utils/formatting.py"]
        U_STY["styles/theme.py"]
    end

    subgraph Repository ["Data Access Layer (data/)"]
        R_SHT["sheets_repository.py"]
    end

    subgraph Cloud ["Persistence Storage"]
        DB[("Google Sheets")]
    end

    APP --> V_DASH & V_BRG & V_DOC & V_TRX & V_PAS & V_DOK & V_MAN & V_RIW & V_LAP & V_ANL & V_SNC
    
    V_TRX & V_PAS & V_DOK & V_MAN --> S_TRX
    V_DASH & V_BRG & V_ANL --> S_STK
    V_LAP & V_DASH --> S_REP
    
    V_BRG & V_TRX --> U_VAL
    V_DASH & V_RIW & V_LAP --> U_FMT
    APP --> U_STY

    V_DASH & V_BRG & V_DOC & V_TRX & V_PAS & V_DOK & V_MAN & V_RIW & V_LAP & V_ANL & V_SNC --> R_SHT
    R_SHT --> DB
```

---

### 5. Project Structure

```
CGIZI/
├── .devcontainer/
│   └── devcontainer.json         # Dev container config (Python 3.11 image)
├── .streamlit/
│   ├── config.toml               # Streamlit server and theme settings
│   ├── secrets.toml              # [GIT-IGNORED] GCP Service Account private key & spreadsheet ID
│   └── secrets.toml.example      # Template for environment secret setup
├── data/
│   ├── __init__.py
│   └── sheets_repository.py      # Google Sheets connection, CRUD, cache management, activity logging
├── docs/
│   ├── PRD.md                    # Product Requirements Document
│   └── ARCHITECTURE.md           # Architecture and technical design document
├── services/
│   ├── __init__.py
│   ├── report_service.py         # Daily summary aggregations, balance movement calculations
│   ├── stock_service.py          # Stock health classifications, percentage & bar rendering math
│   └── transaction_service.py    # Transaction ID generation, stock delta validation, record building
├── styles/
│   ├── __init__.py
│   └── theme.py                  # Custom CSS stylesheets, typography, UI badges, button colors
├── tests/
│   ├── health_check.py           # Automated smoke test verifying view functions and core service logic
│   ├── test_report_service.py    # Unit tests for report calculations
│   ├── test_stock_service.py     # Unit tests for stock status rules
│   ├── test_transaction_service.py # Unit tests for inbound/outbound transactions
│   └── whitebox_test.py          # 92 white-box anomaly test suites covering injections and math boundaries
├── utils/
│   ├── __init__.py
│   ├── formatting.py             # Number, currency (IDR), HTML escaping, and badge builders
│   ├── state.py                  # Streamlit session state management routines
│   └── validators.py             # Input payload validation for master items and transactions
├── views/
│   ├── __init__.py
│   ├── analisis_stok.py          # Stock health charts, category ratio, and valuation analysis
│   ├── dashboard.py              # Executive KPI cards, low-stock warnings, recent activities
│   ├── laporan_harian.py         # Daily stock balance sheet (Beginning + In - Out = Ending)
│   ├── master_barang.py          # Catalog item management with data editor and add form
│   ├── master_dokter.py          # Doctor schedule roster and clinic room assignment
│   ├── pengeluaran.py            # Entry router redirecting to pengeluaran_common
│   ├── pengeluaran_common.py     # Generic expenditure form with in-row package unrolling
│   ├── pengeluaran_dokter.py     # Doctor mass snack grid and individual doctor distribution
│   ├── pengeluaran_pasien.py     # Proportional ward inpatient meal allocation (VIP, K1, K2, K3)
│   ├── riwayat_pengeluaran.py    # Multi-tab historical log with advanced multi-column filtering
│   ├── sinkronisasi.py           # Streamlit cache invalidation and cloud refresh screen
│   └── transaksi.py              # Inbound stock entry with HPP variance detection
├── AGENTS.md                     # AI Agent guidelines and project execution rules
├── app.py                        # Streamlit application entry point and sidebar navigation
├── README.md                     # Project overview and operational guide
└── requirements.txt              # Production Python package dependencies
```

---

### 6. Module Breakdown

#### `data/sheets_repository.py`
- **Responsibility**: Authenticates with Google Drive/Sheets API via GCP Service Account, reads worksheets into Pandas DataFrames, executes atomic cell-range replacements or row appends, and invalidates Streamlit cache.
- **Public Interface**:
  - `get_gspread_client() -> gspread.Client`
  - `get_spreadsheet() -> gspread.Spreadsheet`
  - `get_worksheet(name: str) -> gspread.Worksheet`
  - `get_sheet_data(sheet_name: str) -> pd.DataFrame` (Cached 60s)
  - `update_sheet_data(sheet_name: str, df: pd.DataFrame)`
  - `append_row(sheet_name: str, row_data: list)`
  - `append_rows(sheet_name: str, rows_data: list[list])`
  - `delete_rows(sheet_name: str, row_indices: list[int])`
  - `log_activity(petugas: str, aksi: str, detail: str)`
- **Dependencies**: `gspread`, `gspread_dataframe`, `google.oauth2.service_account`, `streamlit`.

#### `services/stock_service.py`
- **Responsibility**: Pure calculation of stock health percentages, visual progress bar widths, UI color mappings, and status filtering.
- **Public Interface**:
  - `calculate_stock_percentage(stok, min_stok) -> float`
  - `get_stock_status_label(stok, min_stok, status) -> str`
  - `get_stock_bar_width(percentage) -> int`
  - `get_stock_bar_color(status_label) -> str`
  - `filter_by_status(df, status_filter) -> pd.DataFrame`
- **Dependencies**: `pandas`, `math`.

#### `services/transaction_service.py`
- **Responsibility**: Validates outbound stock requests against current balances, calculates prospective balances, formats unique transaction IDs, and builds standard dictionary records.
- **Public Interface**:
  - `generate_transaction_id(existing_count: int) -> str` (e.g. `T0042`)
  - `validate_stock_out(stok_sekarang, jumlah_keluar) -> tuple[bool, str]`
  - `calculate_new_stock(stok_sekarang, jumlah, jenis_transaksi) -> float`
  - `build_transaction_record(...) -> dict`
- **Dependencies**: `datetime`.

#### `services/report_service.py`
- **Responsibility**: Consolidates inbound and outbound transaction series into daily balance statements and financial consumption totals.
- **Public Interface**:
  - `get_daily_summary(df_masuk, df_keluar, date) -> pd.DataFrame`
  - `get_stock_movement_report(df_transaksi, start_date, end_date) -> pd.DataFrame`
  - `calculate_cost_consumption(df_keluar) -> float`
- **Dependencies**: `pandas`.

---

### 7. Data Architecture

#### Entity Relationship Diagram (ERD)
```mermaid
erDiagram
    MASTER_BARANG ||--o{ STOK_MASUK : "replenished by"
    MASTER_BARANG ||--o{ PENGELUARAN_PASIEN : "consumed by"
    MASTER_BARANG ||--o{ PENGELUARAN_DOKTER : "consumed by"
    MASTER_BARANG ||--o{ PENGELUARAN_MANAJEMEN : "consumed by"
    MASTER_DOKTER ||--o{ PENGELUARAN_DOKTER : "assigned to"

    MASTER_BARANG {
        string id_barang PK
        string nama_barang
        string kategori
        string satuan
        float stok_sekarang
        float stok_minimal
        float harga_master
        string supplier
        string status
    }

    MASTER_DOKTER {
        string id_dokter PK
        string nama_dokter
        string poli
        string jadwal
        string status
    }

    STOK_MASUK {
        string id_transaksi PK
        string tanggal
        string id_barang FK
        string nama_barang
        string kategori
        float jumlah
        string satuan
        float harga_beli
        string supplier
        string petugas
        string keterangan
    }

    PENGELUARAN_PASIEN {
        string id_transaksi PK
        string tanggal
        string kategori
        string id_barang FK
        string nama_barang
        float jumlah
        string satuan
        float harga_satuan
        float total_biaya
        string petugas
        string keterangan
    }

    PENGELUARAN_DOKTER {
        string id_transaksi PK
        string tanggal
        string kategori
        string id_barang FK
        string nama_barang
        float jumlah
        string satuan
        float harga_satuan
        float total_biaya
        string petugas
        string keterangan
    }

    PENGELUARAN_MANAJEMEN {
        string id_transaksi PK
        string tanggal
        string kategori
        string id_barang FK
        string nama_barang
        float jumlah
        string satuan
        float harga_satuan
        float total_biaya
        string petugas
        string keterangan
    }

    LOG {
        string timestamp
        string petugas
        string aksi
        string detail
    }
```

#### Data Dictionary Table

| Entity (Sheet) | Field Name | Data Type | Nullable | Description & Constraints |
|---|---|---|---|---|
| `master_barang` | `id_barang` | string | No | Item identifier (e.g. "BRG001") |
| `master_barang` | `nama_barang` | string | No | Unique item label |
| `master_barang` | `kategori` | string | No | Classification (Bahan Kering, Basah, Snack, Buah, etc.) |
| `master_barang` | `satuan` | string | No | Metric unit (Kg, Pcs, Bks, Liter, Butir) |
| `master_barang` | `stok_sekarang` | float | No | Current physical balance (`>= 0`) |
| `master_barang` | `stok_minimal` | float | No | Low-stock threshold |
| `master_barang` | `harga_master` | float | No | Standard catalog purchase price (HPP in IDR) |
| `master_barang` | `supplier` | string | Yes | Default supplier names (comma-separated if multiple) |
| `master_barang` | `status` | string | No | "True" for monitored stock; "False" for Bahan Bebas |
| `stok_masuk` | `id_transaksi` | string | No | Unique inbound transaction code (e.g. "IN-20261005-001") |
| `stok_masuk` | `tanggal` | string | No | Inbound receipt date (`YYYY-MM-DD`) |
| `stok_masuk` | `jumlah` | float | No | Received quantity (`> 0`) |
| `stok_masuk` | `harga_beli` | float | No | Invoice unit purchase price |
| `stok_masuk` | `petugas` | string | No | Receiving staff name |
| `pengeluaran_*` | `id_transaksi` | string | No | Outbound code (e.g. "OUT-20261005-001") |
| `pengeluaran_*` | `kategori` | string | No | Recipient group (e.g. "VIP", "Dokter Praktek", "Direksi") |
| `pengeluaran_*` | `jumlah` | float | No | Consumed physical quantity (`> 0`) |
| `pengeluaran_*` | `harga_satuan` | float | No | Unit price applied from `master_barang.harga_master` |
| `pengeluaran_*` | `total_biaya` | float | No | Total valuation (`jumlah * harga_satuan`) |
| `log` | `timestamp` | string | No | ISO / local formatted audit timestamp |
| `log` | `aksi` | string | No | Action type (e.g. "Stok Masuk", "Tambah Barang") |

#### Migration Strategy
Because Google Sheets is a schema-on-read tabular datastore, migrations are performed by executing code scripts (or manually in Google Sheets) to add columns. Column orders are preserved by reading headers dynamically via `df.columns` in `data/sheets_repository.py`.

---

### 8. System Flows

#### Flow 1: Application Startup and Initialization
```mermaid
sequenceDiagram
    autonumber
    actor User as Client Browser
    participant App as app.py
    participant Theme as styles/theme.py
    participant Repo as data/sheets_repository.py
    participant GCP as Google Cloud API

    User->>App: GET / (Streamlit Session Start)
    App->>App: st.set_page_config(layout="wide")
    App->>Theme: apply_theme() (Inject Custom CSS)
    Theme-->>App: CSS Injected
    App->>App: Render Sidebar Navigation
    User->>App: Select Menu (e.g. "Dashboard")
    App->>Repo: get_sheet_data("master_barang")
    alt Cache Valid (<60s)
        Repo-->>App: Return Cached DataFrame
    else Cache Expired / First Run
        Repo->>GCP: wks.get_all_values()
        GCP-->>Repo: 2D Matrix of Cells
        Repo->>Repo: Clean whitespaces & convert numeric dtypes
        Repo-->>App: Return Fresh DataFrame & Store in Cache
    end
    App->>User: Render Dashboard Visualizations
```
*Step-by-step*:
1. Streamlit receives client HTTP connection and executes `app.py`.
2. `st.set_page_config` sets browser tab title and full-width layout.
3. `styles/theme.py:apply_theme()` injects custom CSS for metric cards, tables, and buttons.
4. User selects a navigation view from `st.sidebar.radio`.
5. The view requests dataframes via `sheets_repository.py:get_sheet_data(sheet_name)`.
6. `@st.cache_data(ttl=60)` checks if the cached dataframe exists and is fresh; if not, requests raw cells from Google Sheets API, parses them via Pandas, caches them, and returns.

#### Flow 2: Inbound Stock Creation Request (Create)
```mermaid
sequenceDiagram
    autonumber
    actor Staff as Petugas Logistik
    participant View as views/transaksi.py
    participant Val as utils/validators.py
    participant Svc as services/transaction_service.py
    participant Repo as data/sheets_repository.py
    participant Sheets as Google Sheets API

    Staff->>View: Enter Inbound Goods (Item, Qty, Harga, Supplier)
    Staff->>View: Click "Simpan Transaksi"
    View->>Val: validate_transaction_input(items, petugas)
    Val-->>View: Input Valid (True)
    View->>Repo: get_sheet_data("master_barang")
    Repo-->>View: master_df
    loop For each item in rows
        View->>Svc: calculate_new_stock(current_stok, qty, "+ Stok Masuk")
        Svc-->>View: new_stok
        View->>View: Update master_df in memory
        View->>Svc: build_transaction_record(...)
        Svc-->>View: new_record_dict
    end
    View->>Repo: append_rows("stok_masuk", new_rows_data)
    Repo->>Sheets: wks.append_rows(new_rows_data)
    Sheets-->>Repo: 200 OK
    View->>Repo: update_sheet_data("master_barang", master_df)
    Repo->>Sheets: set_with_dataframe(master_df)
    Sheets-->>Repo: 200 OK
    Repo->>Repo: Clear Cache (get_sheet_data.clear())
    View->>Repo: log_activity(petugas, "Stok Masuk", detail)
    Repo->>Sheets: wks.append_row(log_data)
    Sheets-->>Repo: 200 OK
    View->>Staff: st.success("Transaksi Berhasil Disimpan!")
```
*Step-by-step*:
1. Staff fills out dynamic input rows for received items.
2. `utils/validators.py:validate_transaction_input` checks for non-empty petugas and positive quantities.
3. For each row, `services/transaction_service.py:calculate_new_stock` computes the incremented balance.
4. `data/sheets_repository.py:append_rows` sends new rows to `stok_masuk`.
5. `data/sheets_repository.py:update_sheet_data` replaces `master_barang` with the updated dataframe.
6. `get_sheet_data.clear()` invalidates cache.
7. `data/sheets_repository.py:log_activity` writes an audit trail.

#### Flow 3: Outbound Inpatient Meal Distribution (Read, Compute & Deduct)
```mermaid
sequenceDiagram
    autonumber
    actor Staff as Petugas Distribusi
    participant View as views/pengeluaran_pasien.py
    participant Svc as services/transaction_service.py
    participant Repo as data/sheets_repository.py
    participant Sheets as Google Sheets API

    Staff->>View: Input Bed Counts (VIP=2, K1=3, K2=0, K3=0)
    Staff->>View: Select Menu Items & Total Qty (e.g. 10 Pcs)
    View->>View: Proportional Split: VIP=4 Pcs, K1=6 Pcs
    Staff->>View: Click "Simpan Pengeluaran Pasien"
    View->>Repo: get_sheet_data("master_barang")
    Repo-->>View: master_df
    View->>Svc: validate_stock_out(stok_sekarang, total_qty)
    alt Insufficient Stock
        Svc-->>View: (False, "Stok tidak mencukupi")
        View->>Staff: st.error("Stok Tidak Cukup!")
    else Sufficient Stock
        Svc-->>View: (True, "OK")
        View->>Repo: append_rows("pengeluaran_pasien", patient_rows)
        View->>Repo: update_sheet_data("master_barang", master_df_deducted)
        Repo->>Sheets: Batch Commit
        Repo->>Repo: Invalidate Cache
        View->>Staff: Render Printable Receipt Modal
    end
```

#### Flow 4: Master Catalog Update & Edit
```mermaid
sequenceDiagram
    autonumber
    actor Staff as Petugas
    participant View as views/master_barang.py
    participant Val as utils/validators.py
    participant Repo as data/sheets_repository.py
    participant Sheets as Google Sheets API

    Staff->>View: Edits Cells in st.data_editor
    Staff->>View: Click "Simpan Perubahan"
    View->>Val: validate_edited_dataframe(edited_df)
    alt Duplicate Code or Null Cells
        Val-->>View: (False, "Kode duplikat atau ada sel kosong")
        View->>Staff: st.error(message)
    else Validation Passed
        Val-->>View: (True, "Valid")
        View->>Repo: update_sheet_data("master_barang", edited_df)
        Repo->>Sheets: set_with_dataframe(edited_df)
        Sheets-->>Repo: 200 OK
        Repo->>Repo: get_sheet_data.clear()
        View->>Repo: log_activity(petugas, "Update Master Barang", summary)
        View->>Staff: st.success("Data Master Berhasil Diperbarui!")
    end
```

#### Flow 5: Row Deletion Flow
```mermaid
sequenceDiagram
    autonumber
    actor Staff as User
    participant View as views/master_barang.py
    participant Repo as data/sheets_repository.py
    participant Sheets as Google Sheets API

    Staff->>View: Select Item & Click "Hapus Barang"
    View->>Repo: delete_rows("master_barang", [row_index])
    Repo->>Repo: Sort row_indices descending
    loop For each index
        Repo->>Sheets: wks.delete_rows(index)
    end
    Sheets-->>Repo: 200 OK
    Repo->>Repo: get_sheet_data.clear()
    View->>Repo: log_activity("User", "Hapus Barang", item_name)
    View->>Staff: st.success("Barang Berhasil Dihapus!")
```

#### Flow 6: Authentication & Authorization Flow
```mermaid
sequenceDiagram
    autonumber
    actor Staff as User
    participant View as Streamlit Views
    participant State as Streamlit Session State

    Staff->>View: Access View (Open Terminal)
    Note over View,State: No Central Login Gateway [Inferred]
    Staff->>View: Select "Nama Petugas" from dropdown / input
    View->>State: Store petugas in session_state
    View->>View: Check if Petugas is non-empty before Submit
    alt Petugas Empty
        View->>Staff: st.error("Identitas Petugas wajib diisi!")
    else Petugas Provided
        View->>View: Proceed with Transaction
    end
```

#### Flow 7: Error Handling & Resilience Flow
```mermaid
sequenceDiagram
    autonumber
    actor User as User
    participant View as Streamlit View
    participant Repo as data/sheets_repository.py
    participant API as Google API

    View->>Repo: Read / Write Request
    alt Network / Quota Exception (APIError 429)
        Repo->>API: Call Google Sheets API
        API-->>Repo: 429 ResourceExhausted
        Repo-->>View: Raise Exception
        View->>View: Catch Exception in try/except block
        View->>User: st.error("Gagal terhubung ke Google Sheets. Coba beberapa saat lagi.")
    else Normal Execution
        Repo->>API: Call Google Sheets API
        API-->>Repo: 200 OK
        Repo-->>View: Result Data
    end
```

---

### 9. API Design
CGIZI does not expose a public REST or GraphQL HTTP API. It operates as a server-side rendered application where user interactions trigger internal Streamlit component callbacks:
- **Internal Contract**: Functions in `services/` and `data/` communicate via typed Python arguments and Pandas DataFrames.
- **Data Serialization**: Two-way dataframe conversions via `gspread_dataframe` (`get_as_dataframe` and `set_with_dataframe`).
- **Data Export Formats**: Users can download CSV or Microsoft Excel (`.xlsx`) files via `st.download_button` in `views/riwayat_pengeluaran.py` and `views/laporan_harian.py`.

---

### 10. Security Architecture
- **Authentication**: Physical terminal trust model. Staff select their identity via UI inputs (`petugas`).
- **Authorization**: Flat access model. All screens are universally accessible from the sidebar.
- **Secrets Management**: Service account private keys are isolated inside `.streamlit/secrets.toml` which is ignored by git (`.gitignore`).
- **Injection Protection**: In-memory HTML rendering utilizes `utils/formatting.py:escape_html` to prevent stored Cross-Site Scripting (XSS).
- **Known Weaknesses**:
  - Lack of password authentication permits unauthorized impersonation on unattended stations.
  - Lack of fine-grained Google Sheets cell-level locks; the GCP Service Account possesses broad Editor permissions on the entire spreadsheet.

---

### 11. Configuration & Environments

#### Environment Matrix
- **Development**: Local machine running `streamlit run app.py` with `.streamlit/secrets.toml`.
- **Container**: VS Code DevContainer using `.devcontainer/devcontainer.json` on Python 3.11 image.
- **Production**: Streamlit Community Cloud or local on-premise server with production Google Sheet ID in secrets.

#### Secrets & Configuration Variables Table
| Config Key | Storage Location | Type | Description |
|---|---|---|---|
| `spreadsheet_id` | `secrets.toml` | string | Google Sheets Unique Identifier |
| `gcp_service_account.type` | `secrets.toml` | string | "service_account" |
| `gcp_service_account.project_id` | `secrets.toml` | string | GCP Project ID |
| `gcp_service_account.private_key_id` | `secrets.toml` | string | Key identifier |
| `gcp_service_account.private_key` | `secrets.toml` | string | RSA private key string |
| `gcp_service_account.client_email` | `secrets.toml` | string | Service account email |

---

### 12. Deployment & Infrastructure
- **Hosting Pattern**: Streamlit server process (port 8501).
- **Devcontainer**: `.devcontainer/devcontainer.json` installs Python 3.11 with automatic post-create dependency installation via `pip install -r requirements.txt`.
- **Stateless Web Tier**: Streamlit application server holds minimal session state; all persistent states reside in Google Sheets.

---

### 13. Observability
- **Audit Logging**: Every transaction and master edit is appended to the `log` worksheet via `data/sheets_repository.py:log_activity(petugas, aksi, detail)`.
- **Application Logs**: Console stdout/stderr outputs standard Streamlit operational telemetry.
- **Telemetry Deficit**: No external APM (e.g. Sentry, Datadog) currently integrated `[Inferred]`.

---

### 14. Testing Strategy
- **Framework**: Python Standard Library + Custom Test Runners.
- **Suites**:
  - `tests/test_stock_service.py`: Stock percentages, status badges, bar width clamping.
  - `tests/test_transaction_service.py`: Transaction ID generation, stock delta validation.
  - `tests/test_report_service.py`: Daily balance and consumption aggregations.
  - `tests/health_check.py`: Smoke testing verifying imports and module linkages.
  - `tests/whitebox_test.py`: 92 boundary tests covering XSS injection, division by zero, float precision, and simulated race conditions.
- **Coverage Gaps**: No automated end-to-end browser integration tests (e.g. Playwright/Selenium) for Streamlit UI interactions.

---

### 15. Architectural Decisions (ADR)

#### ADR-001: Google Sheets as Persistent Datastore `[Inferred]`
- **Context**: The hospital nutrition department required rapid cloud access, zero-cost database infrastructure, and spreadsheet familiarity.
- **Decision**: Adopt Google Sheets via `gspread` and `gspread-dataframe` instead of a SQL database.
- **Consequence**: Zero database server maintenance, but subjects the app to API rate limits (60 writes/min) and potential concurrency overwrite hazards.

#### ADR-002: Streamlit for Full-Stack Presentation `[Inferred]`
- **Context**: Rapid development of data-centric dashboards without needing a separate React/Vue frontend and FastAPI/Django backend.
- **Decision**: Use Streamlit to build reactive web screens in pure Python.
- **Consequence**: Fast development speed, but standardizes full-page re-execution on user input changes requiring aggressive caching (`@st.cache_data`).

#### ADR-003: In-Memory Virtual Package Unrolling
- **Context**: Patients and doctors receive composite packages (e.g. "Paket Snack"), but physical inventory tracks individual raw cakes and drinks.
- **Decision**: Decompose packages into physical sub-items in Python memory during transaction submission before writing to Google Sheets.
- **Consequence**: Google Sheets always holds true physical inventory balances; virtual packages never pollute stock ledgers.

---

### 16. Technical Debt & Risks

| Issue / Debt | Impact | Severity | Recommended Fix |
|---|---|---|---|
| **Race Conditions on Stock Updates** | Two simultaneous users can overwrite each other's stock balance calculations. | High | Implement optimistic locking by tracking a version column in `master_barang`. |
| **Reverse Stock Calculation in Reports** | Daily reports recalculate past opening stock by subtracting subsequent transactions in memory. | Medium | Store daily closing snapshots in a dedicated `stok_harian` worksheet. |
| **No Transaction Reversal UI** | Staff cannot void erroneous entries directly from the web interface. | Medium | Add a "Batalkan Transaksi" action in `riwayat_pengeluaran.py` that reverses inventory balances. |
| **Google Sheets 60s Cache Stale Window** | If user A submits a transaction, user B might see stale data for up to 60 seconds if cache is not cleared globally. | Low | Configure Streamlit cache keys with short TTL or broadcast cache purge events. |

---

### 17. Scalability & Improvement Recommendations
1. **Database Migration**: When transaction volume exceeds 20,000 rows, migrate data layer to SQLite (local) or PostgreSQL (cloud) using SQLAlchemy ORM.
2. **Authentication Middleware**: Introduce lightweight JWT or session-based PIN login per staff member.
3. **Automated Offline Fallback**: Implement local SQLite caching so the nutrition department can continue recording meal distribution even during internet outages.
