import pandas as pd

def get_daily_transactions(transaksi_df: pd.DataFrame, target_date_str: str) -> pd.DataFrame:
    """
    Filter transactions for a specific date string.
    
    Args:
        transaksi_df (pd.DataFrame): Transactions dataframe.
        target_date_str (str): Date string in YYYY-MM-DD.
        
    Returns:
        pd.DataFrame: Filtered daily transactions.
    """
    if transaksi_df.empty:
        return pd.DataFrame()
    return transaksi_df[transaksi_df['tanggal'] == target_date_str].copy()

def aggregate_daily_summary(df_daily: pd.DataFrame, master_df: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate daily summary (Total Masuk, Total Keluar, Net) per item.
    
    Args:
        df_daily (pd.DataFrame): Daily transactions.
        master_df (pd.DataFrame): Master items (for names and units).
        
    Returns:
        pd.DataFrame: Summary dataframe.
    """
    if df_daily.empty:
        return pd.DataFrame()
        
    df_merge = pd.merge(df_daily, master_df[['kode_barang', 'nama_barang', 'satuan']], on='kode_barang', how='left')
    
    summary_data = []
    for kode in df_merge['kode_barang'].unique():
        df_item = df_merge[df_merge['kode_barang'] == kode]
        nama = df_item['nama_barang'].iloc[0]
        satuan = df_item['satuan'].iloc[0]
        
        masuk = df_item[df_item['jenis'] == 'Masuk']['jumlah'].sum()
        keluar = df_item[df_item['jenis'] == 'Keluar']['jumlah'].sum()
        net = masuk - keluar
        
        if net > 0:
            net_str = f"+{net} {satuan}"
        elif net < 0:
            net_str = f"{net} {satuan}"
        else:
            net_str = f"0 {satuan}"
            
        summary_data.append({
            'Kode SKU': kode,
            'Nama Barang': nama,
            'Total Masuk': f"{masuk} {satuan}" if masuk > 0 else "-",
            'Total Keluar': f"{keluar} {satuan}" if keluar > 0 else "-",
            'Pergerakan Bersih (Net)': net_str
        })
        
    return pd.DataFrame(summary_data)

def filter_last_n_days(df_trx: pd.DataFrame, n_days: int) -> pd.DataFrame:
    """
    Filter transactions for the last N days based on 'tanggal_dt'.
    
    Args:
        df_trx (pd.DataFrame): The filtered transaction dataframe.
        n_days (int): Number of days.
        
    Returns:
        pd.DataFrame: Filtered dataframe.
    """
    if df_trx.empty or 'tanggal_dt' not in df_trx.columns:
        return df_trx
        
    batas_tanggal = pd.Timestamp.today() - pd.Timedelta(days=n_days)
    return df_trx[df_trx['tanggal_dt'] >= batas_tanggal].copy()

def aggregate_trend_data(df_trx_filtered: pd.DataFrame) -> pd.DataFrame:
    """
    Group filtered transactions by date and type for charting.
    
    Args:
        df_trx_filtered (pd.DataFrame): Filtered transactions.
        
    Returns:
        pd.DataFrame: Grouped dataframe ready for bar chart.
    """
    if df_trx_filtered.empty:
        return pd.DataFrame()
    return df_trx_filtered.groupby(['tanggal', 'jenis'])['jumlah'].sum().reset_index()
