import pandas as pd
from typing import Tuple

def calculate_stock_percentage(stok_sekarang: float, stok_minimum: float) -> float:
    """
    Calculate the percentage of current stock relative to the minimum stock.
    
    Args:
        stok_sekarang (float): Current stock.
        stok_minimum (float): Minimum threshold stock.
        
    Returns:
        float: Percentage of stock.
    """
    stok_minimum_safe = max(stok_minimum, 1.0)
    return stok_sekarang / stok_minimum_safe

def classify_stock_status(stok_sekarang: float, stok_minimum: float, persentase: float) -> Tuple[str, str, str, str, str, str]:
    """
    Classify stock into Krisis, Mendekati, or Aman, and return UI formatting details.
    
    Args:
        stok_sekarang (float): Current stock.
        stok_minimum (float): Minimum threshold stock.
        persentase (float): Percentage (stok_sekarang / stok_minimum).
        
    Returns:
        Tuple[str, str, str, str, str, str]: A tuple containing:
            - status_text (str)
            - color_hex (str)
            - bg_color (str)
            - text_color (str)
            - icon (str)
            - estimasi (str)
    """
    if stok_sekarang < stok_minimum:
        if stok_sekarang == 0:
            status_text = "STOK HABIS"
            color_hex = "#d32f2f"
            bg_color = color_hex
            text_color = "white"
            icon = "🚫"
            estimasi = "Habis Hari Ini"
        else:
            status_text = f"KRITIS (Sisa {int(persentase * 100)}%)" if persentase > 0.1 else "SANGAT KRITIS"
            color_hex = "#d32f2f"
            bg_color = "rgba(211, 47, 47, 0.1)"
            text_color = color_hex
            icon = "🩸" if persentase <= 0.2 else "🔻"
            estimasi = "Segera Habis"
    elif stok_sekarang <= (stok_minimum * 1.25):
        status_text = "Mendekati Min"
        color_hex = "#f57f17"
        bg_color = "rgba(251, 192, 45, 0.1)"
        text_color = color_hex
        icon = "⚠️"
        estimasi = "Aman Sementara"
    else:
        status_text = "STOK AMAN"
        color_hex = "#2ca02c"
        bg_color = "rgba(44, 160, 44, 0.1)"
        text_color = color_hex
        icon = "✅"
        estimasi = "Aman Terkendali"
        
    return status_text, color_hex, bg_color, text_color, icon, estimasi

def calculate_bar_width(stok_sekarang: float, stok_minimum: float) -> int:
    """
    Calculate the progress bar width for the dashboard visualization.
    
    Args:
        stok_sekarang (float): Current stock.
        stok_minimum (float): Minimum threshold stock.
        
    Returns:
        int: Bar width percentage (0 to 100).
    """
    return int(min(100.0, (stok_sekarang / max(1.0, stok_minimum * 2)) * 100.0))

def filter_stock_by_status(master_df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Filter the master dataframe into Krisis, Mendekati, and Aman dataframes.
    
    Args:
        master_df (pd.DataFrame): The main inventory dataframe.
        
    Returns:
        Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]: (krisis_df, mendekati_df, aman_df)
    """
    krisis_df = master_df[master_df['stok_sekarang'] < master_df['stok_minimum']]
    mendekati_df = master_df[(master_df['stok_sekarang'] >= master_df['stok_minimum']) & (master_df['stok_sekarang'] <= (master_df['stok_minimum'] * 1.25))]
    aman_df = master_df[master_df['stok_sekarang'] > (master_df['stok_minimum'] * 1.25)]
    return krisis_df, mendekati_df, aman_df
