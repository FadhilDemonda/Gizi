import pandas as pd
from services.report_service import get_daily_transactions

def test_get_daily_transactions():
    df = pd.DataFrame([
        {'tanggal': '2026-09-24', 'jumlah': 10},
        {'tanggal': '2026-09-25', 'jumlah': 5},
    ])
    
    res = get_daily_transactions(df, '2026-09-25')
    assert len(res) == 1
    assert res.iloc[0]['jumlah'] == 5
