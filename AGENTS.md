# AGENTS.md — AI Agent Operating Instructions
## CGIZI — Sistem Informasi Manajemen Stok Gizi RS An-Nisa

---

### 1. Project Summary
CGIZI is a web-based nutrition inventory and expenditure management system for RS An-Nisa's Nutrition Department (Instalasi Gizi). Built in Python with Streamlit and Pandas, it tracks food supply stock, inbound receipts, clinical inpatient meal allocations, physician snack boxes, and administrative disbursements. All persistent storage is backed by Google Sheets via `gspread` and `gspread-dataframe`.

---

### 2. Tech Stack & Versions
- **Language**: Python 3.10 / 3.11 (`.devcontainer/devcontainer.json`)
- **Web UI Framework**: Streamlit `>= 1.30.0`
- **Data Analysis**: Pandas `>= 2.0.0`
- **Visualization**: Plotly `>= 5.18.0`
- **Persistence**: Google Sheets API v4 via `gspread >= 5.12.0` and `gspread-dataframe >= 3.3.1`
- **Auth Client**: `google-auth >= 2.25.0`
- **Testing**: Standalone test runners (`tests/whitebox_test.py`, `tests/health_check.py`) using Python standard library

---

### 3. Setup & Commands

#### Install Dependencies
```bash
pip install -r requirements.txt
```

#### Run Local Development Server
```bash
streamlit run app.py
```
*(Runs on `http://localhost:8501`)*

#### Run Tests
```bash
# Run 92 white-box anomaly and boundary tests
python tests/whitebox_test.py

# Run application health check and smoke tests
python tests/health_check.py

# Run individual service test suites
python -m unittest tests/test_stock_service.py
python -m unittest tests/test_transaction_service.py
python -m unittest tests/test_report_service.py
```

#### Syntax Verification & Compile
```bash
python -m py_compile app.py
python -m py_compile views/*.py
python -m py_compile services/*.py
python -m py_compile data/*.py
```

---

### 4. Project Structure Map

| Directory / File | Description & Purpose |
|---|---|
| `app.py` | Application entry point, page config, theme application, and sidebar navigation router. |
| `views/` | Streamlit presentation screens (forms, data editors, visual layouts, and widgets). |
| `services/` | Pure business logic functions (stock arithmetic, status labeling, aggregations). |
| `data/sheets_repository.py` | Google Sheets database gateway, CRUD operations, caching, and activity logging. |
| `styles/theme.py` | Custom CSS stylesheets, typography, UI badges, and dynamic button themes. |
| `utils/` | Cross-cutting input validators (`validators.py`), formatters (`formatting.py`), and state helpers (`state.py`). |
| `tests/` | Unit, smoke, and white-box test suites (`whitebox_test.py`, `health_check.py`). |
| `.streamlit/secrets.toml` | GCP Service Account credentials and target Google Spreadsheet ID (Git-ignored). |
| `docs/PRD.md` | Product Requirements Document. |
| `docs/ARCHITECTURE.md` | Architecture and technical design document. |

---

### 5. Architecture Rules
1. **Strict Layering**:
   - `views/` files must handle UI widgets and user interactions. They must delegate calculations to `services/` and database operations to `data/sheets_repository.py`.
   - Never write raw Google Sheets API calls inside `views/`. Always invoke functions from `data/sheets_repository.py`.
2. **Pure Domain Services**:
   - Files in `services/` (`stock_service.py`, `transaction_service.py`, `report_service.py`) must remain pure Python and Pandas. **Never import `streamlit` inside `services/`**.
3. **Cache Coherence**:
   - Any write, append, update, or delete action must call `get_sheet_data.clear()` or let `sheets_repository.py` invalidate cached dataframes immediately.
4. **Virtual Package Isolation**:
   - Virtual bundles (Snack, Buah, Roti) must be unrolled into physical ingredients before saving to sheets. Never write virtual package names as stock items in `master_barang`.

---

### 6. Coding Conventions
- **Naming**:
  - Python files, functions, and variables use `snake_case` (e.g., `calculate_new_stock`, `nama_barang`).
  - Google Sheet columns and DataFrame columns use lowercase `snake_case` (e.g., `stok_sekarang`, `harga_master`).
  - View entry functions use `render_<module_name>()` (e.g., `render_transaksi`, `render_master_barang`).
- **Formatting**:
  - Currency must be formatted in Indonesian Rupiah (`Rp 1.500.000`) using `utils/formatting.py:format_currency_idr`.
  - Indonesian decimal commas (`1,5`) and dots (`1.5`) must be parsed safely using `pd.to_numeric` or custom parsing in `sheets_repository.py`.
- **Typing**:
  - Use Python standard type hints for service function arguments and returns (e.g., `def calculate_stock_percentage(stok: float, min_stok: float) -> float:`).
- **Error Handling**:
  - Trap network/quota exceptions in `data/sheets_repository.py` and display user-friendly `st.error()` alerts in `views/`. Never crash Streamlit with unhandled tracebacks.

---

### 7. How to Add a New CRUD Resource

Follow this step-by-step pattern when introducing a new resource (e.g., `master_supplier`):
1. **Google Sheets Table**: Add a new tab in the Google Spreadsheet (or define headers in code) with standard columns.
2. **Repository Functions**: Add sheet-specific accessors in `data/sheets_repository.py` if custom transformation is required, or use generic `get_sheet_data("master_supplier")`.
3. **Validator**: In `utils/validators.py`, write validation rules (e.g., `validate_supplier_input(name, phone)`).
4. **Service**: In `services/`, add business rules and transformation functions.
5. **View**: Create `views/master_supplier.py` containing `def render_master_supplier():`.
6. **Navigation Router**: In `app.py`:
   - Import `from views.master_supplier import render_master_supplier`.
   - Add menu entry to `menu_options` list.
   - Add routing branch inside `main()`: `elif selected == "🚚 Master Supplier": render_master_supplier()`.
7. **Tests**: Add test cases to `tests/whitebox_test.py` and `tests/health_check.py`.
8. **Documentation**: Update `docs/PRD.md` and `docs/ARCHITECTURE.md`.

---

### 8. Testing Rules
- **Where Tests Go**: All test suites live inside `tests/`.
- **Pre-Commit Verification**: Run `python tests/whitebox_test.py` before completing any task. All 92 tests must pass with 0 failures.
- **Edge Case Coverage**: When modifying calculation or validation logic, test for:
  - Division by zero (`min_stok = 0`, `total_pasien = 0`).
  - Negative values (`stok < 0`, `qty < 0`).
  - Float precision (`0.1 + 0.2`, `0.05 step`).
  - Empty or NaN inputs (`pd.NA`, `None`, empty string).
  - Malicious HTML/Script injection strings.

---

### 9. Database Rules
- **Schema-on-Read**: Google Sheets has no automated migration runner (Alembic/Django). Any new column must be handled gracefully with `.get('new_col', default_value)`.
- **Column Preservations**: When updating a sheet with `update_sheet_data(sheet_name, df)`, verify the dataframe retains all original column headers.
- **Index Safety**: When deleting rows via `delete_rows(sheet_name, indices)`, always sort indices descending to avoid shifting row offsets during deletion.

---

### 10. Security Rules
- **Never Commit Secrets**: Never commit `.streamlit/secrets.toml`. Only commit `.streamlit/secrets.toml.example` with dummy values.
- **Sanitize HTML**: Whenever rendering user-generated text inside `st.markdown(..., unsafe_allow_html=True)`, escape the text using `utils/formatting.py:escape_html()`.
- **Mandatory Staff Identity**: Every write action must require a non-empty `petugas` parameter to preserve audit trails.

---

### 11. Do / Don't List

#### DO
- **DO** use `wks.append_rows()` for bulk row insertions instead of sequential `append_row()` calls.
- **DO** clear `@st.cache_data` whenever the underlying Google Sheet is modified.
- **DO** maintain `step=0.05` and format `%.2f` for fractional quantity inputs (e.g., half-portions of fruit/bread).
- **DO** unroll composite packages into real inventory lines before persisting.

#### DON'T
- **DON'T** import `streamlit` inside `services/` or `data/` calculation functions.
- **DON'T** write negative stock to `master_barang` unless the item is explicitly flagged as "Bahan Bebas" (`status == "False"`).
- **DON'T** rely on global `pytest` binary in shell commands; run tests using `python tests/whitebox_test.py`.
- **DON'T** overwrite entire sheets when only appending new transactions; use `append_rows()`.

---

### 12. Definition of Done Checklist
- [ ] Code compiles without errors (`python -m py_compile <modified_files>`).
- [ ] All 92 white-box tests pass (`python tests/whitebox_test.py`).
- [ ] Health check passes (`python tests/health_check.py`).
- [ ] No regression in in-row package configuration and supplier popovers.
- [ ] Google Sheets cache invalidation is triggered on every data modification.
- [ ] Documentation (`docs/PRD.md`, `docs/ARCHITECTURE.md`, `AGENTS.md`) is kept up to date.

---

### 13. Known Pitfalls & Gotchas
1. **Google API Rate Limit (429)**: Google Sheets has a rate limit of 60 writes per minute. Avoid writing cell-by-cell; always use batch dataframe sets or row appends.
2. **Streamlit Execution Model**: Any widget interaction reruns the entire script from top to bottom. State must be preserved using `st.session_state` keys.
3. **Number Formatting in Google Sheets**: Indonesian locale formatting uses comma `,` as decimal separator and dot `.` as thousand separator. Ingestion scripts must strip currency symbols and normalize commas before parsing floats.
4. **Race Condition Overwrites**: Simultaneous writes from different browsers will overwrite each other's stock balance calculations because Google Sheets has no transaction lock.

---

### 14. Pointers to Documentation
- For product requirements, user stories, and acceptance criteria: [docs/PRD.md](file:///c:/Users/mfadh/OneDrive/Documents/1D/CGIZI/docs/PRD.md)
- For system architecture, C4 diagrams, sequence flows, and tech debt: [docs/ARCHITECTURE.md](file:///c:/Users/mfadh/OneDrive/Documents/1D/CGIZI/docs/ARCHITECTURE.md)
