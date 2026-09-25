import pandas as pd
from services.stock_service import classify_stock_status, filter_stock_by_status

def test_classify_stock_status():
    # Habis
    status, _, _, _, _, _ = classify_stock_status(0, 10, 0.0)
    assert status == "STOK HABIS"
    
    # Kritis
    status, _, _, _, _, _ = classify_stock_status(9, 10, 0.9)
    assert status.startswith("KRITIS")
    
    # Mendekati (Exactly 1.25x)
    status, _, _, _, _, _ = classify_stock_status(12.5, 10, 1.25)
    assert status == "Mendekati Min"
    
    # Aman
    status, _, _, _, _, _ = classify_stock_status(13, 10, 1.3)
    assert status == "STOK AMAN"
