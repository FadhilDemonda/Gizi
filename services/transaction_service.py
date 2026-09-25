import pandas as pd
from typing import Tuple, Dict, Any, List
from datetime import datetime

def generate_transaction_id(current_length: int) -> str:
    """
    Generate the next transaction ID.
    
    Args:
        current_length (int): Current number of transactions (or length + offset).
        
    Returns:
        str: Formatted transaction ID (e.g. T0001)
    """
    return f"T{current_length + 1:04d}"

def validate_stock_out(stok_awal: float, jumlah_keluar: float) -> Tuple[bool, float]:
    """
    Validate if there is enough stock for a 'Keluar' transaction.
    
    Args:
        stok_awal (float): Initial stock.
        jumlah_keluar (float): Amount to reduce.
        
    Returns:
        Tuple[bool, float]: (is_valid, stok_akhir)
    """
    stok_akhir = stok_awal - jumlah_keluar
    is_valid = stok_akhir >= 0
    return is_valid, stok_akhir

def compute_stok_akhir(stok_awal: float, jumlah: float, jenis_transaksi: str) -> float:
    """
    Compute final stock based on transaction type.
    
    Args:
        stok_awal (float): Initial stock.
        jumlah (float): Amount changed.
        jenis_transaksi (str): 'Masuk' or 'Keluar' or 'Edit'.
        
    Returns:
        float: Final stock.
    """
    if jenis_transaksi == "Masuk":
        return stok_awal + jumlah
    elif jenis_transaksi == "Keluar":
        return stok_awal - jumlah
    return stok_awal

def build_transaction_record(
    transaksi_df_len: int, 
    jenis: str, 
    kode_barang: str, 
    jumlah: float, 
    petugas: str, 
    shift: str, 
    keterangan: str
) -> Dict[str, Any]:
    """
    Build a dictionary representing a new transaction log entry.
    
    Args:
        transaksi_df_len (int): Current number of transactions to generate ID.
        jenis (str): Transaction type (Masuk, Keluar, Edit).
        kode_barang (str): SKU.
        jumlah (float): Amount.
        petugas (str): PIC.
        shift (str): Shift time.
        keterangan (str): Additional description.
        
    Returns:
        Dict[str, Any]: The transaction record.
    """
    return {
        'id_transaksi': generate_transaction_id(transaksi_df_len),
        'tanggal': datetime.today().strftime('%Y-%m-%d'),
        'jenis': jenis,
        'kode_barang': kode_barang,
        'jumlah': jumlah,
        'petugas': petugas,
        'shift': shift,
        'keterangan': keterangan
    }
