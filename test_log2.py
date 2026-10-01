import toml
import gspread
import pandas as pd

def test_read():
    secrets = toml.load(".streamlit/secrets.toml")
    gc = gspread.service_account_from_dict(secrets["gcp_service_account"])
    sh = gc.open_by_url(secrets["google_sheets"]["url"])
    ws = sh.worksheet("log")
    try:
        df = pd.DataFrame(ws.get_all_records(numericise_ignore=["all"]))
        if not df.empty:
            numeric_cols = ['stok_sekarang', 'stok_minimal', 'stok_minimum', 'harga_master', 'qty', 'harga_real', 'total_harga']
            for col in numeric_cols:
                if col in df.columns:
                    if df[col].dtype == object:
                        df[col] = df[col].apply(lambda x: str(x).replace(',', '.') if isinstance(x, str) else x)
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        print(f"Success! Read {len(df)} rows.")
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_read()
