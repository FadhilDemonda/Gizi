import pandas as pd
from typing import Tuple

def validate_new_item(kode_brg: str, nama_brg: str, master_df: pd.DataFrame, supplier: str = "") -> Tuple[bool, str]:
    """
    Validate if a new item can be added.
    
    Args:
        kode_brg (str): SKU
        nama_brg (str): Name
        master_df (pd.DataFrame): Existing items
        supplier (str, optional): Supplier name
        
    Returns:
        Tuple[bool, str]: (is_valid, error_message)
    """
    if not str(kode_brg).strip() or not str(nama_brg).strip():
        return False, "Kode dan Nama Barang harus diisi!"
        
    clean_kode = str(kode_brg).strip()
    clean_sup = str(supplier).strip().lower()
    
    if clean_sup and 'supplier' in master_df.columns:
        exists = (
            (master_df['kode_barang'].astype(str).str.strip().str.lower() == clean_kode.lower()) &
            (master_df['supplier'].astype(str).str.strip().str.lower() == clean_sup)
        ).any()
        if exists:
            return False, f"Kode Barang '{clean_kode}' dengan Supplier '{supplier}' sudah terdaftar!"
    else:
        if clean_kode in master_df['kode_barang'].astype(str).str.strip().values:
            return False, "Kode Barang sudah terdaftar!"
            
    return True, ""

def validate_editor_changes(edited_df: pd.DataFrame) -> Tuple[bool, str]:
    """
    Validate if changes in the data editor are valid.
    
    Args:
        edited_df (pd.DataFrame): Edited dataframe
        
    Returns:
        Tuple[bool, str]: (is_valid, error_message)
    """
    # Kode barang boleh sama untuk barang dari supplier berbeda.
    # Duplikasi hanya ditolak jika kombinasi kode_barang dan supplier sama persis.
    if 'supplier' in edited_df.columns and 'kode_barang' in edited_df.columns:
        clean_kode = edited_df['kode_barang'].astype(str).str.strip().str.lower()
        clean_sup = edited_df['supplier'].astype(str).str.strip().str.lower()
        combo = clean_kode + "||" + clean_sup
        if combo.duplicated().any():
            return False, "❌ Gagal! Terdapat kombinasi Kode Barang dan Supplier yang duplikat."
    elif 'kode_barang' in edited_df.columns:
        if edited_df['kode_barang'].duplicated().any():
            return False, "❌ Gagal! Terdapat Kode Barang yang duplikat (sama). Kode harus unik."

    # Periksa data sel yang kosong pada kolom utama
    critical_cols = [c for c in ['kode_barang', 'nama_barang'] if c in edited_df.columns]
    if critical_cols:
        for c in critical_cols:
            if edited_df[c].isnull().any() or (edited_df[c].astype(str).str.strip() == "").any():
                return False, "❌ Gagal! Terdapat data sel yang kosong. Harap isi dengan lengkap."
    else:
        if edited_df.isnull().any().any() or (edited_df == "").any().any():
            return False, "❌ Gagal! Terdapat data sel yang kosong. Harap isi dengan lengkap."
            
    return True, ""

def validate_transaction(petugas: str, jumlah: float) -> Tuple[bool, str]:
    """
    Validate if a transaction is valid.
    
    Args:
        petugas (str): PIC Name
        jumlah (float): Amount
        
    Returns:
        Tuple[bool, str]: (is_valid, error_message)
    """
    if not str(petugas).strip():
        return False, "Nama petugas harus diisi!"
    try:
        val = float(jumlah)
        import math
        if math.isnan(val) or math.isinf(val) or val <= 0:
            return False, "Jumlah perubahan harus lebih besar dari 0!"
    except (ValueError, TypeError):
        return False, "Jumlah perubahan tidak valid!"
    return True, ""
