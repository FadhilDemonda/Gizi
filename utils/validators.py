import pandas as pd
from typing import Tuple

def validate_new_item(kode_brg: str, nama_brg: str, master_df: pd.DataFrame) -> Tuple[bool, str]:
    """
    Validate if a new item can be added.
    
    Args:
        kode_brg (str): SKU
        nama_brg (str): Name
        master_df (pd.DataFrame): Existing items
        
    Returns:
        Tuple[bool, str]: (is_valid, error_message)
    """
    if kode_brg == "" or nama_brg == "":
        return False, "Kode dan Nama Barang harus diisi!"
    if kode_brg in master_df['kode_barang'].values:
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
    if edited_df['kode_barang'].duplicated().any():
        return False, "❌ Gagal! Terdapat Kode Barang yang duplikat (sama). Kode harus unik."
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
    if not petugas:
        return False, "Nama petugas harus diisi!"
    if jumlah == 0:
        return False, "Jumlah perubahan tidak boleh 0!"
    return True, ""
